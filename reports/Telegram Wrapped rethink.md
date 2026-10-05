# Move Telegram Wrapped onto the user's device

Telegram Wrapped cannot get fast by adding machines. **Telegram caps how fast one account can be read, and the cap does not depend on how much hardware reads it.** Extra servers, a separate IP per user and Takeout all leave that cap where it is, and several of them add risk to the user's account. The route to results that are both fast and accurate has three parts. First, get every number that can be counted exactly from cheap `limit=1` count searches, which takes seconds to a minute. Second, keep reading the full text in the background while the user is already swiping through a deck built from those exact numbers. Third, offer the official Telegram Desktop JSON export as an "exact deep mode". For the architecture, the recommendation is **one TypeScript analysis engine that runs in the browser**. It is fed either by an in-browser MTProto client (the default fast path, which works on mobile) or by a streamed `result.json` (desktop, exact, private). The server no longer holds sessions. It keeps only static hosting, a share endpoint that receives aggregates only, and an opt-in LLM proxy. For analysis, the LLR plus English-bigram phrase ranker should be replaced with a deterministic three-track pipeline: whole-message catchphrases, dispersion-weighted log-odds n-grams, and per-chat inside jokes. An optional, consented Claude Haiku 4.5 call would only *select and label* candidates that have already been verified, at under one cent per user. For the deck, lead with exact, people-centric and Telegram-native stats such as calls, voice-note minutes, groups and year-over-year change. The 16-type personality should become about 8–10 archetypes, each with a visible "because". Vibe age stays, but with its drivers shown. Phrases become private-only, and contact names are masked on share cards by default. Three risks must be resolved before committing. **Telegram's API Terms appear to prohibit "deployment" of AI/ML on platform data**, and that wording may cover even on-device models. The browser MTProto ecosystem is thin: GramJS was archived in July 2026. And the core rate numbers have never been measured on this app's real account.

*How to read the evidence:* core.telegram.org, most press sites and several vendor pages could not be fetched during research. Claims tagged **(snippet)** rest only on search-engine snippets. Everything in the product/press discussion of section 4 also comes from search summaries. Claims labelled *inference* are reasoning from the sources, not sourced facts. Telegram Desktop and Telethon source files were read directly from GitHub.

## Per-account flood limits, not hardware, cap reading at a few requests per second

### Every read costs one request per 100 messages, and Telegram publishes no budget

Every history or search call returns at most 100 messages. Telegram's own exporter reads in slices of `kMessagesSliceLimit = 100`, one request in flight per chat ([tdesktop export_api_wrap.cpp](https://raw.githubusercontent.com/telegramdesktop/tdesktop/dev/Telegram/SourceFiles/export/export_api_wrap.cpp)). The example account's ~500k counted messages are the user's own *sent* messages, so reading their text alone takes **at least 5,000 search pages**. Reading both sides of every chat would take far more. Throttling arrives as a 420 `FLOOD_WAIT_X`, which says "Please wait {value} seconds before repeating the action". A `FLOOD_PREMIUM_WAIT_X` variant adds an upsell to Premium ([Telegram error docs](https://core.telegram.org/api/errors) (snippet)). Telegram publishes no per-method numbers. Telethon's maintainer is blunt: "Nobody knows the exact limits for all requests since they depend on a lot of factors" ([Telethon errors.rst](https://raw.githubusercontent.com/LonamiWebs/Telethon/v1/readthedocs/concepts/errors.rst)). The official desktop client simply re-queues a request after exactly `secs*1000+10` ms, whatever the wait length ([tdesktop mtp_instance.cpp](https://raw.githubusercontent.com/telegramdesktop/tdesktop/dev/Telegram/SourceFiles/mtproto/mtp_instance.cpp)). Waiting out X exactly is therefore the officially modelled behaviour. Community reports say that retrying during a wait lengthens it, but that claim is not backed by Telegram.

### Realistic rates put a full read of this account at 15 minutes to 4 hours

The only hard datapoint is a Desktop export that read **10,000 messages in 18 s on one account and 34 s on another**, about 300–550 messages/s or 3–5.5 requests/s ([tdesktop #8533](https://github.com/telegramdesktop/tdesktop/issues/8533)). Telethon's old rule of thumb is far more conservative: `GetHistory` floods at "around 30 seconds per 10 requests" ([Telethon messages.py](https://raw.githubusercontent.com/LonamiWebs/Telethon/v1/telethon/client/messages.py)). Applied to 5,000 pages, the range is wide:

| Pacing assumption | Rate | Time for 5,000 pages (500k own messages) |
|---|---|---|
| Telethon conservative rule | 0.33 req/s | ≈ 4.2 h |
| Telethon default sleep | 1 req/s | ≈ 83 min |
| Observed Desktop export | 3–5.5 req/s | ≈ 15–28 min |
| Current app budget (`TG_PAGE_BUDGET=600` in `TG_FETCH_DEADLINE=75` s) | ≈ 8 req/s implied | Covers only 60k messages ≈ 12% of this account |

The last row explains the disappointing live run (*inference*). Within 75 seconds, the current budget can read about an eighth of a 500k-message account, and only by assuming a rate above anything observed. The "estimated mode", with its weighted windows, is not a tuning mistake. It follows directly from asking for minutes-scale results on an account that needs tens of minutes. **No pacing trick makes a full-text read of a heavy account fit in a minute.** The design has to show exact numbers first and finish the text analysis later.

### Count searches are the cheap path to exact numbers

`messages.search` with `from_id = inputPeerSelf` is a production path in Telegram's own exporter. Desktop uses it for "only my messages" mode, and switches to it automatically when `getHistory` returns `CHANNEL_PRIVATE` ([tdesktop export_api_wrap.cpp](https://raw.githubusercontent.com/telegramdesktop/tdesktop/dev/Telegram/SourceFiles/export/export_api_wrap.cpp)). The response carries an exact `count`. A `limit=1` call therefore returns a chat's exact sent total in one request. The same method also accepts filters for voice notes, round videos and phone calls ([Telethon on PyPI](https://pypi.org/project/Telethon/), schema introspected in research). Exact totals, per-chat rankings, media counts and year-over-year deltas can all come from a few hundred calls instead of thousands. One assumption still needs checking. The repo's `tests/fake_telegram.py` treats search counts as exact in 1:1 private chats, and no source confirms that. `live_check.py --verify N` exists for exactly this check, and it should be run before the counts become the headline.

### Takeout cannot help a fresh phone-code login

Takeout wraps calls in `invokeWithTakeout` after `account.initTakeoutSession` ([Takeout API](https://core.telegram.org/api/takeout) (snippet)). Telethon notes that "some of the calls made through the takeout session will have lower flood limits", without giving numbers ([Telethon account.py](https://raw.githubusercontent.com/LonamiWebs/Telethon/v1/telethon/client/account.py)). The catch matters for this app. On a new device, Telegram tells the user they can download their data only after a delay: "We have notified all your devices about the export request… Please come back on {date}" ([tdesktop lang.strings](https://raw.githubusercontent.com/telegramdesktop/tdesktop/dev/Telegram/Resources/langs/lang.strings)). Third-party guides put that hold at 24 hours unless another device approves it ([mosaicchats](https://www.mosaicchats.com/blog/how-to-export-telegram-chat) (snippet)). Every run of this app is a fresh login, so Takeout will usually be refused, and the attempt can **push a "data export requested" alert to the user's phone**. Even when granted, the desktop exporter still reads sequentially, so Takeout makes waits rarer but does not parallelise anything (*inference*). Opening a second takeout also invalidates the first (`TAKEOUT_INVALID`) ([Telethon errors.csv](https://raw.githubusercontent.com/LonamiWebs/Telethon/v1/telethon_generator/data/errors.csv)). The current `TAKEOUT_MAX_WAIT=0` default is right. The team should consider switching Takeout off by default if live testing shows the alert fires even when the request is denied.

### Parallel machines with different IPs per user would add risk without adding budget

Spinning up N machines for one user fails on three counts. First, a session cannot be shared: **`AUTH_KEY_DUPLICATED` permanently kills an auth key used "under two different IP addresses simultaneously"** ([Telethon errors.csv](https://raw.githubusercontent.com/LonamiWebs/Telethon/v1/telethon_generator/data/errors.csv)). Each machine would therefore need its own login, with its own code, its own "new login" notification and its own fresh, closely watched session. Second, the best available evidence says flood limits are per account and per method. People running several accounts rotate them precisely *because* one account's wait does not transfer to the others ([tgcf #30](https://github.com/aahnik/tgcf/issues/30)). Extra sessions for the same account therefore add no read budget. This is community evidence; Telegram has never stated the scope ([MadelineProto #996](https://github.com/danog/MadelineProto/issues/996)). Third, one account logging in from several datacenter IPs within seconds looks like an account takeover. Telegram also puts every account using an unofficial API client "under observation" and threatens permanent bans for flooding ([Telegram API Terms](https://core.telegram.org/api/terms) (snippet)). The Telethon FAQ adds that anti-spam measures have "gotten more aggressive" since 2023 ([Telethon FAQ](https://raw.githubusercontent.com/LonamiWebs/Telethon/v1/readthedocs/quick-references/faq.rst)).

Separate IPs do have one legitimate use, which is spreading many *different* users' logins. IP-level heuristics show up mainly at sign-in (`PHONE_NUMBER_FLOOD`) and when many accounts share one IP ([esimpy](https://esimpy.com/blog/why-telegram-says-too-many-attempts)). A browser-side architecture gets that spread for free, because each user connects from their own IP. The safe speed lever is the one the repo already uses: **several concurrent requests across different chats inside one session, with AIMD backoff**. This resembles the official client, which opens a second export connection on the same auth key ([tdesktop export_api_wrap.cpp](https://raw.githubusercontent.com/telegramdesktop/tdesktop/dev/Telegram/SourceFiles/export/export_api_wrap.cpp)). Whether that concurrency is penalised per account has never been measured.

## The browser beats the server on trust, cost and scale; the server wins only on convenience

### A server-held session is a full account takeover credential

The current design holds a live MTProto auth key on the server. Such a key is equivalent to a logged-in device. Security research on stolen `tdata` describes impersonation "without needing passwords or bypassing Two-Factor Authentication", with tokens that "remain usable indefinitely until the victim manually terminates all active sessions" ([session-hijacking research](https://github.com/kamronsaparbaev/telegram-session-hijacking-research) (snippet)). Infostealers target exactly this material ([SANS ISC](https://isc.sans.edu/diary/Guest+Diary+Beyond+Cryptojacking+Telegram+tdata+as+a+Credential+Harvesting+Vector+Lessons+from+a+Honeypot+Incident/32888/)). The repo's mitigations (Fernet at rest, `log_out` after the run, TTL cleanup) shrink the exposure window to minutes. They do not change what a breach of Redis plus `SESSION_ENCRYPTION_KEY` would expose: **every in-flight user's account, with full write access**.

The 2026 "Telega" affair shows the reputational climate. A Russian third-party client shipped an extra RSA key that enabled man-in-the-middle attacks, Apple flagged it as malicious, and it was pulled in April 2026 ([Meduza](https://meduza.io/en/news/2026/04/17/report-apple-warns-russian-iphone-users-that-unofficial-telegram-client-telega-contains-malicious-code) (snippet)). Telegram is reportedly testing a warning label for unofficial clients ([abit.ee](https://abit.ee/en/soft/messengers/telegram-unofficial-client-security-warning-telega-mitm-ios-messenger-security-third-party-client-ru-en) (snippet; "not officially announced")). A phone-number-plus-OTP form on a third-party site is also the textbook Telegram phishing pattern. That probably suppresses both conversion and sharing (*inference*: no funnel data exists).

### The category has already chosen local processing

Nearly every WhatsApp, iMessage and Telegram analyser processes an export locally and markets "nothing leaves your browser" as a headline feature. Examples include [WhatsAnalyze](https://whatsanalyze.com/), [PurpleChats](https://dev.to/rahmanfrr/i-built-a-100-private-whatsapp-chat-analyzer-zero-servers-zero-tracking-1cpl) and the browser-side Telegram tools [Telegramalyzer](https://telegramalyzer.github.io/Telegramalyzer/) and [telegram.graphics](https://charludo.github.io/telegram.graphics/). iMessage Wrapped tools read `chat.db` locally and **upload only aggregates** for share pages ([gtarpenning/imessage-wrapped](https://github.com/gtarpenning/imessage-wrapped)). The viral "Messages Wrapped" read metadata only, never message text ([Product Hunt](https://www.producthunt.com/products/messages-wrapped)).

Telegram's export is unusually rich. `result.json` carries per-message timestamps, sender IDs, edits, replies, forwards, media types, sticker emoji, text entities and reactions ([tdesktop export_output_json.cpp](https://raw.githubusercontent.com/telegramdesktop/tdesktop/dev/Telegram/SourceFiles/export/output/export_output_json.cpp)). It also covers full cloud history, unlike WhatsApp's 40,000-message cap ([such.chat](https://www.such.chat/blog/how-to-backup-telegram-chats) (snippet)).

The friction is real, though. Full export is Desktop-only ([androidpolice](https://www.androidpolice.com/telegram-export-chats-groups-channels-images/) (snippet)). It carries the same security hold for new desktop sessions. A heavy account's JSON plausibly runs to hundreds of MB, although nobody has published sizes. Mobile Safari reportedly kills pages at around 100 MB on iPhone ([Lap Cat Software](https://lapcatsoftware.com/articles/2026/1/7.html) (snippet)). Parsing must therefore stream (`File.stream()` into [@streamparser/json](https://github.com/juanjoDiaz/streamparser-json) inside a Worker), and the export path is effectively desktop-first.

### In-browser MTProto is proven but thinly supported

Telegram's own web clients run MTProto in the browser. Web A "uses a custom version of GramJS" over WebSockets and Workers ([Ajaxy/telegram-tt](https://github.com/Ajaxy/telegram-tt) (snippet)), connecting to `wss://*.web.telegram.org/apiws` endpoints ([core.telegram.org transports](https://core.telegram.org/mtproto/transports) (snippet)). The library risk is concrete. **GramJS "is archived and no longer maintained as of July 14, 2026"** and points to the [teleproto](https://github.com/sanyok12345/teleproto) fork ([gram-js/gramjs](https://github.com/gram-js/gramjs)). tdweb is an Emscripten build pinned to emsdk 3.1.1 ([tdlib/td example/web](https://github.com/tdlib/td/tree/master/example/web)).

Shipping the api_id in client JavaScript is normal. Every open-source client does it, and the Terms require each app to use its own api_id, not to keep it secret ([obtaining_api_id](https://core.telegram.org/api/obtaining_api_id) (snippet)). Per-user rate limits should match the server path, because they attach to the account and not to the client's location. This is *inference*: no primary source says so. The browser path does lose the server's ability to keep working after the user leaves. iOS can kill a backgrounded tab's WebSocket, so a long deep read needs checkpointing to IndexedDB and must resume when the tab returns.

| Dimension | (a) Desktop JSON export, parsed in browser | (b) MTProto client in browser | (c) Server workers holding sessions (current) |
|---|---|---|---|
| Time to first result | Slow: Desktop install, possible 24 h hold, export run, then parse | Fast: exact count slides in ~1 min (*inference*; measure) | Fast, but queued under load (`MAX_CONCURRENT_PIPELINES=8`) |
| Accuracy | Highest: every message, both sides, exact; depends on the user ticking the right chat types | Same API as today; exact if the user lets the deep read finish | Exact up to the page budget, estimated beyond |
| Privacy | Best: verifiable "nothing leaves the device" | Good: no server session, but users must trust the page code | Weakest: server sees text and holds full-access keys |
| Infra cost at 100k users | Static hosting | Static hosting + small share/LLM API | Modest compute; ~300–500 users/h per small instance (*inference*) |
| Scalability | Unlimited (user's CPU) | Unlimited; limits and IPs spread per user | Bounded by instances and by Telegram anti-abuse on a few server IPs |
| Friction | High: desktop-only, multistep, large files | Low–medium: phone + code | Low–medium: phone + code |
| Security liability | Minimal | Low: XSS/supply-chain could steal the in-page session | High: breach = mass account takeover; 2FA no help |
| Mobile | Poor | Good, with iOS backgrounding caveats | Best (thin client, runs in background) |
| Long runs on heavy accounts | Fine: one export, local parse | Tab must stay open or resume | Best: runs unattended, notifies via bot |
| Engineering effort | Medium: streaming parser + engine port | High: engine port + teleproto integration | Done |

The steelman for (c) is real. It is built, it works on every phone, and it is the only option that can grind through a 30-minute deep read while the user's phone sleeps and then ping them through the existing bot. Its compute bill is trivial. Its true costs are trust, breach liability and concentration of logins on a few IPs, and those costs grow with success. The recommended architecture therefore builds the browser engine first. It keeps (c) only as a hardened fallback until (b) passes its measurement gates (section 5).

## Statistics should propose phrases and an LLM should only choose

### The current phrase output fails for fixable, mostly mechanical reasons

Reading `backend/app/text_analysis.py` shows a **sort bug**: candidates are ordered `(-len(words), -score)`, so every 5-gram that passes the filters is accepted before any shorter phrase. The 15 slots fill with overlapping fragments of long, often copy-pasted messages. Five more defects compound it:

- **No real background for longer phrases.** The background is English bigrams only, so every 3–5-gram and every non-English phrase scores as maximally "distinctive".
- **Forwarded text counts as the user's own.** Forwards are fed in as the user's words, even though `ActivityRecord.forward` exists.
- **Clause boundaries are lost.** Punctuation is stripped before n-gramming, so phrases run across clause boundaries.
- **Rare phrases are subsampled away.** A random 25k-text subsample removes exactly the mid-frequency, per-chat phrases that inside jokes are made of.
- **Emoji are counted per codepoint.** ZWJ sequences, skin tones and flags are split.

The method is also asking the wrong question. Collocation scores measure whether words *co-occur*, not whether a phrase is *characteristic of a person*. PMI favours rare pairs and t-score favours frequent ones ([LADAL](https://ladal.edu.au/tutorials/collocations/collocations.html); [Evert](https://lexically.net/downloads/corpus_linguistics/Evert2008.pdf)). Single-document extractors such as YAKE and KeyBERT surface topics, and they degrade on "informal… noisy and short" text ([arXiv 1910.07897](https://arxiv.org/pdf/1910.07897)).

The right core is the **weighted log-odds ratio with an informative Dirichlet prior** ("Fightin' Words"). It is a variance-adjusted z-score that shrinks rare noise toward zero ([Monroe, Colaresi & Quinn 2008](https://www.researchgate.net/publication/228277150_Fightin'_Words_Lexical_Feature_Selection_and_Evaluation_for_Identifying_the_Content_of_Political_Conflict); [logodds implementation](https://github.com/juliamendelsohn/logodds)). The same machinery gives three contrasts: you vs. a background, one chat vs. your other chats (inside jokes), and you vs. a friend. Idiolect research supports the premise. Word n-grams identified anonymised Enron authors with success "as high as 100%" ([Wright 2017](https://www.semanticscholar.org/paper/Using-word-n-grams-to-identify-authors-and-a-corpus-Wright/802c27f566f183f0a37c79084f48de77d44cf4cd)).

### A three-track deterministic pipeline, with the LLM as an optional curator

The replacement has three tracks.

- **Track A: whole-message catchphrases.** Short messages repeated verbatim, such as "ну такое", "bro what" or "👀". Each needs at least 5 uses on at least 4 distinct days, and greetings are blocklisted.
- **Track B: in-message n-grams.** Phrases of n = 1–4 that never cross punctuation and never start or end with a connector word (gensim's rule, [phrases.py](https://github.com/piskvorky/gensim/blob/develop/gensim/models/phrases.py)). NPMI or LLR serves only as a coherence *filter*. Ranking uses `z_logodds × min(1, days/10)`.
- **Track C: per-chat inside jokes.** Log-odds of one chat against the user's other chats, requiring at least 3 uses on at least 3 days, at least 60% of the user's total uses in that chat, and excluding the partner's name.

Pre-filtering does more than scoring does. Messages with `fwd_from` or `via_bot_id`, bot commands and code blocks are dropped. URL, mention and blockquote spans are cut out using Telegram's own entity types ([Telethon api.tl](https://github.com/LonamiWebs/Telethon/blob/v1/telethon_generator/data/api.tl)). Elongations and laughter families ("ахахах", "hahaha", "jajaja") are collapsed. Emoji are counted as grapheme clusters ([UAX #29](http://www.unicode.org/reports/tr29/)). All of this is counting. The research estimates 10–30 s and bounded memory for 500k messages using Apriori-style pruning (*inference*, not measured).

Chat-register backgrounds are the open problem. Against a formal corpus, every "lol" looks distinctive. The research found no open per-language chat n-gram corpus. The options are k-anonymous cross-user counts (which require uploading n-gram aggregates and raise their own consent questions), OpenSubtitles-style corpora, or, in the short term, frequency ranking plus a per-language generic-phrase blocklist.

An LLM adds taste, not facts. Zero-shot LLMs beat unsupervised keyphrase extractors but trail supervised ones ([arXiv 2312.15156](https://arxiv.org/pdf/2312.15156)). LLMs also invent phrases unless constrained, which is why KeyLLM offers `check_vocab` and candidate-only modes ([KeyLLM guide](https://github.com/MaartenGr/KeyBERT/blob/master/docs/guides/keyllm.md)). The pattern is **statistics propose, LLM disposes**:

1. Send 60–120 candidates as `{id, phrase, count, days, z, 2–3 redacted examples}`.
2. Ask the model to choose, group and title them.
3. Discard any id it returns that is not in the list.
4. Always display the phrase and count from the app's own table.

Hallucinated phrases become impossible by construction. Consumer precedents (Text Unwrapped on Claude, Claude-written iMessage Wrapped quotes) show demand ([Show HN](https://news.ycombinator.com/item?id=46428595) (snippet); [Jake Spurlock](https://jakespurlock.com/2026/02/i-built-my-own-imessage-wrapped-and-so-can-you/) (snippet)). Nobody has published an evaluation of catchphrase or "funniness" curation, so quality must be judged on real accounts.

### Multilingual chat needs per-chat language votes, not per-message NLP

Short-message language ID is unreliable. Lingua self-reports about **74% accuracy on single words but 99.7% on sentences**, and it runs 3,000 texts in about 12 s in low-accuracy mode ([lingua-py](https://github.com/pemistahl/lingua-py)). The research also found mixed evidence on whether fastText handles short text well ([modelpredict survey](https://modelpredict.com/language-identification-survey)). The robust recipe has five parts:

- Detect language only on messages of at least 20 characters, then take a majority vote per chat and per user.
- Pick stopword and connector lists from [stopwords-iso](https://github.com/stopwords-iso/stopwords-iso).
- Add Latin-script transliterations of common Russian function words.
- Fold `ё→е`.
- Never run heavy spaCy/stanza pipelines on the per-user hot path.

### Topics and mood are aggregate features, best done on-device

LDA is a poor fit for one-line messages. BERTopic-style pipelines (multilingual embeddings → UMAP → HDBSCAN → c-TF-IDF) beat LDA and NMF on coherence for short, low-resource text ([arXiv 2402.03067](https://arxiv.org/pdf/2402.03067); [arXiv 2212.08459](https://arxiv.org/pdf/2212.08459)). The key move is to **sessionise chats on idle gaps first**, so each "document" is a conversation rather than a three-word line. No paper validates a gap threshold, so it must be tuned. **multilingual-e5-small (47M parameters, 384 dimensions)** is the size/quality sweet spot. It averaged 46.0 vs 30.4 for paraphrase-multilingual-MiniLM on Polish MTEB ([PL-MTEB](https://arxiv.org/html/2405.10138v2)). bge-m3 (568M) is the quality ceiling ([aimultiple](https://aimultiple.com/multilingual-embedding-models)).

In-browser WebGPU embedding ran at about **187 docs/s vs 51 on WASM** in one benchmark ([arXiv 2607.25180](https://arxiv.org/pdf/2607.25180) (snippet)). That implies roughly 9 minutes for 100k sessions on a laptop and several times longer on phones (*inference*).

For mood, XLM-T reaches macro-F1 between **56.4 (Hindi) and 77.3 (German)**, and Russian is not among its fine-tuning languages ([XLM-T](https://github.com/cardiffnlp/xlm-t)). Russian has tiny dedicated models such as [rubert-tiny2 CEDR emotion](https://huggingface.co/cointegrated/rubert-tiny2-cedr-emotion-detection). Per-message accuracy is only moderate, so mood must be shown as a smoothed monthly trend.

The cheapest robust signal is the **Emoji Sentiment Ranking**: 751 emojis scored from 1.6M tweets in 13 languages, with no significant cross-language differences ([Kralj Novak et al. 2015](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0144296)). It is a lexicon rather than a trained model. That makes it language-independent, which suits code-switched text, and it is plausibly less exposed to Telegram's AI clause (*inference*). "Your saddest month" should be avoided. It edges toward health inference, which is GDPR Art. 9 territory.

### Personality and vibe age survive only as explained, playful style labels

The science does not support psychological claims. Big Five prediction from social-media footprints correlates only **r = 0.29–0.40** ([Azucar et al. 2018 meta-analysis](https://www.sciencedirect.com/science/article/abs/pii/S0191886917307328)). That falls short of the accuracy needed to assess an individual ([Digital Psychology 2020](https://ejournals.facultas.at/index.php/digitalpsychology/article/download/1823/1584) (snippet)). About **half of people get a different four-letter MBTI type on retest** ([Myers-Briggs Company](https://ap.themyersbriggs.com/themyersbriggs-mbti-facts.aspx)). The current 16-type EVTM×INRD code inherits that instability: it splits continuous z-scores into binary letters, so users near the midpoint flip type.

Text-based age prediction has reached **MAE of 4.1–6.8 years** on blogs and forum posts ([Nguyen, Smith & Rosé 2011](https://aclanthology.org/W11-1515.pdf)). Mixed-language one-liners are likely worse. Both slides are still worth keeping, because Spotify's 2025 "listening age" became the shareable hook of the year ([Fast Company](https://www.fastcompany.com/91454685/spotify-wrapped-2025-eagerly-checking-your-listening-age-everyone-else-is-too)). Its derivation, the release dates of the songs you play, was explainable. The rule is the same here. Describe *style*, never real age or personality. Show the two or three metrics that drove each label. Never apply either label to contacts.

### Cost and placement of each model

Claude Haiku 4.5 costs **$1 per million input tokens and $5 per million output tokens**, with a 50% Batch discount that stacks with caching ([Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)). The table applies those prices to the research's token estimates. Russian-heavy users likely need 1.5–2× more tokens; this has not been measured.

| Task | Recommended technique | Where it runs | Est. tokens (in / out) | Haiku 4.5 cost per user (list) |
|---|---|---|---|---|
| Signature phrases, inside jokes | Tracks A–C (log-odds, dispersion, filters) | Browser engine (deterministic) | — | $0 |
| Phrase curation and titles | Candidate-constrained LLM pick, validated by id | Opt-in server proxy → Haiku 4.5 | ~3–6k / ~0.5k | ≈ $0.006–0.009 |
| Topic clusters | Sessionise → e5-small → HDBSCAN → c-TF-IDF | Browser (WebGPU/WASM) | — | $0 |
| Topic labels | LLM on keywords + redacted lines | Opt-in proxy | ~12–15k / ~1k | ≈ $0.02 |
| Mood trend | Emoji lexicon (+ optional XLM-T / rubert-tiny2 sample) | Browser | — | $0 |
| Archetype, vibe age | Transparent rules on exact metrics | Browser | — | $0 |
| "Minimal" LLM bundle (above + 10 friend blurbs from aggregates) | — | Opt-in proxy | ~35k / ~3.5k | ≈ $0.05 ($0.026 Batch); ≈ $5k per 100k users |
| Send all 500k messages | Not recommended | — | ~7.5M / — | ≥ $7.50 |

Cost is not the constraint here: the LLM layer is cheap. The constraint is permission. Telegram's API Terms reportedly prohibit "using, accessing or aggregating data obtained from the Telegram platform to train, fine-tune or otherwise engage in the development, enhancement or **deployment** of artificial intelligence, machine learning models". The exceptions reportedly require explicit consent from **all relevant users** per chat ([Telegram API Terms](https://core.telegram.org/api/terms) (snippet); [Open Terms Archive memo](https://opentermsarchive.org/en/memos/telegram-prohibits-collecting-data-for-ai-use/) (snippet)). A plain reading could cover on-device classifiers, and even the existing `ml/` module, not just third-party LLMs. Contacts cannot consent. This is *inference* from snippets, and it is the single largest legal risk in the project.

GDPR adds a second layer. Recital 18 applies the Regulation to "controllers or processors which provide the means" for household processing ([GDPR Recital 18](https://gdpr-info.eu/recitals/no-18/) (snippet)). Contacts' messages are third-party data that the user cannot consent for ([Internet Policy Review](https://policyreview.info/articles/analysis/privacy-self-management-and-issue-privacy-externalities-thwarted-expectations-and)). Anthropic's commercial API reportedly does not train on customer content and deletes inputs within 30 days by default, with zero data retention by agreement ([getvoibe](https://www.getvoibe.com/resources/claude-api-data-retention/) (secondary)). Some newer "Covered Models" reportedly carry mandatory 30-day retention that overrides ZDR ([digitalapplied](https://www.digitalapplied.com/blog/fable-5-30-day-data-retention-zdr-enterprise-2026) (secondary)). That is another reason to use Haiku-class models.

The defensible order is:

1. Deterministic counting.
2. Lexicons.
3. On-device models, after legal sign-off.
4. A separate, explicit opt-in that sends only the user's *own* redacted candidate phrases and aggregates.

## Exact numbers, people and calls make recaps shareable; text mining does not

### What the hits and flops of other recaps teach

Wrapped works when usage data becomes an identity statement backed by a number the user believes. Spotify's 2025 edition drew **200M engaged users and 500M shares in its first 24 hours**, its "biggest launch ever" ([Rolling Stone](https://www.rollingstone.com/music/music-news/spotify-wrapped-2025-success-1235477520/); [TechCrunch](https://techcrunch.com/2025/12/04/spotify-says-wrapped-2025-is-its-biggest-yet-with-200m-users-in-its-first-day)). It followed a 2024 edition panned for an "unnecessary" AI podcast and nonsense micro-genres such as "Pink Pilates Princess Strut Pop" ([Several](https://several.com/news/spotify-wrapped-2024-backlash)). 2024 also drew accuracy complaints that ran to 20+ pages of community threads ([Spotify Community](https://community.spotify.com/t5/Your-Library/My-Wrapped-content-is-inaccurate/td-p/7242372)).

Researchers describe the "limits of the Wrapped self", the moment the data-self doesn't match the felt self ([Annabell & Rasmussen 2025](https://journals.sagepub.com/doi/10.1177/14614448251391301)). The lesson for this app is direct. **An estimated headline number is a liability, and a generic LLM paragraph is a known negative signal.** Labels need a visible "because", as Spotify's 2023 characters had ([Time](https://time.com/6340656/spotify-wrapped-guide-2023/)).

Messaging recaps that spread were built on relationship dynamics from metadata. Messages Wrapped offered who texts most, fastest and slowest responders, and percentage of conversations started, and reportedly passed 15,000 users within days ([X launch post](https://x.com/sabziz/status/1867308611925684560); [Product Hunt](https://www.producthunt.com/products/messages-wrapped)). Collectible or comparative endings give people a reason to post. Discord's Checkpoint ends on one of 10 cards plus a wearable avatar decoration ([How-To Geek](https://www.howtogeek.com/discord-checkpoint-is-the-end-of-year-recap-you-never-knew-you-needed/)), and Duolingo shows a global percentile ([Digital Trends](https://www.digitaltrends.com/phones/duolingo-year-in-review-2024-how-to-find-yours/)). There is a known failure mode. Facebook's 2014 Year in Review showed Eric Meyer his recently deceased daughter. In 2015 the company added filters for deceased relatives and exes, plus editing ([Phys.org/AP](https://phys.org/news/2015-01-facebook-year-feature-painful.html); [TechCrunch](https://techcrunch.com/2015/12/16/no-more-tears-in-review)).

Today, `SummarySlide.tsx` (lines 83–88) puts `topChat.name` and the avatar on the default share image. **That should be masked by default now.**

### Telegram's schema supports exact, native slides the app doesn't use yet

Introspecting Telethon 1.45.0's TL layer confirms the following ([Telethon on PyPI](https://pypi.org/project/Telethon/)):

- **Calls:** `MessageActionPhoneCall(call_id, video, reason, duration)` with an `InputMessagesFilterPhoneCalls` search filter. That supports call minutes, longest call, video vs. voice, and missed calls.
- **Voice and round-video notes:** `DocumentAttributeAudio(duration, voice)` with `InputMessagesFilterVoice`/`RoundVideo` filters.
- **Sticker packs:** sticker set identity on `DocumentAttributeSticker`.
- **Reactions:** `ReactionCount.chosen_order` marks reactions the user gave.
- **Forwards:** the source channel on `MessageFwdHeader`.
- **Year-over-year and "new people":** one extra `limit=1` count per top chat with last year's dates.
- **Smaller extras:** Saved Messages, dice, polls, stories and gifts.

**"Left on read" cannot be computed honestly.** Telegram exposes only the *current* read pointers per dialog, not per-message read times (*inference* from the schema). Whether a global call-log search works, and what it costs, is unverified.

| # | Slide (current → proposed) | Verdict | Data basis | Why |
|---|---|---|---|---|
| 1 | Total sent | **Keep** as hero; add YoY delta | Exact | The "minutes" equivalent; must be exact |
| 2 | Year in rhythm | **Keep**; absorb streak + active days | Weighted / exact windows | One story, not three thin slides |
| 3 | Peak hour | **Rework** into a "night owl / 3 a.m. club" chip inside rhythm or archetype | Weighted | Readable persona, thin as a standalone slide |
| 4 | Reply speed | **Rework** to "fastest replier" (named, masked on share) + your median | Sampled windows | Mirrors viral "fastest responder"; global average is dull |
| 5 | Texter personality (16 types) | **Rework** to ~8–10 archetypes with a 1-line "because"; collectible end card | Rules on exact metrics | Personas drive shares; opaque codes invite "Sound Town" scepticism |
| 6 | Vibe age | **Keep, explain** 2–3 driving signals; style, not real age | Text-derived | Direct analogue of 2025's "listening age" hit |
| 7 | Top conversations | **Keep** (core); mask on share; skip chats silent in the last ~3 months as "top" | Exact | Most compelling messaging stat; ex/deceased risk |
| 8 | Conversation starter % | **Keep**, per-friend framing, "estimated" badge | Sampled windows | "Who texts first" is the viral messaging stat |
| 9 | Streak | **Merge** into rhythm | Exact windows | Too thin alone |
| 10 | Most-reacted message | **Keep**; blur text on export | Exact per fetched message | Telegram-unique and funny; leaks text if shared |
| 11 | Media mix | **Rework** → "How you talk", with voice-note minutes as the hero | Exact (filters) | Minutes are memorable; percentages are not |
| 12 | Emoji | **Merge** with reactions ("your go-to reaction", custom emoji) | Exact / weighted | Overlaps stickers alone |
| 13 | Top stickers | **Keep, upgrade** to top *pack* + top sticker | Exact | Visual, native, share-safe |
| 14 | Vocabulary / phrases | **Rebuild** (Tracks A–C); private-only, never on share cards; hide when output is generic | Text-derived | Highest privacy and quality risk, lowest virality |
| 15 | Summary card | **Keep, fix privacy**: masked names, archetype + vibe age + 3 exact numbers | — | Currently leaks a contact name |
| N1 | **Calls** (minutes, longest, video vs voice, call buddy) | **New** | Exact | Untapped, emotional, Discord-style voice-time analogue; needs live check |
| N2 | **Group life** ("you wrote 31% of X") | **New** | Exact | Social but not about one person |
| N3 | **Year-over-year / new people** | **New** | Exact | A data-grounded "evolution" story; avoid a "faded friends" card |
| N4 | **Your feed** (channels you forward from) | **New, optional** | Exact | Public entities, safe to share |
| N5 | **Saved Messages** ("you texted yourself 412 times") | **New, optional** | Exact | Relatable; currently excluded from selection |
| N6 | **Extras** (dice, polls, stories, gifts, friends who joined) | **Optional, auto-hide** | Exact | Telegram flavour when notable |
| N7 | **Percentile** vs other users | **Later** | Exact + k-anonymous aggregates | Duolingo/Spotify comparison hook |
| — | Left on read, "who you ignore", faded friends, sentiment scores, LLM narrative paragraphs | **Drop / never build** | — | Not computable, hurtful, or a known backlash pattern |

The core deck should hold about 10–12 slides, with optional slides shown only when their numbers are notable. That target is the research's estimate; no primary source sets an optimal count. Every card should export at 1080×1920, carry a one-line derivation caption, show an "estimated" badge when the number is weighted, and default to share-safe content.

## A client-side engine with progressive accuracy is the recommended build

### The end-to-end design

The recommended system has one analysis engine (TypeScript, with WASM where it helps) that consumes a stream of normalised message records, `{chat, date, out, text, entities, media, reactions, fwd}`. Two feeders drive it.

The **default fast path** is an in-browser MTProto client (teleproto). After login it runs five stages:

1. **Census.** Dialogs, one `limit=1` count search per dialog, filter counts for voice, round video and calls, and last year's counts for top chats. This is roughly 300–700 calls. At the observed 3–5 requests/s that is about one to four minutes (*inference*; measure). It immediately unlocks the exact slides: total, top chats, groups, YoY, voice and calls. The deck becomes playable at this point.
2. **Deep read.** Stream own-message pages, top chats first, under AIMD concurrency. Checkpoint to IndexedDB so a killed tab resumes.
3. **Both-sides windows.** Fetch both sides for the top 8 private chats, which gives reply speed, starters and "you vs. them" phrases.
4. **Local analysis.** Run the engine in a Worker. Slides upgrade from "estimated" to "exact" badges as coverage rises.
5. **Log out.** Call `auth.logOut`.

For the 500k-message account, the deep read is the 15–28-minute (best case) or roughly 80-minute (1 req/s) part. That is precisely why the deck must not wait for it.

The **exact deep mode** streams a Desktop `result.json` into the same engine. It is the recommended path for privacy-minded and desktop users, and the only path that yields both sides of every chat.

The **server** shrinks to four jobs: static hosting, a share endpoint that receives only the final aggregate `WrappedData` with masked names, k-anonymous aggregates for the percentile slide, and an opt-in LLM proxy that receives only redacted candidates. It never holds a Telegram session or message text.

### Phased plan

| Phase | Scope | Exit gate |
|---|---|---|
| 0. Measure + quick wins (current stack) | Run the measurements below. Fix the phrase sort bug, drop forwards/bots/code, segment at punctuation, add a distinct-days requirement, collapse laughter, count emoji as graphemes, drop the English-bigram distinctiveness term, stop subsampling. Mask names on the summary card. Prototype calls/YoY/voice-minute counts in Python. | Rate and exactness numbers recorded on ≥2–3 real accounts; phrase precision@10 judged better by the account owners |
| 1. Shared engine + export mode | Port stats and Tracks A–C to TS. Streaming `result.json` parser in a Worker. New exact slides. Archetype rework, vibe age with drivers. | 500k-message export parses on desktop Chrome within agreed time and memory; outputs match the Python pipeline on the same data |
| 2. Browser MTProto fast path | teleproto in a Worker, census → progressive deck → resumable deep read, `auth.logOut`, CSP and an open-source build | iOS/Android completion rate acceptable; FLOOD_WAIT profile no worse than server; bundle size acceptable |
| 3. Retire server-held sessions | Server becomes static + share + aggregates. Keep (c) only behind a flag if Phase 2 fails its gates, and then never persist text | Security review sign-off; no session material in any server store |
| 4. Optional intelligence | On-device topics/mood, LLM curation opt-in, percentile slide | Written legal opinion on Telegram's AI clause and GDPR basis; DPA/no-training terms with the LLM vendor |

### What must be measured before committing

| Measurement | How | Decision it gates |
|---|---|---|
| Is `messages.search(from_id=self).count` exact in 1:1 chats and groups? | `python -m scripts.live_check --verify 3` (and higher N) on 2–3 accounts | Whether exact headline numbers can rest on count searches |
| Sustained req/s before the first FLOOD_WAIT, X values, effect of concurrency across chats, for `search` vs `getHistory` | Extend `live_check.py` to log per-call timing and waits | Deep-read time estimates; AIMD defaults; whether "exact for everyone" is realistic |
| Wall time to read every own message on the 500k account | `live_check.py` with an unlimited `TG_PAGE_BUDGET`/deadline | Whether the deep read is minutes or hours; how the UX for long runs should look |
| Takeout: granted-immediately rate on fresh logins; does a denied request still alert the user's devices? | Live test on several accounts | Whether to turn Takeout off by default |
| Global call-log search (`InputMessagesFilterPhoneCalls`, empty peer) cost and completeness; Saved Messages counts | Live test | Calls and Saved Messages slides |
| `result.json` size and export duration for a heavy account; streaming-parse throughput and peak memory in desktop Chrome and iOS Safari | Export the test account; browser benchmark | Viability of export mode and whether it is desktop-only |
| teleproto bundle size, layer currency, iOS backgrounding behaviour, resume reliability | Prototype | Go/no-go for the browser fast path |
| e5-small and sentiment throughput on mid-range phones; Russian vs English token ratio for Haiku | Benchmarks | On-device topic/mood feasibility; LLM cost for RU users |
| Phrase quality, old vs new, in RU/EN mixed accounts | Blind owner ratings of top-10 lists | Whether phrases ship at all, and whether LLM curation adds value |
| Funnel drop-off at phone login vs export upload | Analytics after launch | Which path to make primary per platform |
| Full, current Telegram API Terms text (AI clause, third-party login) | Direct read + counsel | Whether any ML/LLM features ship |

### Open risks

There are four. The **AI clause** could forbid not only the LLM step but any model over API-obtained chats. If counsel reads it that way, the product must be built from deterministic counting and lexicons only, which the recommended design allows. **Browser MTProto rests on one fork of an archived library.** A possible "unofficial client" warning label could also make the login look hostile at exactly the wrong moment. **Rate limits remain folklore** until measured, and every timing in this report inherits that uncertainty. Finally, **people-centric slides carry emotional risk** that no filter fully removes, because the app cannot know who has died or who is an ex. Hiding a person and masking names by default are the only robust mitigations.

## Conclusion

The rethink turns the question around. Accuracy has been treated as a single global property that forced a trade against speed. It is better treated per slide. The stats that make messaging recaps spread (totals, top people, groups, calls, voice minutes, year-over-year change) turn out to be the *cheapest* to compute exactly, through count searches and filters. The stats that are slow, approximate and legally exposed are the text-mining ones, and they are also the least viral. Build the deck so that the exact stats arrive first and the text-derived ones arrive later, labelled honestly. Then "fast" and "accurate" stop competing. The FLOOD_WAIT ceiling, which looked like the problem, becomes a background detail.

The larger strategic shift is that Telegram Wrapped's bottleneck was never compute. It was trust: a stranger's site asking for a phone code, holding a key that bypasses 2FA, and reading friends' messages. Moving the session and the text onto the user's device, and sending only aggregates and explicitly consented, redacted candidates anywhere else, removes the biggest liability. It also turns "nothing leaves your device" from a footnote into the product's best marketing line. The deciding work now is empirical: an afternoon of `live_check.py` runs and one legal read of Telegram's AI clause will settle more than any further desk research.
