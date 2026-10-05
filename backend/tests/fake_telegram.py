"""In-memory fake of the parts of Telethon the pipeline uses.

Implements ``messages.search`` semantics (newest first, ``offset_id``,
``min_date``/``max_date``, ``from_id=self``, exact ``count``) and
``get_messages(offset_date=...)`` over synthetic chats with known ground truth,
so tests can check both accuracy and the number of API calls.
"""
from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any

from telethon import errors
from telethon.tl.functions.messages import SearchRequest
from telethon.tl.types import (
    Channel,
    Chat,
    InputPeerChannel,
    InputPeerChat,
    InputPeerUser,
    User,
)


@dataclass
class FakeMsg:
    id: int
    date: datetime
    out: bool
    message: str = ""
    media: Any = None
    sticker: Any = None
    photo: Any = None
    voice: Any = None
    gif: Any = None
    video_note: Any = None
    audio: Any = None
    video: Any = None
    document: Any = None
    action: Any = None
    fwd_from: Any = None
    reply_to: Any = None
    edit_date: Any = None
    reactions: Any = None
    entities: Any = None


@dataclass
class FakeChat:
    entity: Any
    name: str
    messages: list[FakeMsg] = field(default_factory=list)  # ascending ids/dates

    @property
    def key(self) -> int:
        return self.entity.id


WORDS = ["hey", "lol", "coffee", "tomorrow", "see you", "nice", "ok", "dinner", "meeting", "haha", "love it"]


def build_chat(
    entity: Any,
    name: str,
    start: datetime,
    end: datetime,
    n: int,
    out_ratio: float,
    rng: random.Random,
    first_id: int = 1,
    sticker_every: int = 0,
    photo_every: int = 0,
) -> FakeChat:
    span = (end - start).total_seconds()
    dates = sorted(start + timedelta(seconds=rng.random() * span) for _ in range(n))
    msgs = []
    for i, d in enumerate(dates):
        out = rng.random() < out_ratio
        m = FakeMsg(id=first_id + i, date=d, out=out, message=" ".join(rng.choice(WORDS) for _ in range(3)))
        if out and sticker_every and i % sticker_every == 0:
            doc = SimpleNamespace(id=1000 + (i // sticker_every) % 3, attributes=[SimpleNamespace(alt="😂")], thumbs=None)
            m.media, m.sticker, m.document, m.message = object(), doc, doc, ""
        elif out and photo_every and i % photo_every == 0:
            m.media, m.photo = object(), object()
        if out and i % 50 == 0:
            m.reactions = SimpleNamespace(results=[SimpleNamespace(reaction=SimpleNamespace(emoticon="🔥"), count=i % 7 + 1)])
        msgs.append(m)
    return FakeChat(entity=entity, name=name, messages=msgs)


def user(uid: int, name: str, **kw: Any) -> User:
    return User(id=uid, access_hash=uid * 7, first_name=name, **kw)


def megagroup(cid: int, title: str, date: datetime) -> Channel:
    return Channel(id=cid, title=title, access_hash=cid * 7, date=date, photo=None, megagroup=True)


def basic_group(cid: int, title: str, date: datetime) -> Chat:
    return Chat(id=cid, title=title, participants_count=5, date=date, version=1, photo=None)


class FakeClient:
    def __init__(
        self,
        chats: list[FakeChat],
        flood_every: int = 0,
        flood_seconds: int = 1,
        latency: float = 0.0,
        ignore_from_id_in_private: bool = False,
    ) -> None:
        self.latency = latency
        self.ignore_from_id_in_private = ignore_from_id_in_private
        self.chats = {c.key: c for c in chats}
        self._order = chats
        self.calls: dict[str, int] = {"search": 0, "history": 0, "dialogs": 0, "download": 0}
        self.flood_every = flood_every
        self.flood_seconds = flood_seconds
        self._n = 0

    def _maybe_flood(self) -> None:
        self._n += 1
        if self.flood_every and self._n % self.flood_every == 0:
            raise errors.FloodWaitError(request=None, capture=self.flood_seconds)

    def _chat_for_peer(self, peer: Any) -> FakeChat:
        if isinstance(peer, InputPeerUser):
            return self.chats[peer.user_id]
        if isinstance(peer, InputPeerChat):
            return self.chats[peer.chat_id]
        if isinstance(peer, InputPeerChannel):
            return self.chats[peer.channel_id]
        raise TypeError(peer)

    async def __call__(self, request: Any) -> Any:
        assert isinstance(request, SearchRequest)
        self.calls["search"] += 1
        if self.latency:
            await asyncio.sleep(self.latency)
        self._maybe_flood()
        chat = self._chat_for_peer(request.peer)
        apply_from = request.from_id is not None and not (
            self.ignore_from_id_in_private and isinstance(request.peer, InputPeerUser)
        )
        matching = [
            m for m in chat.messages
            if (not apply_from or m.out)
            and (request.min_date is None or m.date >= request.min_date)
            and (request.max_date is None or m.date <= request.max_date)
        ]
        count = len(matching)
        page = [m for m in reversed(matching) if not request.offset_id or m.id < request.offset_id]
        return SimpleNamespace(messages=page[: request.limit], count=count)

    async def get_messages(self, entity: Any, limit: int = 100, offset_date: datetime | None = None) -> list[FakeMsg]:
        self.calls["history"] += 1
        if self.latency:
            await asyncio.sleep(self.latency)
        self._maybe_flood()
        chat = self.chats[entity.id]
        older = [m for m in reversed(chat.messages) if offset_date is None or m.date < offset_date]
        return older[:limit]

    async def get_dialogs(self, limit: Any = None) -> list[Any]:
        self.calls["dialogs"] += 1
        return [
            SimpleNamespace(
                id=c.key, name=c.name, entity=c.entity,
                message=c.messages[-1] if c.messages else None,
            )
            for c in self._order
        ]

    async def download_profile_photo(self, entity: Any, file: Any = None, download_big: bool = False) -> bytes:
        self.calls["download"] += 1
        return b"\xff\xd8\xff-avatar"

    async def download_media(self, doc: Any, file: Any = None, thumb: Any = None) -> bytes:
        self.calls["download"] += 1
        return b"RIFF-sticker"

    def takeout(self, **kwargs: Any) -> Any:
        raise errors.TakeoutInitDelayError(request=None, capture=86400)

    @property
    def total_calls(self) -> int:
        return sum(self.calls.values())
