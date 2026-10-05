# Telegram MTProto data access at scale: rate limits, Takeout, and parallelism

Research date: 2026-10-05. Method note: core.telegram.org, docs.telethon.dev and gotd.dev were blocked by this environment's egress proxy, so official-doc wording below comes from (a) search-engine snippets of core.telegram.org pages, (b) the Telegram Desktop source on GitHub (raw files read directly), and (c) Telethon's source and bundled error table (raw files read directly). Statements are tagged **[official]** (Telegram docs or Telegram's own client source/strings), **[library]** (maintainer-written library docs/source), or **[community]** (users, blogs, SEO sites). SEO-style blogs are treated as low-confidence.

Sizing for the example account (221 chats, ~500k messages). Every history or search call returns at most 100 messages, so reading 500k messages takes at least **5,000 requests**. Reading only the user's *own* sent messages with `messages.search(from_id=self)` costs (sent count / 100) requests.

---

## 1. How Telegram rate limits work (FLOOD_WAIT_X, FLOOD_PREMIUM_WAIT_X, SLOWMODE_WAIT_X, PEER_FLOOD): scope and evidence

### Takeaway
FLOOD_WAIT is a 420 error that tells the client how many seconds to wait. Telegram publishes no numeric limits and no official statement about scope. The best evidence says the limits are per account and per method, with extra IP-level and pattern-level anti-abuse checks layered on top, especially around login and when many accounts share one IP. Nothing official says that adding sessions or IPs for the *same account* gives you more read budget. One hard constraint: an auth key used from two IPs at once is permanently invalidated.

### Cited Findings
- **[official]** `FLOOD_WAIT_X` means "Please wait {value} seconds before repeating the action." `FLOOD_PREMIUM_WAIT_X` means "Please wait {value} seconds before repeating the action, or purchase a Telegram Premium subscription to remove this rate limit." (core.telegram.org/api/errors, via search snippet) — [Error handling](https://core.telegram.org/api/errors)
- **[library]** Telethon's error table describes the 420 family: `FLOOD_WAIT_X` "A wait of {seconds} seconds is required"; `FLOOD_PREMIUM_WAIT_X` "…required in non-premium accounts"; `SLOWMODE_WAIT_X` "…before sending another message in this chat"; `TAKEOUT_INIT_DELAY_X` "…before being able to initiate the takeout"; `FROZEN_METHOD_INVALID` (420) "a method that is not available for frozen accounts". `PEER_FLOOD` is a **400** error, "Too many requests". — [Telethon errors.csv](https://raw.githubusercontent.com/LonamiWebs/Telethon/v1/telethon_generator/data/errors.csv)
- **[library]** `AUTH_KEY_DUPLICATED` (406): "The authorization key (session file) was used under two different IP addresses simultaneously, and can no longer be used. Use the same session exclusively, or use different sessions." — [Telethon errors.csv](https://raw.githubusercontent.com/LonamiWebs/Telethon/v1/telethon_generator/data/errors.csv)
- **[library]** Telethon maintainer docs: "Nobody knows the exact limits for all requests since they depend on a lot of factors, so don't bother asking." By default the library auto-sleeps on flood waits shorter than 60 s. — [Telethon errors.rst](https://raw.githubusercontent.com/LonamiWebs/Telethon/v1/readthedocs/concepts/errors.rst)
- **[official, client behaviour]** Telegram Desktop's MTProto layer treats `FLOOD_WAIT_(\d+)` and `FLOOD_PREMIUM_WAIT_(\d+)` the same way: it re-queues the request to send after exactly `secs*1000+10` ms. It auto-retries `SLOWMODE_WAIT` only when the wait is under 3 s. For 5xx/internal errors it backs off 1 s and doubles up to about 60 s. The line `// if (secs >= 60) return false;` is commented out, so the official desktop client waits out flood waits of any length. — [tdesktop mtp_instance.cpp](https://raw.githubusercontent.com/telegramdesktop/tdesktop/dev/Telegram/SourceFiles/mtproto/mtp_instance.cpp)
- **[community]** `FLOOD_PREMIUM_WAIT_6` was first reported on `SaveBigFilePartRequest` (file upload) in July 2024, i.e. on file transfer rather than history reads. — [Telethon issue #4417](https://github.com/LonamiWebs/Telethon/issues/4417)
- **[community]** A Telethon user reported `FLOOD_WAIT` of 286 s on `contacts.ResolveUsername`, a method well known for strict limits. — [GitHub issue (autoclickers #71)](https://github.com/faxw3b/main-telegram-autoclickers/issues/71)
- **[community]** A TDLib user got `FLOOD_WAIT_30` when calling `getChats` plus `getChatHistory` (no maintainer answer visible). — [tdlib/td #743](https://github.com/tdlib/td/issues/743)
- **[community]** The question "are FLOOD_WAIT limits per account or per IP/proxy?" was asked on MadelineProto in July 2021, and no maintainer answer is visible. — [MadelineProto #996](https://github.com/danog/MadelineProto/issues/996)
- **[community, low confidence]** Blog claims (not backed by Telegram):
  - Limits apply to accounts or IP addresses, and Telegram "monitors… overall activity originating from a particular IP subnet".
  - Many sessions sending from one IP get "limits… reduced severalfold".
  - Retrying during a flood wait makes the block longer.
  - New accounts get stricter limits; aged and Premium accounts get higher thresholds.
  - [prmotion.me](https://prmotion.me/en/post/how-to-bypass-floodwait-limits-in-telegram-and-configure-stable-automation); [esimpy](https://esimpy.com/blog/telegram-flood-wait)
- **[community, low confidence]** One claim puts the TDLib user-account global ceiling at "~30 requests per second across all request types". It comes from an unofficial skills page with no primary source. — [skills.lc TDLib skill](https://skills.lc/xCyanGrizzly/DragonsStash/xcyangrizzly-dragonsstash-claude-skills-tdlib-telegram-skill-md)
- **[library FAQ]** Telethon FAQ:
  - Since 2023, "Telegram has started putting a lot more measures to prevent spam… some of the anti-spam measures have gotten more aggressive."
  - Use the library "only on well-established accounts".
  - Numbers from some countries (Iran, Russia) and VoIP numbers are more likely to be banned.
  - `PeerFloodError` means the account is limited; check with @SpamBot.
  - [Telethon FAQ](https://raw.githubusercontent.com/LonamiWebs/Telethon/v1/readthedocs/quick-references/faq.rst)

### Inferences
- The `X` in FLOOD_WAIT_X is the actual budget signal. A well-behaved client waits exactly X seconds; that is what tdesktop does. Hammering during a wait is the main way to turn a short wait into a long one (community claim, consistent with official advice to wait).
- PEER_FLOOD is about *sending to* or *adding* peers (spam limits), not reading. A read-only stats app should never see it. If it does, the account is already spam-limited.
- Because tdesktop retries FLOOD_PREMIUM_WAIT just like FLOOD_WAIT, a server can treat Premium users more leniently on some methods (so far seen on file transfer). The app should treat both the same way.
- Scope: per-method, per-account limits are the working assumption among library maintainers, but no official statement exists. IP-level effects are documented by the community mainly for **auth** (`PHONE_NUMBER_FLOOD`, sign-in waits) and for many accounts sharing one IP. That matters for a server that logs many users in from a few IPs. See §5.

### Gaps
- No official table of per-method limits exists, and I found no official statement of scope (per user, auth key, IP or DC). The core.telegram.org/api/errors page could not be fetched in full, so any extra wording there about scope or escalation is unverified.
- No first-party measurement of FLOOD_WAIT durations for `messages.getHistory`/`messages.search` from 2024–2026. Typical reported values (≈30 s for history/chat-list bursts; hundreds of seconds for resolveUsername) are anecdotal.

---

## 2. messages.getHistory vs messages.search (limits, filters, from_id=self in private chats)

### Takeaway
Both methods return at most 100 messages per call, and both page by offset_id/add_offset. The library rule of thumb is that history paging floods at roughly 10 requests per 30 s *sustained* (an old Telethon figure). Telegram's own exporter uses `messages.search` with `from_id = inputPeerSelf` to read only the user's own messages, which is good evidence that the filter is a supported path. I found no direct evidence about its exactness in 1:1 private chats.

### Cited Findings
- **[official, client source]** Telegram Desktop's exporter reads every chat in slices of `kMessagesSliceLimit = 100`, one request at a time per chat, using `messages.getHistory(peer, offset_id, add_offset=-100, limit=100)`.
- **[official, client source]** When `onlyMyMessages` is set, the exporter instead uses `messages.search(flags=from_id, peer, q="", from_id=inputPeerSelf, filter=Empty, min_date=0, max_date=0, offset_id, add_offset=-100, limit=100)`. It switches to that mode automatically when `getHistory` returns `CHANNEL_PRIVATE` (left/kicked channels).
- **[official, client source]** Supporting details from the same file: file chunk size is 128 KB with `kFileRequestsCount = 2` concurrent file requests; the `kFileNextRequestDelay` is commented out.
- Source for the three points above: [tdesktop export_api_wrap.cpp](https://raw.githubusercontent.com/telegramdesktop/tdesktop/dev/Telegram/SourceFiles/export/export_api_wrap.cpp)
- **[library]** Telethon `iter_messages` uses a chunk size of 100 (`_MAX_CHUNK_SIZE = 100`).
- **[library]** The docstring says: "Telegram's flood wait limit for GetHistoryRequest seems to be around 30 seconds per 10 requests, therefore a sleep of 1 second is the default for this limit."
- **[library]** The library only applies the 1 s wait when `limit > 3000` ("retrieving more than 3000 messages will take longer than half a minute"). For `ids=` lookups it uses 10 s if more than 300 are requested.
- Source for the three points above: [Telethon messages.py](https://raw.githubusercontent.com/LonamiWebs/Telethon/v1/telethon/client/messages.py)
- **[library]** Telethon docs: "If either search, filter or from_user are provided, messages.Search will be used instead of messages.getHistory". Searches run server-side, "so the rules for how it works are also fuzzy". — [Telethon client docs](https://docs.telethon.dev/en/stable/modules/client.html) (via search snippet)
- **[official]** TDLib `getChatHistory`: limit "can't be greater than 100"; results are newest first. — [TDLib getChatHistory](https://core.telegram.org/tdlib/docs/classtd_1_1td__api_1_1get_chat_history.html) (via search snippet)
- **[repo]** This codebase already relies on `messages.search(from_id=InputPeerSelf, min_date, max_date)`, using the `count` field for exact sent totals per dialog. It falls back to the non-takeout client when a search inside takeout is rejected with a TAKEOUT error. — `backend/app/fetcher.py` (lines ~320–355)

### Inferences
- **Reading everything (both sides) costs ≥5,000 getHistory calls for 500k messages.** Reading only own messages costs (own_sent/100) search calls; typically own messages are ~30–50% of a chat (an assumption, not sourced). Search also returns an exact `count` in one cheap call (`limit=1`). That makes it the most cost-effective way to get exact totals.
- The "30 s per 10 requests" figure (~0.33 req/s ≈ 33 msg/s) dates from Telethon's early years (circa 2018) and is very conservative compared with the desktop export benchmark in §4 (≈300–550 msg/s). It should be treated as a worst case, not the norm.
- Telegram's exporter uses search with from_id=self as a production path, so the filter is not an unsupported trick. Its behaviour in private chats is not specifically documented. The repo's `tests/fake_telegram.py` *assumes* exactness; this should be checked on real accounts (e.g. compare search `count` with a full getHistory walk on a few 1:1 chats via `scripts/live_check.py`).

### Gaps
- No source found comparing the flood cost of `messages.search` vs `messages.getHistory` directly (whether search is weighted more heavily server-side). Community lore says searches flood sooner, but I found no citable measurement.
- No verified statement about whether `min_date`/`max_date` on `messages.search` are inclusive or exclusive, or whether they combine exactly with `from_id` in private chats. The official method pages could not be fetched.

---

## 3. Takeout (account.initTakeoutSession / invokeWithTakeout / TAKEOUT_INIT_DELAY_X)

### Takeaway
Takeout is Telegram's official export path, and libraries say some calls inside it get lower flood limits. But a session that has just been logged in (exactly the case for a web app doing phone-code login) normally gets `TAKEOUT_INIT_DELAY_X` of up to 24 h. Telegram notifies all of the user's devices. The delay can be skipped only if the user approves the export on another, older device. For an "instant" web app, takeout is opportunistic at best.

### Cited Findings
- **[official]** To use takeout, call `account.initTakeoutSession` with flags for what will be exported (contacts, private-chat messages, basic groups, supergroups, channels, files with optional max size). Then wrap every query in `invokeWithTakeout(takeout_id, query)`, including `upload.getFile`. Finish with `account.finishTakeoutSession`, also wrapped. — [Takeout API](https://core.telegram.org/api/takeout); [invokeWithTakeout](https://core.telegram.org/method/invokeWithTakeout); [account.initTakeoutSession](https://core.telegram.org/method/account.initTakeoutSession) (via search snippets)
- **[official, client string]** Telegram Desktop's delay message: "For security reasons, you will be able to begin downloading your data in {hours}. We have notified all your devices about the export request to make sure it's authorized and give you time to react if it's not. Please come back on {date} and repeat the request using the same device." — [tdesktop lang.strings](https://raw.githubusercontent.com/telegramdesktop/tdesktop/dev/Telegram/Resources/langs/lang.strings)
- **[community]** "As a safeguard against account takeovers, Telegram blocks data export for 24 hours after you sign in on a new device… you will either have to wait for 24 hours – or confirm the export request from another device and begin downloading your data immediately." — [mosaicchats guide (2026)](https://www.mosaicchats.com/blog/how-to-export-telegram-chat) (via search snippet); see also [tdesktop #8609](https://github.com/telegramdesktop/tdesktop/issues/8609), [bugs.telegram.org/c/60](https://bugs.telegram.org/c/60)
- **[official, client source]** tdesktop sends `account.initTakeoutSession` on a **separate export connection** (`toDC(MTP::ShiftDcId(0, MTP::kExportDcShift))`). It sets flags from the user's selection: `message_users`, `message_chats`, `message_megagroups`, `message_channels`, `files`, `file_max_size`, `contacts`. After that, it wraps everything in `MTPInvokeWithTakeout`, including `messages.search` for the only-my-messages mode, and finishes with `account.finishTakeoutSession(success)`. — [tdesktop export_api_wrap.cpp](https://raw.githubusercontent.com/telegramdesktop/tdesktop/dev/Telegram/SourceFiles/export/export_api_wrap.cpp)
- **[library]** Telethon `client.takeout()` docstring: "Some of the calls made through the takeout session will have lower flood limits… since the rate limits will be lower. Only some requests will be affected, and you will need to adjust the `wait_time` of methods like `client.iter_messages`. You should `except errors.TakeoutInitDelayError as e`… access `e.seconds`." — [Telethon account.py](https://raw.githubusercontent.com/LonamiWebs/Telethon/v1/telethon/client/account.py)
- **[library]** Error semantics: `TAKEOUT_INIT_DELAY_X` (420) "A wait of {seconds} seconds is required before being able to initiate the takeout"; `TAKEOUT_INVALID` (400) "invalidated by another data export session"; `TAKEOUT_REQUIRED` (400/403) "You must initialize a takeout request first". — [Telethon errors.csv](https://raw.githubusercontent.com/LonamiWebs/Telethon/v1/telethon_generator/data/errors.csv)
- **[community]** Takeout delays happen "depending on the condition of the session" (Telethon). gotd's floodwait middleware recognises `TAKEOUT_INIT_DELAY` and waits it out. — [gotd data-export docs](https://gotd.dev/docs/advanced/data-export/) (via search snippet)
- **[repo]** This repo defaults to `USE_TAKEOUT=1` with `TAKEOUT_MAX_WAIT=0` (use takeout only if granted immediately). It has seen servers reject `messages.search` inside takeout. — `.env.example`, `backend/app/fetcher.py`

### Inferences
- In a fresh phone-code login (this app's flow), expect `TAKEOUT_INIT_DELAY_X` most of the time. Many users will also get a "data export requested" notice on their phone. That notice could be alarming in a consumer stats app and should be explained in the UI, or takeout should be skipped.
- Takeout's benefit is described only as "lower flood limits for some calls", with no published numbers. The desktop exporter still runs **sequentially** (one 100-message slice in flight per chat) even inside takeout. So takeout makes waits rarer rather than making each request faster.
- Starting a second takeout invalidates the first (`TAKEOUT_INVALID`). Parallel machines each opening their own takeout for the same account would fight each other.

### Gaps
- I found no official number for the delay length (24 h is community-reported and consistent with the official string's "{hours}/{date}"). I also found no rule for which sessions are exempt (session age? device trust?).
- No official list of which methods get relaxed limits inside takeout, and no measured speed-up factor.
- No source confirms whether `messages.search` is officially allowed inside takeout. tdesktop does it, but this repo has observed rejections.

---

## 4. Realistic throughput numbers (desktop export, Telethon, Pyrogram, TDLib)

### Takeaway
Hard numbers are scarce. The best datapoint is a Telegram Desktop export report: 10,000 messages read in 18 s on one account and 34 s on another (≈300–550 msg/s, ≈3–5.5 requests/s sequentially). At those rates 500k messages take ~15–28 min. The conservative library rule (10 requests per 30 s) gives ~4 h. Server-side pacing differs per account.

### Cited Findings
- **[community]** "Telegram A takes only 18 seconds to read 10000 messages. Telegram B takes 34 seconds to read 10000 messages", reported during a desktop export. No maintainer explanation was given. — [tdesktop #8533](https://github.com/telegramdesktop/tdesktop/issues/8533)
- **[community, 2022]** Media download inside "Export chat history" ran at ~2 MB/s vs ~9 MB/s for a normal "Save as", which suggests separate pacing for export file transfers. No maintainer reply. — [tdesktop #24828](https://github.com/telegramdesktop/tdesktop/issues/24828)
- **[library]** Telethon: getHistory flood limit "seems to be around 30 seconds per 10 requests"; "retrieving more than 3000 messages will take longer than half a minute". A later changelog says `iter_messages` was "optimized to be faster by sleeping only as much as needed" and auto-retries `RpcCallFailError`, "which happened frequently when iterating over many messages". — [Telethon messages.py](https://raw.githubusercontent.com/LonamiWebs/Telethon/v1/telethon/client/messages.py); [Telethon changelog](https://docs.telethon.dev/en/stable/misc/changelog.html) (snippet)
- **[community, low confidence]** An SEO blog claims Telegram Desktop "writes 1 million messages to JSON in 6 minutes 42 seconds" on an M2 MacBook Air, and that export time fell from 68 min to 7 min with media disabled. It has no methodology and mentions SQLite, which the tdesktop exporter does not use. Treat as unreliable. — [pcg-telegram blog](https://pcg-telegram.com/blogs/1207122357/)

### Inferences
- Back-of-envelope for 500k messages:
  - Conservative (0.33 req/s): 5,000 calls ≈ 4.2 h.
  - Telethon default pacing (1 req/s): ≈ 83 min.
  - Desktop-export observed (3–5.5 req/s): ≈ 15–28 min.
  - Own messages only via search (if ~150–250k sent, assumed): divide by ~2–3.
- The current repo budget (`TG_PAGE_BUDGET=600` pages, 60k messages; `TG_FETCH_DEADLINE=75` s) implies ~8 req/s. That is already above the desktop-export observation, which explains why estimated mode is needed for large accounts.
- Data export speed is probably dominated by server-side pacing (one in-flight request plus FLOOD_WAITs), not client CPU. Disabling media helps mainly because file downloads are slow and paced separately.

### Gaps
- No reliable 2024–2026 benchmarks for Pyrogram `get_chat_history`, TDLib `getChatHistory` or GramJS at the 100k–1M scale. No citable measurement of the requests/s at which `messages.getHistory` starts returning FLOOD_WAIT, or of how long the waits are.
- Unknown whether reading different chats concurrently (N parallel requests on one connection) is penalised per account. Recommended: measure with `scripts/live_check.py` on 2–3 real accounts, logging the req/s, the first FLOOD_WAIT X value, and the total time.

---

## 5. Would parallel machines / different IPs / multiple sessions for the same user help? Risks and Terms of Service

### Takeaway
Probably not, and it adds real risk. Each extra machine needs its own auth key, which means another login: a new code SMS or in-app code, a new "new login" notification, and another young session under watch. Reusing one session from two IPs at once triggers `AUTH_KEY_DUPLICATED`, which permanently kills the session. Flood limits are believed to be per account, so extra sessions add suspicion without adding budget. The Terms put all third-party-client accounts "under observation" and ban flooding.

### Cited Findings
- **[library]** `AUTH_KEY_DUPLICATED` (406): the session "was used under two different IP addresses simultaneously, and can no longer be used." — [Telethon errors.csv](https://raw.githubusercontent.com/LonamiWebs/Telethon/v1/telethon_generator/data/errors.csv)
- **[official]** API Terms (via search snippets): "If you use the Telegram API for flooding, spamming, faking subscriber and view counters of channels, you will be banned forever." "All accounts that log in using unofficial Telegram API clients are automatically put under observation to avoid violations of the Terms of Service." Client apps "must guard their users' privacy with utmost care". — [Telegram API Terms of Service](https://core.telegram.org/api/terms)
- **[official, needs verification]** API Terms (via search snippet) prohibit "using, accessing or aggregating data obtained from the Telegram platform to train, fine-tune or otherwise engage in the development, enhancement or deployment of artificial intelligence, machine learning models and similar technologies." — [Telegram API Terms of Service](https://core.telegram.org/api/terms); summarised by a secondary site as prohibiting use of Telegram data "to develop, train, benchmark, or otherwise build AI or machine-learning systems" — [telegramscraper.shop (2026)](https://telegramscraper.shop/blog/is-telegram-scraping-legal)
- **[official, via search snippet]** Client developers must use their own api_id and must not force users of other clients to download their app; monetisation must be disclosed. — [Telegram API Terms of Service](https://core.telegram.org/api/terms); [Creating your Telegram Application](https://core.telegram.org/api/obtaining_api_id)
- **[community]** Logging several accounts into one IP/device in a short window "can trigger FLOOD_WAIT", because Telegram watches patterns across accounts. Users of multi-account forwarders ask to rotate accounts *because* one account's flood wait doesn't transfer to the others, which implies per-account limits. — [esimpy](https://esimpy.com/blog/why-telegram-says-too-many-attempts); [tgcf #30](https://github.com/aahnik/tgcf/issues/30)
- **[community]** Multiple consumers on one account/session cause "update stealing and FLOOD_WAIT". — [better-tg-cli #5](https://github.com/TheVilfer/better-tg-cli/issues/5)
- **[official, client source]** The official desktop client itself opens an extra connection (`kExportDcShift`) on the *same* auth key for export. Several MTProto connections per auth key from one IP is normal client behaviour. — [tdesktop export_api_wrap.cpp](https://raw.githubusercontent.com/telegramdesktop/tdesktop/dev/Telegram/SourceFiles/export/export_api_wrap.cpp)
- **[library]** Telethon FAQ: since 2023 anti-spam "gotten more aggressive"; use only well-established accounts; VoIP and some country numbers are banned more readily. — [Telethon FAQ](https://raw.githubusercontent.com/LonamiWebs/Telethon/v1/readthedocs/quick-references/faq.rst)

### Inferences
- **Parallelism inside one session is the safe lever.** Several concurrent requests across *different chats* on one auth key, from one server IP, with AIMD backoff on FLOOD_WAIT, is what the repo's `AdaptiveThrottle` does. It resembles official client behaviour (the exporter plus a separate export connection).
- **Multiple machines for one user** would each need a separate login. Each login is a new code, a new device notification and a new fresh session, possibly with a takeout delay. Each also adds a new IP to the account's history. If limits are per account (best evidence), total throughput is unchanged, and the pattern of one account logging in from N datacenter IPs within seconds looks like account takeover or abuse.
- **Proxying through different IPs per user** (one IP per user, not per request) may lower *auth-time* IP-level flood risk when many users log in from one server (PHONE_NUMBER_FLOOD and sign-in waits are known to be IP-sensitive per the community). It is unlikely to speed up reading one user's history.
- Risks to weigh, in order: a permanent session kill (AUTH_KEY_DUPLICATED); the account being flagged or limited (observation of unofficial clients plus abuse heuristics); a "permanent ban" clause for flooding. These are reputational and legal risks for a consumer app whose users' own accounts are at stake.
- ToS implication for the product: the app's current deterministic stats are fine. Any plan to send users' messages to an LLM or ML model ("deployment of AI/ML") may conflict with the AI clause and needs a legal read of the full current terms text.

### Gaps
- I could not fetch the full API Terms text, so section numbers and exact wording beyond the snippets are unverified. In particular, I found nothing on whether server-side phone-code login on behalf of users is specifically addressed.
- No official statement says whether flood limits are tracked per auth key or per user ID. The per-account conclusion rests on library behaviour and community reports.

---

## 6. Restrictions on freshly logged-in sessions and what they mean for a "log in fresh each time" web app

### Takeaway
A new session works for reading history and search right away. It is blocked for some sensitive actions (terminating other sessions, changing phone, changing admins) for about 24 h, and data export via Takeout is usually delayed about 24 h unless approved from another device. Every login notifies the user's other devices. For this app, plan on no takeout, a careful but steady read rate, and clear UX about the login and any export notifications.

### Cited Findings
- **[official]** You cannot log out other sessions if fewer than 24 hours have passed since the current session logged in (`account.resetAuthorization` → `FRESH_RESET_AUTHORISATION_FORBIDDEN`). — [account.resetAuthorization](https://core.telegram.org/method/account.resetAuthorization) (via search snippet); [bugs.telegram.org/c/218](https://bugs.telegram.org/c/218)
- **[library]** Other "fresh session" errors: `FRESH_CHANGE_PHONE_FORBIDDEN` (406) "Recently logged-in users cannot use this request"; `FRESH_CHANGE_ADMINS_FORBIDDEN` (400/406); generic `SESSION_TOO_FRESH_X` (400) "The session logged in too recently and {seconds} seconds must pass before calling the method". — [Telethon errors.csv](https://raw.githubusercontent.com/LonamiWebs/Telethon/v1/telethon_generator/data/errors.csv)
- **[official, client string]** On export requests, Telegram has "notified all your devices about the export request"; the user is told to "come back on {date}… using the same device". — [tdesktop lang.strings](https://raw.githubusercontent.com/telegramdesktop/tdesktop/dev/Telegram/Resources/langs/lang.strings)
- **[community]** Export is blocked for 24 h after sign-in on a new device unless confirmed from another device. — [mosaicchats guide](https://www.mosaicchats.com/blog/how-to-export-telegram-chat) (snippet)
- **[library]** Auth-related limits: `PHONE_NUMBER_FLOOD` (400) "You asked for the code too many times"; `SEND_CODE_UNAVAILABLE` (406) when all delivery options are used; `SESSION_PASSWORD_NEEDED` (401) for 2FA. — [Telethon errors.csv](https://raw.githubusercontent.com/LonamiWebs/Telethon/v1/telethon_generator/data/errors.csv)
- **[repo]** The app revokes the authorization (`log_out`) after the pipeline finishes, and revokes unused logins after `SESSION_TTL`. — `CLAUDE.md` / `backend/app/telegram_service.py`

### Inferences
- `log_out` of its *own* session is allowed for a fresh session. Only resetting *other* sessions is restricted, so the app's post-run revoke is fine.
- Each run is a fresh session, so the app never benefits from session "maturity". If the product wants takeout's relaxed limits, the only reliable route is to tell users to approve the export prompt on their phone, which takes them out of the flow. Keep `TAKEOUT_MAX_WAIT=0` as the default.
- Repeated runs for the same user (re-logins) each send a code and a new-login notification. Rate-limit re-runs per phone (the repo already caps send-code at 3 per phone per 10 min) to avoid `PHONE_NUMBER_FLOOD` and to avoid looking like credential stuffing.

### Gaps
- No official list of every method gated by session freshness, and no confirmation of whether `messages.search` or `getHistory` rate limits are stricter for young sessions. That is community belief only (e.g. "new profiles… strict restrictions" in [prmotion.me](https://prmotion.me/en/post/how-to-bypass-floodwait-limits-in-telegram-and-configure-stable-automation), which is about new *accounts* and mass messaging, not new sessions or reading).
