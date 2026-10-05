# Architecture options for Telegram Wrapped: export upload vs. in-browser MTProto vs. server-side workers

Research notes, Oct 2026. Network caveat: core.telegram.org, kaspersky.com, lapcatsoftware.com, rewindfy.com, wrap2025.com and abit.ee were blocked by the research environment's egress proxy. Claims attributed to those pages come from search-result snippets, not full-page reads, and are marked "(snippet)". Treat them as lower confidence.

Internal context (from this repo, not the web): the current backend uses `TG_PAGE_BUDGET=600`, `TG_FETCH_DEADLINE=75` (seconds) and `MAX_CONCURRENT_PIPELINES=8` per instance (`.env.example`). Above the page budget it switches to an "estimated" mode. In other words, the current design already gives up some exactness to stay fast.

## (a) Official export (Telegram Desktop "Export Telegram data", JSON) + client-side parsing

### Takeaway
The official JSON export has nearly every field a Wrapped needs: timestamps, sender IDs, edits, replies, forwards, media types, sticker emoji, text entities and reactions. Because it contains the full cloud history, it is the most accurate source. The friction is high, though. Full export is Desktop-only, a fresh desktop login has a security hold of up to 24 h unless another device approves it, and big accounts produce very large JSON files that mobile Safari cannot reasonably parse. It works well as a "privacy/accuracy mode", but poorly as the main mobile funnel.

### Cited Findings
- The full-account export has been available since Telegram Desktop added "Settings > Export Telegram data". It produces data "accessible offline in JSON-format or in beautifully formatted HTML" — [Telegram blog: Chat Export Tool](https://telegram.org/blog/export-and-more) (snippet via search)
- Top-level `result.json` keys written by the exporter (from current tdesktop source): `about`, `personal_information`, `profile_pictures`, `stories`, `profile_music`, `contacts`, `frequent_contacts`, `sessions`, `web_sessions`, and `chats` / `left_chats` (dialog arrays) — [tdesktop export_output_json.cpp](https://raw.githubusercontent.com/telegramdesktop/tdesktop/dev/Telegram/SourceFiles/export/output/export_output_json.cpp)
- Per-message fields (same source):
  - Core: `id`, `type`, `date`, `date_unixtime`, `edited`, `edited_unixtime`.
  - Sender: `from`, `from_id`, `author`, `actor` (service messages).
  - Relations: `reply_to_message_id`, `reply_to_peer_id`, `forwarded_from`, `forwarded_from_id`, `forwarded_from_name`, `saved_from`, `via_bot`.
  - Content: `text`, `text_entities`, `rich_message`.
  - Media: `photo`, `photo_file_size`, `width`, `height`, `file`, `file_name`, `file_size`, `thumbnail`, `media_type`, `mime_type`.
  - Other: `inline_bot_buttons`, `reactions` (emoji, count, recent).
  - [tdesktop export_output_json.cpp](https://raw.githubusercontent.com/telegramdesktop/tdesktop/dev/Telegram/SourceFiles/export/output/export_output_json.cpp)
- `media_type` values are `sticker`, `video_message`, `voice_message`, `animation`, `video_file` and `audio_file`. Service-message `action` values include `create_group`, `invite_members`, `pin_message`, `phone_call`, `take_screenshot`, `migrate_to_supergroup` and many more — [tdesktop export_output_json.cpp](https://raw.githubusercontent.com/telegramdesktop/tdesktop/dev/Telegram/SourceFiles/export/output/export_output_json.cpp)
- Media files can be left out. When media download is disabled, `result.json` still keeps metadata and placeholder values — [EChat (Desktop-compatible JSON exporter)](https://github.com/MohammadLarki/EChat); [chatexport.guide](https://chatexport.guide/guides/telegram/) (snippets)
- The full export is Desktop-only, and the mobile apps do not have it — [androidpolice](https://www.androidpolice.com/telegram-export-chats-groups-channels-images/); [takeoutday.org](https://takeoutday.org/guides/how-to-export-telegram-data) (snippets, secondary sources)
- Telegram applies a security hold to exports. After a new sign-in, export is blocked for up to 24 h unless the request is approved from an already-logged-in device. That approval request is sent to all of the user's devices — [invitemember blog](https://blog.invitemember.com/how-to-export-telegram-chat-history/); [ihaveapc](https://ihaveapc.com/2024/12/how-to-export-personal-data-using-telegram-desktop/) (snippets)
- A first-hand user report (Sept 2020, tdesktop issue) describes the flow as: Settings > Advanced > Export > "Mobile approval" > wait 24 hours > download. The export then failed with an error dialog — [tdesktop #8609](https://github.com/telegramdesktop/tdesktop/issues/8609)
- Unlike WhatsApp's 40,000-message chat-export cap, Telegram exports a chat's full cloud history. Large chats "may take several minutes" — [secondary guides via search](https://www.such.chat/blog/how-to-backup-telegram-chats) (snippet; no authoritative timing data found)
- Many existing open-source Telegram analyzers consume `result.json`, and several run fully in the browser:
  - [telegram-chat-analyser](https://github.com/nualimov/telegram-chat-analyser): "locally in your browser".
  - [Telegramalyzer](https://telegramalyzer.github.io/Telegramalyzer/) and [telegram.graphics](https://charludo.github.io/telegram.graphics/): static GitHub Pages sites.
  - [tg-analyzer](https://github.com/Dugit0/tg-analyzer): Python, generates an HTML report.
  - [Telegram-Conversation-Behavioral-Analyzer](https://github.com/AFA06/Telegram-Conversation-Behavioral-Analyzer): the user sends the result.json to a bot, so the server sees the data.
- Streaming JSON parsing in the browser: `@streamparser/json` is a "fast dependency-free library to parse a JSON stream… in Node.js, Deno or any modern browser". It is fully spec-compliant and has a WHATWG TransformStream flavour (`@streamparser/json-whatwg`) that can be fed by `File.stream()` inside a Web Worker — [streamparser-json GitHub](https://github.com/juanjoDiaz/streamparser-json)
- Mobile Safari memory limits:
  - iOS Safari terminates tabs much more aggressively than desktop browsers. A Jan 2026 article reports pages crashing around ~100 MB on an iPhone and ~200 MB on an iPad — [Lap Cat Software, "Mobile Safari web pages are severely limited by memory" (2026)](https://lapcatsoftware.com/articles/2026/1/7.html) (snippet)
  - When WASM `memory.grow()` exceeds the limit, Safari kills the whole tab without warning — [WebKit bug 221530](https://bugs.webkit.org/show_bug.cgi?id=221530) (snippet)
  - Godot reports OOM on iOS Safari 16.2 with a 2 GB max Wasm memory — [godot #70621](https://github.com/godotengine/godot/issues/70621) (snippet)

### Inferences
- For a Wrapped, a JSON export with media excluded is complete for counts, timing, replies, edits, forwards, stickers (`media_type: sticker` + `sticker_emoji`), reactions and phrases. Accuracy would be exact (no sampling), which beats the current server's "estimated mode".
- Known gaps in the export compared with live MTProto:
  - Avatars and thumbnails only come along if media is included.
  - Deleted messages and secret chats are absent.
  - Reaction detail shows only "recent" reactors.
  - Users must pick the chat types (private, groups, etc.) correctly in the export dialog. If they don't, results silently drop chats.
- The `result.json` for a heavy user can plausibly be hundreds of MB to several GB. I found no authoritative size statistics (see Gaps).
- Parsing therefore needs to be streaming: a `File.stream()` → `@streamparser/json` (or a WASM SAX parser) pipeline in a Worker that emits per-message records and aggregates on the fly, never holding the whole tree. Desktop Chrome/Firefox can handle this.
- On iPhone, the export is not even producible, and a 500 MB+ JSON file would be hard to get onto the phone. Mobile users would need a desktop step, which makes this a high-friction, desktop-first flow.
- The 24 h hold mainly hits users who don't already run Telegram Desktop. Existing Desktop users, plus anyone who taps "approve" on their phone, can export immediately.
- Option (a) gives the strongest privacy story ("no server ever sees messages"). That claim is easy to verify with an open-source, static, offline-capable page. It is also the dominant pattern among WhatsApp analyzers (see the products section).

### Gaps
- No authoritative data on export duration or `result.json` size for large accounts. Telegram does not publish it, and I found only anecdotal "several minutes" claims. This should be measured on a real heavy account.
- I could not confirm whether the 24 h hold applies to every Desktop session or only to newly authorized ones. Secondary sources say "new device".
- I could not verify the exact current Desktop UI path or whether the HTML/JSON "Export chat history" per-chat option exists on mobile. Some 2026 guides title themselves "(Desktop & Mobile)", but the snippets say mobile has no full export.
- No browser benchmark found for parse throughput (MB/s) of `@streamparser/json` vs. alternatives. It needs a local benchmark.

## (b) MTProto client in the user's browser (GramJS / teleproto / tdweb; as Telegram Web K/A do)

### Takeaway
Running MTProto in the browser is proven: both official web clients do it over Telegram's `wss://*.web.telegram.org/apiws` endpoints. It would keep the session on the user's device and spread compute and rate limits across users. The main risks are library maturity and the trust model. GramJS was archived in July 2026 (successor: teleproto), tdweb is a hard-to-build Emscripten artifact, and users still type their phone code into a third-party web page. The server can't see the session, but the user can't verify that.

### Cited Findings
- Telegram Web A (web.telegram.org/a, the official client that won the Telegram Lightweight Client Contest) "uses a custom version of GramJS as an MTProto implementation", together with WebSockets, Web Workers and WebAssembly — [Ajaxy/telegram-tt](https://github.com/Ajaxy/telegram-tt) (snippet)
- Telegram Web K runs MTProto 2.0 inside a Web Worker so crypto and serialization don't block the UI. It supports WebSocket and HTTPS transports — [DeepWiki on a Web K fork](https://deepwiki.com/loyldg/mytelegram-webk) (snippet; secondary)
- Per Telegram's transport docs, the WebSocket URI form is `…:80/api(w)(s)`, where `w` adds CORS headers for browser use and `s` enables WebSocket. The browser endpoints used in practice are `wss://{pluto,venus,aurora,vesta,flora}.web.telegram.org/apiws`, carrying obfuscated intermediate MTProto — [core.telegram.org transports](https://core.telegram.org/mtproto/transports) (snippet; direct fetch blocked); [tg-ws-relay](https://github.com/cakson/tg-ws-relay) (snippet)
- GramJS "is archived and no longer maintained as of July 14, 2026". The README points to the fork [teleproto](https://github.com/sanyok12345/teleproto) "with minimal code changes". GramJS has ~1.8k stars. It is bundled for browsers with webpack, uses localStorage to cache layers in browsers, and supports `StringSession` — [gram-js/gramjs README](https://github.com/gram-js/gramjs)
- Third-party browser projects use teleproto ("actively maintained GramJS fork with up-to-date TL layers") over MTProto WebSocket, sometimes through a Cloudflare proxy — [TG-WebApp-Proxy](https://github.com/hllfcknwrld/TG-WebApp-Proxy) (snippet)
- tdweb is TDLib compiled to WASM with Emscripten and packaged for npm. The build is pinned to emsdk 3.1.1 ("known to work"), and the README warns against the system emscripten package — [tdlib/td example/web](https://github.com/tdlib/td/tree/master/example/web)
- The tdlib repo has open issues about MTProto-over-WS connections — [tdlib/td #1491](https://github.com/tdlib/td/issues/1491)
- Telegram API Terms §2.1: every app must obtain its own api_id. The sample api_id in open-source code is server-limited and causes `API_ID_PUBLISHED_FLOOD` for real users — [core.telegram.org obtaining_api_id](https://core.telegram.org/api/obtaining_api_id) (snippet)
- Using official clients' api_id/hash in third-party apps can trigger enforcement — [Grokipedia summary](https://grokipedia.com/page/Official_Telegram_client_API_ID_and_API_hash) (snippet; tertiary source)
- Accounts logging in through unofficial API clients are "automatically put under observation". Flooding or spamming leads to a permanent ban — [core.telegram.org obtaining_api_id](https://core.telegram.org/api/obtaining_api_id) (snippet)
- Telegram is reportedly testing an in-chat warning label for users of unofficial clients after the 2026 "Telega" scandal. In that case, a Russian third-party client was found to ship an extra RSA key that enabled MITM through VK-linked infrastructure, Apple flagged it as malicious, and it was pulled from the App Store in April 2026 — [abit.ee](https://abit.ee/en/soft/messengers/telegram-unofficial-client-security-warning-telega-mitm-ios-messenger-security-third-party-client-ru-en) (snippet, "not officially announced"); [Meduza, 2026-04-17](https://meduza.io/en/news/2026/04/17/report-apple-warns-russian-iphone-users-that-unofficial-telegram-client-telega-contains-malicious-code) (snippet); [opennet.ru](https://www.opennet.ru/opennews/art.shtml?num=65063)

### Inferences
- An api_id in client-side JS is normal and unavoidable. Every open-source client and every web client ships its api_id/hash in its code. The ToS requirement is that the app uses *its own* api_id, not that the api_id stays secret. A browser build of this app would expose the same api_id the server uses today.
- Rate limits: FLOOD_WAIT is enforced per account/authorization and per method on Telegram's side. Client location should not change the limits, so in-browser fetching is as fast as server-side fetching for a single user. Total throughput scales with users because each user's limits and network are independent. (No primary source found that explicitly states the limits are identical. This is inferred from how FLOOD_WAIT works per user.)
- Telegram may also apply per-api_id or per-IP heuristics. Moving to the browser spreads requests across user IPs instead of concentrating them on a few server IPs, which plausibly *reduces* anti-abuse risk.
- Most of the current Python pipeline (fetcher/throttle/stats/ml/phrases) would need porting to TS, or running via Pyodide/WASM. That is a major rewrite.
- Mobile Safari memory limits (see (a)) apply here too. But the pipeline streams small pages (100 messages), so the risk is lower than parsing a giant JSON file. Backgrounding the tab on iOS can kill the WebSocket mid-run, so checkpointing to IndexedDB matters.
- Privacy is better than (c), but the claim is weaker than (a): the page *could* exfiltrate the session, and users can't tell. Open-sourcing, CSP and reproducible static builds help. The new "unofficial client" warning label (if it ships) might also show up for this app's api_id.
- Session lifecycle: after the run, the client should call `auth.logOut`, as the server does today, to avoid leaving an orphaned authorization in the user's device list.

### Gaps
- No bundle-size numbers found for GramJS/teleproto or tdweb (bundlephobia not checked). Experience suggests GramJS ≈ 1+ MB minified and tdweb's WASM several MB, but this is unverified and needs measuring.
- No primary Telegram statement on whether rate limits differ by client IP, api_id or transport.
- The core.telegram.org pages could not be fetched directly. The obtaining_api_id quotes come from search snippets.
- teleproto's maturity (release cadence, layer currency, browser test coverage) was not evaluated.

## (c) Server-side workers holding sessions (current approach)

### Takeaway
This is the fastest to ship and works on every device, but the server ends up holding live account-takeover credentials. An MTProto auth key is equivalent to a logged-in device: it bypasses 2FA, and it doesn't expire until revoked. Throughput is bounded by Telegram's per-account flood limits and the server's IP reputation, not by CPU. Compute cost per user is small, while the security and trust cost is large.

### Cited Findings
- A stolen Telegram Desktop `tdata` folder lets attackers "impersonate victims without needing passwords or bypassing Two-Factor Authentication". Session tokens "do not expire automatically… remain usable indefinitely until the victim manually terminates all active sessions" — [telegram-session-hijacking-research](https://github.com/kamronsaparbaev/telegram-session-hijacking-research) (snippet)
- Infostealers (RedLine, Raccoon, Phemedrone, TdataS) specifically target Telegram session data — [SANS ISC diary](https://isc.sans.edu/diary/Guest+Diary+Beyond+Cryptojacking+Telegram+tdata+as+a+Credential+Harvesting+Vector+Lessons+from+a+Honeypot+Incident/32888/); [TdataS analysis](https://maordayanofficial.medium.com/tdatas-stealer-from-c2-discovery-to-operator-attribution-via-operational-security-failures-d11d78cc8e85); [Kaspersky blog](https://www.kaspersky.com/blog/telegram-no-password-session-stealer/56006/) (snippets)
- Attackers "don't crack Telegram 2FA — they copy your already logged-in session"; 2FA only protects *new* authorizations — [CyberSecurityNews](https://cybersecuritynews.com/hackers-crack-telegram-2fa/) (snippet)
- A malicious PyPI package harvested Telegram sessions for sale on dark markets. Telegram identities are a traded commodity — [Imperva](https://www.imperva.com/blog/from-pypi-to-the-dark-marketplace-how-a-malicious-package-fuels-sale-of-telegram-identities/) (snippet)
- The Telega case (2026) shows the reputational fallout when a third party sits in the path of users' Telegram sessions. Telegram's reported response is to label unofficial clients — [Meduza](https://meduza.io/en/news/2026/04/17/report-apple-warns-russian-iphone-users-that-unofficial-telegram-client-telega-contains-malicious-code); [abit.ee](https://abit.ee/en/soft/messengers/telegram-unofficial-client-security-warning-telega-mitm-ios-messenger-security-third-party-client-ru-en) (snippets)
- Telethon users report accounts banned shortly after creating a session — [Telethon #3861](https://github.com/LonamiWebs/Telethon/issues/3861) (title only)

### Inferences
- The server holding sessions means a breach of Redis plus `SESSION_ENCRYPTION_KEY` would hand over every in-flight account (full read and write access, sending as the user, all chats). The current mitigations limit the exposure window to minutes, which is good practice but does not remove the trust problem:
  - Fernet encryption at rest.
  - `log_out` right after the pipeline.
  - TTL cleanup of unused logins.
- Phone-number + OTP entry on a third-party site is also exactly the pattern of Telegram phishing. Users and security-savvy commentators are primed to distrust it, which likely costs conversion and virality. This is an inference; I found no measured drop-off data.
- Scaling: compute per user is light (tens of seconds of mostly I/O wait plus seconds of CPU for stats). At 10k users the dominant constraints are:
  - Telegram's per-account FLOOD_WAITs, which make each user's run take tens of seconds regardless of hardware.
  - Possible per-IP / per-api_id anti-abuse heuristics when thousands of logins come from a few datacenter IPs.

  `MAX_CONCURRENT_PIPELINES=8` per instance means 100k users in a viral spike need many instances or long queues. (Order-of-magnitude reasoning, not a sourced figure.)
- Rough cost model (inferred, unverified): if a run averages ~60–90 s of wall time at ~8 concurrent per small instance, one instance handles ~300–500 users/hour. 100k users over a viral week is feasible on a handful of instances, so infra cost is modest (tens to low hundreds of USD). The real risks are Telegram-side throttling or bans, and security liability, rather than compute bills.

### Gaps
- I found no public incident where a "Wrapped"/stats site holding Telegram sessions was breached. The risk is inferred from the stealer ecosystem.
- No official Telegram statement on third-party services that log in on users' behalf, beyond the ToS and "observation" language.
- No published per-account rate-limit numbers for `messages.search` / `messages.getHistory`. Telegram does not document them.

## What comparable "wrapped"/chat-analytics products do (upload-export vs. login; privacy & virality)

### Takeaway
Across WhatsApp, iMessage and Telegram analyzers, almost every product uses the export file or a local database read and analyses it on-device. The products then lead with "nothing leaves your browser/device" as a headline feature. Login-based server-side readers are rare, mostly because WhatsApp and iMessage offer no third-party API. Viral iMessage Wrapped tools upload only aggregates for share pages.

### Cited Findings
- WhatsApp analyzers built on browser-side export processing:
  - [WhatsAnalyze](https://whatsanalyze.com/): "nothing uploaded".
  - [whatsappstats.com](https://whatsappstats.com/): offers "Wrapped recaps".
  - [WhatsApp Wrapped (wrappedai.net)](https://wrappedai.net/): "analysis is done entirely on your device".
  - [whats-wrapped.com](https://whats-wrapped.com/).
  - [WhatsAppAnalyser](https://github.com/TinoMuzambi/WhatsAppAnalyser): "Privacy-first browser dashboard … without uploading them".
  - [chat-stats](https://github.com/sakethch0819/chat-stats): "Nothing leaves your browser".
  - (snippets)
- PurpleChats (dev.to launch post) says every step "from unzipping .zip exports to generating interactive Spotify Wrapped-style cards" runs in the browser. It includes a "Wrapped Mode" with story cards, streaks and response-time percentiles, and pitches against tools that make users upload to a server — [DEV Community](https://dev.to/rahmanfrr/i-built-a-100-private-whatsapp-chat-analyzer-zero-servers-zero-tracking-1cpl) (snippet)
- WhatsApp chat exports are capped at 40,000 messages, while Telegram's export is full-history — [such.chat guide](https://www.such.chat/blog/how-to-backup-telegram-chats) (snippet)
- iMessage Wrapped tools read `~/Library/Messages/chat.db` locally. This needs Full Disk Access for the terminal. Only aggregated statistics are uploaded (counts, averages, distributions, emojis, dates), and message content never leaves the computer — [gtarpenning/imessage-wrapped](https://github.com/gtarpenning/imessage-wrapped); [jaswsunny/imessage-wrapped](https://github.com/jaswsunny/imessage-wrapped); [jakespurlock.com, Feb 2026](https://jakespurlock.com/2026/02/i-built-my-own-imessage-wrapped-and-so-can-you/) (snippets)
- A commercial "Wrapped 2025" product exists at [wrap2025.com](https://www.wrap2025.com/). I couldn't fetch it, so the mechanism is unverified.
- Telegram-specific analyzers are essentially all `result.json`-based:
  - [Telegramalyzer](https://telegramalyzer.github.io/Telegramalyzer/), [telegram.graphics](https://charludo.github.io/telegram.graphics/) and [telegram-chat-analyser](https://github.com/nualimov/telegram-chat-analyser): browser-side.
  - [tg-analyzer](https://github.com/Dugit0/tg-analyzer) and [chatan](https://github.com/xxanin/chatan): local CLI.
  - [one bot-based upload tool](https://github.com/AFA06/Telegram-Conversation-Behavioral-Analyzer).
- No official "Telegram Wrapped" exists, and search found no prominent login-based Telegram Wrapped competitor — [search results](https://backlinko.com/telegram-users) (absence of evidence only)

### Inferences
- The market norm for privacy messaging is local processing plus explicit "nothing uploaded" copy. Some products add an optional share step that uploads only aggregates, the iMessage Wrapped pattern. That pattern maps cleanly onto this app: compute on-device, then upload only the final `WrappedData` (no message text) to create a shareable link or PNG.
- Phone-OTP login gives this app a real differentiator: lower friction and mobile support, with no export step. But it is unusual in the category, and it is the pattern most associated with Telegram phishing.
- A hybrid is defensible:
  - In-browser MTProto (b) as the default fast path, running on mobile with no server-held session.
  - Export upload (a) as a "maximum privacy / exact" mode for desktop users and the privacy-conscious.
  - The server reduced to static hosting plus an optional aggregate-only share endpoint.

### Gaps
- No published conversion or drop-off data comparing export-upload and login flows for any wrapped product.
- No user counts found for WhatsApp/iMessage Wrapped tools (wrap2025.com and rewindfy's comparison were blocked).
- Discord and Instagram "wrapped"-like tools were not researched due to tool-call budget. Both platforms offer official data-download packages, so they likely follow the export-upload pattern (unverified).

## Comparison matrix (synthesis; inferred from the findings above)

| Dimension | (a) Export + browser | (b) Browser MTProto | (c) Server workers (current) |
|---|---|---|---|
| Time to first result | Slow: Desktop install, possible 24 h hold, export minutes, then parse (seconds to minutes) | Fast: login plus ~same fetch time as today, minus queueing | Fast, but queued under load (`MAX_CONCURRENT_PIPELINES`) |
| Completeness/accuracy | Highest: full history, exact counts; depends on user choosing chat types | Same API as today; can be exact if the deadline/budget is relaxed (cost is the user's time) | Exact up to `TG_PAGE_BUDGET`, estimated beyond |
| Privacy | Best: verifiable "nothing leaves device" | Good: no server session, but the user must trust the page code | Weakest: server holds full-access auth keys |
| Infra cost at 10k/100k | ~static hosting only | ~static hosting (plus optional share API) | Modest compute; per-IP/flood throttling is the real limit |
| Scalability | Unlimited (client compute) | Unlimited; rate limits spread per user/IP | Bounded by per-instance concurrency and Telegram anti-abuse on server IPs |
| Friction/drop-off | High (desktop-only, multistep, big files) | Low to medium (phone + code) | Low to medium (phone + code) |
| Security liability | Minimal | Low (XSS/supply chain could steal the in-page session) | High (breach = mass takeover; 2FA does not help) |
| Mobile support | Poor (no export on mobile; Safari memory ~100–200 MB tab limit) | Good (Web A/K prove it works); watch iOS backgrounding | Best (thin client) |
| Engineering effort | Medium (new TS/WASM parser + port stats) | High (port pipeline to TS/WASM; GramJS archived → teleproto) | Done |
