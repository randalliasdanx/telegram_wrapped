"""Data acquisition from the Telegram API.

Strategy (designed to minimise API calls while maximising accuracy):

1. **Count** — one ``messages.search(from_id=self, min_date, max_date)`` per
   dialog. Telegram returns the *exact* number of messages the user sent in
   that chat during the period, plus the newest 100 of them. For most chats
   that single call already returns every message.
2. **Plan** — if the remaining messages fit in the page budget we fetch all of
   them (exact mode). Otherwise each chat gets pages in proportion to its
   size, spread over up to 52 time windows (estimated mode). Every window
   reports its own exact message count, so each sampled message carries a
   weight ``window_count / fetched`` — a stratified estimator.
3. **Conversations** — for the top 1:1 chats, a few contiguous history windows
   (both sides) feed reply-speed and conversation-starter stats, and one cheap
   ``limit=1`` search gives the both-sides total for the top chats.

Fetching only the user's *own* messages is the key efficiency win: in a busy
group the user may write 2% of the messages, so ``getHistory`` would waste 98%
of its calls.

Messages are converted to compact :class:`MsgRecord` objects immediately so
memory stays bounded even for accounts with 100k+ messages.
"""
from __future__ import annotations

import asyncio
import logging
import math
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable

from telethon import TelegramClient, errors, utils
from telethon.tl.functions.messages import SearchRequest
from telethon.tl.types import (
    Channel,
    Chat,
    InputMessagesFilterEmpty,
    InputPeerSelf,
    MessageEntityTextUrl,
    MessageEntityUrl,
    MessageMediaWebPage,
    User,
)

from app.throttle import AdaptiveThrottle, BudgetExceeded

log = logging.getLogger("wrapped.fetcher")

PAGE_SIZE = 100  # Telegram's maximum per messages.search call
SERVICE_USER_IDS = {777000, 42777}  # Telegram service notifications
MAX_WINDOWS = 52  # weekly strata at most
FULL_FETCH_WINDOW_MSGS = 1500  # split exact fetches into windows of ~this size for parallelism
CONVERSATION_DIALOGS = 8
CONVERSATION_WINDOWS = 6
TOTALS_FOR_TOP = 12

ProgressFn = Callable[[dict[str, Any]], Any]


# ---------------------------------------------------------------------------
# Compact records
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class MsgRecord:
    """A message the user sent, reduced to what the stats need.

    Attribute names mirror Telethon's so ``app.ml.features`` can consume
    records and Telethon messages interchangeably.
    """

    id: int
    date: datetime
    message: str
    weight: float = 1.0
    media_kind: str | None = None
    sticker_id: int | None = None
    sticker_emoji: str | None = None
    has_link: bool = False
    forward: bool = False
    reply_to: bool = False
    edit_date: bool = False
    reaction_total: int = 0
    reactions: list[tuple[str, int]] | None = None
    dialog: str = ""
    exact: bool = True  # True when this message's window was fetched completely


@dataclass(slots=True)
class HistoryMsg:
    """A message from a both-sides history window (for reply dynamics)."""

    date: datetime
    out: bool


@dataclass
class DialogData:
    name: str
    is_group: bool
    is_private: bool
    entity: Any = field(repr=False, default=None)
    peer: Any = field(repr=False, default=None)
    sent_count: int = 0
    total_count: int | None = None
    records: list[MsgRecord] = field(default_factory=list)
    history_batches: list[list[HistoryMsg]] = field(default_factory=list)
    fetched_unique: int = 0
    complete: bool = False
    filter_ignored: bool = False  # Telegram ignored from_id=self here
    both_sides_count: int = 0  # the count Telegram returned when it ignored from_id


@dataclass
class Collected:
    dialogs: list[DialogData]
    sticker_docs: dict[int, Any] = field(repr=False, default_factory=dict)
    exact: bool = True
    api_calls: int = 0
    total_exact: bool = True


# ---------------------------------------------------------------------------
# Message conversion
# ---------------------------------------------------------------------------
def classify_media(msg: Any) -> str | None:
    """Map a Telethon message to one of the media_totals keys (or sticker)."""
    if getattr(msg, "media", None) is None:
        return None
    if getattr(msg, "sticker", None) is not None:
        return "sticker"
    if getattr(msg, "gif", None) is not None:
        return "gifs"
    if getattr(msg, "video_note", None) is not None:
        return "round_videos"
    if getattr(msg, "voice", None) is not None:
        return "voice_notes"
    if getattr(msg, "audio", None) is not None:
        return "music"
    if getattr(msg, "video", None) is not None:
        return "videos"
    if getattr(msg, "photo", None) is not None:
        return "photos"
    if getattr(msg, "document", None) is not None:
        return "documents"
    return None


def _has_link(msg: Any) -> bool:
    if isinstance(getattr(msg, "media", None), MessageMediaWebPage):
        return True
    for ent in getattr(msg, "entities", None) or ():
        if isinstance(ent, (MessageEntityUrl, MessageEntityTextUrl)):
            return True
    return False


def _reactions(msg: Any) -> tuple[int, list[tuple[str, int]] | None]:
    reactions = getattr(msg, "reactions", None)
    results = getattr(reactions, "results", None) if reactions else None
    if not results:
        return 0, None
    out: list[tuple[str, int]] = []
    total = 0
    for r in results:
        count = getattr(r, "count", 0) or 0
        total += count
        emoji = getattr(r.reaction, "emoticon", None) or "❤️"
        out.append((emoji, count))
    return total, out


def to_record(msg: Any, dialog_name: str, sticker_docs: dict[int, Any] | None = None) -> MsgRecord | None:
    date = getattr(msg, "date", None)
    if date is None or getattr(msg, "action", None) is not None:
        return None  # service message (joined, pinned, call...)
    kind = classify_media(msg)
    sticker_id = None
    sticker_emoji = None
    if kind == "sticker":
        doc = msg.sticker
        sticker_id = doc.id
        for attr in getattr(doc, "attributes", ()):
            alt = getattr(attr, "alt", None)
            if alt:
                sticker_emoji = alt
                break
        if sticker_docs is not None and sticker_id not in sticker_docs:
            sticker_docs[sticker_id] = doc
    reaction_total, reactions = _reactions(msg)
    return MsgRecord(
        id=msg.id,
        date=date,
        message=getattr(msg, "message", None) or "",
        media_kind=kind,
        sticker_id=sticker_id,
        sticker_emoji=sticker_emoji,
        has_link=_has_link(msg),
        forward=getattr(msg, "fwd_from", None) is not None,
        reply_to=getattr(msg, "reply_to", None) is not None,
        edit_date=getattr(msg, "edit_date", None) is not None,
        reaction_total=reaction_total,
        reactions=reactions if reaction_total else None,
        dialog=dialog_name,
    )


# ---------------------------------------------------------------------------
# Dialog selection
# ---------------------------------------------------------------------------
def is_group_entity(entity: Any) -> bool:
    return isinstance(entity, Chat) or (isinstance(entity, Channel) and bool(getattr(entity, "megagroup", False)))


def select_candidate_dialogs(dialogs: list[Any], start: datetime) -> list[Any]:
    """Keep conversations the user can have *sent* messages in this period:
    private chats with humans, basic groups and supergroups. Broadcast
    channels, bots, Saved Messages and Telegram service chats are skipped."""
    selected = []
    for d in dialogs:
        if not getattr(d, "message", None) or d.message.date < start:
            continue
        entity = d.entity
        if isinstance(entity, User):
            if getattr(entity, "bot", False) or getattr(entity, "is_self", False):
                continue
            if getattr(entity, "id", None) in SERVICE_USER_IDS:
                continue
        elif not is_group_entity(entity):
            continue
        selected.append(d)
    log.info("Selected %d candidate dialogs from %d", len(selected), len(dialogs))
    return selected


# ---------------------------------------------------------------------------
# Planning (pure — unit tested)
# ---------------------------------------------------------------------------
@dataclass
class FetchPlan:
    exact: bool
    # dialog index -> (number of windows, max pages per window or None for unlimited)
    per_dialog: dict[int, tuple[int, int | None]]


def plan_fetch(sent_counts: list[int], first_page_sizes: list[int], page_budget: int) -> FetchPlan:
    """Decide how many windows/pages each dialog gets.

    ``sent_counts[i]`` is the exact number of messages the user sent in dialog
    ``i``; ``first_page_sizes[i]`` how many of them the count call returned.
    Dialogs already complete get no plan entry.
    """
    remaining = {
        i: c for i, (c, got) in enumerate(zip(sent_counts, first_page_sizes)) if c > got
    }
    pages_needed = sum(math.ceil(c / PAGE_SIZE) for c in remaining.values())
    per_dialog: dict[int, tuple[int, int | None]] = {}
    if pages_needed <= page_budget:
        for i, c in remaining.items():
            windows = max(1, min(MAX_WINDOWS, math.ceil(c / FULL_FETCH_WINDOW_MSGS)))
            per_dialog[i] = (windows, None)
        return FetchPlan(exact=True, per_dialog=per_dialog)

    # Estimated mode: proportional allocation => uniform sampling fraction.
    # Every dialog keeps at least 2 pages so small chats are not starved.
    total = sum(remaining.values()) or 1
    for i, c in remaining.items():
        pages = max(2, math.floor(page_budget * c / total))
        pages = min(pages, math.ceil(c / PAGE_SIZE))
        windows = max(1, min(MAX_WINDOWS, pages))
        per_dialog[i] = (windows, max(1, math.ceil(pages / windows)))
    return FetchPlan(exact=False, per_dialog=per_dialog)


def window_bounds(start: datetime, end: datetime, n: int) -> list[tuple[datetime, datetime]]:
    span = (end - start) / n
    return [(start + span * k, start + span * (k + 1)) for k in range(n)]


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------
class Fetcher:
    def __init__(
        self,
        client: TelegramClient,
        throttle: AdaptiveThrottle,
        start: datetime,
        end: datetime,
        progress: ProgressFn,
        page_budget: int,
        raw_client: TelegramClient | None = None,
        read_seconds: float = 75,
        conversation_seconds: float = 20,
    ) -> None:
        self.read_seconds = read_seconds
        self.conversation_seconds = conversation_seconds
        self.filter_ignored = 0
        self.client = client
        self.raw_client = raw_client or client
        self.thr = throttle
        self.start = start
        self.end = end
        self.progress = progress
        self.page_budget = page_budget
        self.sticker_docs: dict[int, Any] = {}
        self.analyzed = 0
        self.count_failures = 0
        self._search_client = client

    # -- low level ---------------------------------------------------------
    async def _search(
        self,
        peer: Any,
        *,
        from_self: bool,
        min_date: datetime,
        max_date: datetime,
        offset_id: int = 0,
        limit: int = PAGE_SIZE,
        essential: bool = False,
    ) -> tuple[int, list[Any]]:
        def make() -> Any:
            return self._search_client(SearchRequest(
                peer=peer,
                q="",
                filter=InputMessagesFilterEmpty(),
                min_date=min_date,
                max_date=max_date,
                offset_id=offset_id,
                add_offset=0,
                limit=limit,
                max_id=0,
                min_id=0,
                hash=0,
                from_id=InputPeerSelf() if from_self else None,
            ))

        try:
            result = await self.thr.run(make, essential=essential)
        except errors.RPCError as e:
            # Some servers reject search inside a takeout session; fall back
            # to the regular client for searches once and keep going.
            if self._search_client is not self.raw_client and "TAKEOUT" in str(e).upper():
                log.info("Search not allowed in takeout (%s); using standard client", e)
                self._search_client = self.raw_client
                result = await self.thr.run(make, essential=essential)
            else:
                raise
        messages = list(getattr(result, "messages", []) or [])
        count = getattr(result, "count", None)
        if count is None:
            count = len(messages)
        return count, messages

    async def _emit(self, data: dict[str, Any]) -> None:
        data.setdefault("messages_analyzed", self.analyzed)
        res = self.progress(data)
        if asyncio.iscoroutine(res):
            await res

    # -- phases -------------------------------------------------------------
    async def collect(self, candidates: list[Any]) -> Collected:
        names: dict[str, int] = {}

        def unique_name(d: Any) -> str:
            # Stats are keyed by display name; two chats called "Alex" must not merge
            base = getattr(d, "name", None) or "Deleted Account"
            names[base] = names.get(base, 0) + 1
            return base if names[base] == 1 else f"{base} ({names[base]})"

        dialogs = [
            DialogData(
                name=unique_name(d),
                is_group=is_group_entity(d.entity),
                is_private=isinstance(d.entity, User),
                entity=d.entity,
                peer=utils.get_input_peer(d.entity),
            )
            for d in candidates
        ]
        await self._count_phase(dialogs)
        dialogs = [d for d in dialogs if d.sent_count > 0]
        dialogs.sort(key=lambda d: d.sent_count, reverse=True)
        exact = await self._fetch_phase(dialogs)
        await self._conversation_phase(dialogs)
        return Collected(
            dialogs=dialogs,
            sticker_docs=self.sticker_docs,
            exact=exact and self.count_failures == 0,
            api_calls=self.thr.calls,
            total_exact=self.count_failures == 0 and self.filter_ignored == 0,
        )

    def _own_records(self, msgs: list[Any], d: DialogData, lo: datetime, hi: datetime, seen: set[int]) -> tuple[list[MsgRecord], int, int]:
        """Convert a from_id=self search page into records.

        Returns (records, raw_new, foreign): ``raw_new`` counts every new
        message id (the denominator for weights), ``foreign`` how many were
        not sent by the user — non-zero means Telegram ignored ``from_id``.
        """
        out: list[MsgRecord] = []
        raw_new = foreign = 0
        for m in msgs:
            if m.id in seen:
                continue
            seen.add(m.id)
            raw_new += 1
            if not getattr(m, "out", True):
                foreign += 1
                continue
            rec = to_record(m, d.name, self.sticker_docs)
            if rec and lo <= rec.date <= hi:
                out.append(rec)
        return out, raw_new, foreign

    async def _count_phase(self, dialogs: list[DialogData]) -> None:
        total = len(dialogs)
        done = 0

        async def one(d: DialogData) -> None:
            nonlocal done
            try:
                count, msgs = await self._search(
                    d.peer, from_self=True, min_date=self.start, max_date=self.end, essential=True,
                )
            except Exception as e:
                log.warning("Count failed for a dialog: %s: %s", type(e).__name__, e)
                self.count_failures += 1
                count, msgs = 0, []
            records, raw, foreign = self._own_records(msgs, d, self.start, self.end, set())
            d.records = records
            d.complete = count <= raw
            if foreign:
                # Telegram returned everyone's messages: the count is for both
                # sides. Estimate the user's share from this page until the
                # read phase measures it per time window.
                self.filter_ignored += 1
                d.filter_ignored = True
                d.both_sides_count = count
                d.sent_count = round(count * (raw - foreign) / max(raw, 1))
                log.warning(
                    "from_id filter ignored in a %s chat (%d/%d foreign on first page)",
                    "private" if d.is_private else "group", foreign, raw,
                )
            else:
                d.sent_count = count
            d.fetched_unique = len(d.records)
            self.analyzed += len(d.records)
            done += 1
            if done % 10 == 0 or done == total:
                await self._emit({
                    "phase": "counting",
                    "progress": done,
                    "total": total,
                    "message": f"Counting your messages… {done}/{total} chats",
                })

        await asyncio.gather(*(one(d) for d in dialogs))

    async def _fetch_phase(self, dialogs: list[DialogData]) -> bool:
        plan = plan_fetch(
            [d.sent_count for d in dialogs],
            [len(d.records) if d.complete else 0 for d in dialogs],
            self.page_budget,
        )
        if not plan.per_dialog:
            return self.filter_ignored == 0

        grand = sum(d.sent_count for d in dialogs)
        log.info(
            "Fetch plan: %s mode, %d of %d chats need reading, %d sent messages, %ds budget",
            "exact" if plan.exact else "estimated", len(plan.per_dialog), len(dialogs), grand,
            self.read_seconds,
        )
        # The read budget starts now: slow counting must not eat it.
        self.thr.set_deadline(self.read_seconds)

        # Count-phase pages are kept aside as a fallback sample; windows
        # replace them when they arrive.
        fallback: dict[int, list[MsgRecord]] = {}
        for i in plan.per_dialog:
            self.analyzed -= len(dialogs[i].records)
            fallback[i] = dialogs[i].records
            dialogs[i].records = []

        @dataclass
        class Window:
            i: int
            lo: datetime
            hi: datetime
            max_pages: int | None
            count: int | None = None
            raw: int = 0
            pages: int = 0
            offset_id: int = 0
            done: bool = False
            records: list[MsgRecord] = field(default_factory=list)
            seen: set[int] = field(default_factory=set)

        windows = [
            Window(i, lo, hi, max_pages)
            for i, (n, max_pages) in plan.per_dialog.items()
            for lo, hi in window_bounds(self.start, self.end, n)
        ]
        random.shuffle(windows)  # interleave chats so a cut is spread evenly

        pages_total = sum(
            (mp if mp is not None else math.ceil(dialogs[i].sent_count / PAGE_SIZE / n)) * n
            for i, (n, mp) in plan.per_dialog.items()
        ) or 1
        pages_done = 0
        stopped = False

        async def next_page(w: Window) -> None:
            nonlocal pages_done, stopped
            if w.done or stopped:
                return
            d = dialogs[w.i]
            try:
                count, msgs = await self._search(
                    d.peer, from_self=True, min_date=w.lo, max_date=w.hi, offset_id=w.offset_id,
                )
            except BudgetExceeded:
                stopped = True
                return
            except Exception as e:
                log.warning("Window fetch failed: %s: %s", type(e).__name__, e)
                w.done = True
                return
            pages_done += 1
            w.pages += 1
            if w.count is None:
                w.count = count
            recs, raw, _ = self._own_records(msgs, d, w.lo, w.hi, w.seen)
            w.records.extend(recs)
            w.raw += raw
            self.analyzed += len(recs)
            if not msgs or w.raw >= (w.count or 0) or (w.max_pages is not None and w.pages >= w.max_pages):
                w.done = True
            else:
                w.offset_id = min(m.id for m in msgs)
            if pages_done % 5 == 0:
                await self._emit({
                    "phase": "fetching",
                    "progress": min(pages_done, pages_total),
                    "total": pages_total,
                    "message": "Reading your messages…",
                })

        # Breadth first: one page from every window per round, so a deadline
        # still leaves a sample spread across the whole year and every chat.
        while not stopped:
            pending = [w for w in windows if not w.done]
            if not pending:
                break
            await asyncio.gather(*(next_page(w) for w in pending))

        incomplete = stopped
        by_dialog: dict[int, list[Window]] = {}
        for w in windows:
            by_dialog.setdefault(w.i, []).append(w)

        for i, ws in by_dialog.items():
            d = dialogs[i]
            reached = [w for w in ws if w.count is not None]
            unique: dict[int, MsgRecord] = {}
            covered = 0
            for w in reached:
                covered += w.count or 0
                # weight = messages in window / messages actually seen there
                weight = (w.count / w.raw) if w.raw and w.count and w.count > w.raw else 1.0
                for rec in w.records:
                    rec.weight = weight
                    rec.exact = weight == 1.0 and not d.filter_ignored
                    unique.setdefault(rec.id, rec)  # windows share boundary seconds
                if weight != 1.0:
                    incomplete = True
            records = list(unique.values())
            # Windows report counts in the same unit as the dialog total:
            # both sides when Telegram ignored from_id, the user's otherwise.
            dialog_total = d.both_sides_count if d.filter_ignored else d.sent_count
            if d.filter_ignored and records and covered:
                # Weighted own records estimate what the user sent in the
                # reached windows; extrapolate to unreached windows.
                own = sum(r.weight for r in records)
                d.sent_count = round(own * max(dialog_total / covered, 1.0))
            if not records:
                # Nothing read for this chat: fall back to its newest messages
                records = fallback.get(i, [])
                self.analyzed += len(records)
                if records:
                    w8 = d.sent_count / len(records)
                    for rec in records:
                        rec.weight, rec.exact = w8, w8 == 1.0
                    incomplete = incomplete or w8 != 1.0
            elif covered and covered < dialog_total:
                # Some windows never reached: scale the reached ones up
                incomplete = True
                scale = dialog_total / covered
                for rec in records:
                    rec.weight *= scale
                    rec.exact = False
            d.records = records
            d.fetched_unique = len(records)
            d.complete = not incomplete and d.fetched_unique >= d.sent_count

        if stopped:
            log.info("Read budget reached after %d pages; finishing with estimates", pages_done)
        return plan.exact and not incomplete and self.filter_ignored == 0

    async def _conversation_phase(self, dialogs: list[DialogData]) -> None:
        await self._emit({"phase": "conversations", "message": "Looking at how your conversations flow…"})
        self.thr.set_deadline(self.conversation_seconds)
        top_private = [d for d in dialogs if d.is_private][:CONVERSATION_DIALOGS]
        top_any = dialogs[:TOTALS_FOR_TOP]

        async def total_one(d: DialogData) -> None:
            try:
                count, _ = await self._search(d.peer, from_self=False, min_date=self.start, max_date=self.end, limit=1)
                d.total_count = max(count, d.sent_count)
            except BudgetExceeded:
                pass
            except Exception as e:
                log.debug("Total count failed: %s", e)

        async def history_one(d: DialogData) -> None:
            span = (self.end - self.start).total_seconds()
            n = CONVERSATION_WINDOWS
            for k in range(n):
                point = self.start + timedelta(seconds=span * (k + random.random()) / n)
                try:
                    msgs = await self.thr.run(
                        lambda p=point: self.client.get_messages(d.entity, limit=PAGE_SIZE, offset_date=p),
                    )
                except BudgetExceeded:
                    return
                except Exception as e:
                    log.debug("History window failed: %s", e)
                    continue
                batch = [
                    HistoryMsg(date=m.date, out=bool(getattr(m, "out", False)))
                    for m in (msgs or [])
                    if getattr(m, "action", None) is None and m.date and self.start <= m.date <= self.end
                ]
                if len(batch) > 1:
                    batch.sort(key=lambda h: h.date)
                    d.history_batches.append(batch)

        await asyncio.gather(
            *(total_one(d) for d in top_any),
            *(history_one(d) for d in top_private),
        )


async def download_avatar(client: TelegramClient, throttle: AdaptiveThrottle, entity: Any, timeout: float = 8.0) -> str | None:
    """Small profile photo as a data: URI (best effort, optional)."""
    import base64

    if getattr(entity, "photo", None) is None:
        return None
    try:
        data = await asyncio.wait_for(
            throttle.run(lambda: client.download_profile_photo(entity, file=bytes, download_big=False)),
            timeout,
        )
    except (BudgetExceeded, asyncio.TimeoutError):
        return None
    except Exception as e:
        log.debug("Avatar download failed: %s", e)
        return None
    if not data:
        return None
    return "data:image/jpeg;base64," + base64.b64encode(data).decode()
