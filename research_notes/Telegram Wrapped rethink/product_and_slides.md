# Product & slide design for Telegram Wrapped: what makes "Wrapped" recaps engaging/shareable, and which slides Telegram data can honestly support

> Method note for the report writer: web *search* worked but almost every full-page *fetch* was blocked by the sandbox egress proxy (forbes.com, techcrunch.com, wikipedia.org, core.telegram.org, producthunt.com, irrationallabs.com, LSE repository, Duolingo blog, Strava support, Spotify substack all returned EGRESS_BLOCKED). Findings below therefore come from search-result summaries of the cited pages (treat exact wording as paraphrase) plus primary verification of the Telegram API schema by installing Telethon 1.45.0 from PyPI and introspecting its generated TL types/functions. Where a number comes only from a marketing aggregator, it is flagged as low-confidence.

## 1. Spotify Wrapped design lessons: story format, identity, shareable cards, personas, and what was criticised

### Takeaway
Wrapped works because it turns usage data into an identity statement in a story format, with each card ready to post. It fails when labels feel generic, AI-made or invented, or when headline numbers don't match what users remember. 2024 (AI podcast, "Music Evolution" nonsense genres, dropped favourite features) was panned. 2025 recovered with a playful but *explainable* metric ("listening age", derived from release dates) plus social/comparative features, and set records.

### Cited Findings
**Scale / virality numbers (Spotify-reported via press)**
- Wrapped 2025: 200M engaged users and 500M shares in the first 24 hours after the Dec 3 launch. Spotify called it its "biggest launch ever", +19% vs 2024 — [Rolling Stone](https://www.rollingstone.com/music/music-news/spotify-wrapped-2025-success-1235477520/); [TechCrunch](https://techcrunch.com/2025/12/04/spotify-says-wrapped-2025-is-its-biggest-yet-with-200m-users-in-its-first-day); [IBTimes UK](https://www.ibtimes.co.uk/record-breaking-spotify-wrapped-2025-sees-200m-engage-500m-shares-day-1760640)
- In 2024 Wrapped took 62 hours to reach 200M engaged users. 2025's first-day shares were reported as "41% more than last year" — [RouteNote](https://routenote.com/blog/spotify-wrapped-2025-record-breaking-launch/); [NewsBytes](https://www.newsbytesapp.com/news/science/over-200m-people-viewed-spotify-wrapped-2025-within-a-day/story)
- Older figures appear only in marketing aggregators, not primary sources (LOW confidence): 2021 had 120M users and 60M shares; 2023 had 1.5B social impressions and 156M users; 2024 had 2.1M social mentions in 48h and 400M TikTok views in 3 days; 2020 Wrapped was linked to a 21% rise in app downloads — [Webtonic](https://www.webtonic.io/blog/spotify-wrapped-marketing-strategy-7-lessons-from-a-viral-campaign); [MarketingWithDave](https://marketingwithdave.com/case-study-how-spotify-wrapped-became-a-viral-phenomenon-and-when-it-backfired/)

**Personas and identity labels: the most-discussed features, and the riskiest**
- 2023 "Me in 2023" put each user in one of 12 listening "characters" (e.g. Luminary = plays light, upbeat music more than others; Alchemist = makes more playlists; Shapeshifter = moves quickly between artists). Each label came with a *because* explanation. "Sound Town" matched users to a city with a similar taste profile — [Time](https://time.com/6340656/spotify-wrapped-guide-2023/); [Johns Hopkins News-Letter](https://www.jhunewsletter.com/article/2024/01/spotify-wrapped-2023-excites-the-music-streaming-community-with-new-features)
- Sound Town got the most social-media interest, but also scepticism. Small Burlington, VT came up surprisingly often, and people doubted results because so many different artists mapped to one place. Users went to X/TikTok to decode what the towns "meant", which drove memes — [Johns Hopkins News-Letter](https://www.jhunewsletter.com/article/2024/01/spotify-wrapped-2023-excites-the-music-streaming-community-with-new-features); [Time: Sound Towns explained](https://time.com/6340986/spotify-wrapped-sound-towns-explained/)
- 2025 added "Listening Age", based on the release dates of the songs you play most. It also added "Clubs" (6 groups such as Soft Hearts, Serotonin, Cosmic Stereo, Full Charge, Grit Collective, Cloud State Society), a fan leaderboard ranking you among your top artist's listeners worldwide, and a "Wrapped Party" for comparing with friends — [Music Ally](https://musically.com/2025/12/05/clubs-fan-leaderboards-listening-age-wrapped-2025-reveals-a-new-set-of-features/); [CHCH](https://www.chch.com/chch-news/spotify-wrapped-2025-drops-with-new-listening-age-and-music-trend-clubs/); [TechBuzz](https://www.techbuzz.ai/articles/spotify-wrapped-2025-adds-friend-battles-and-listening-age)
- Fast Company reported that "everyone" was checking their listening age, i.e. it became the shareable hook of 2025 — [Fast Company](https://www.fastcompany.com/91454685/spotify-wrapped-2025-eagerly-checking-your-listening-age-everyone-else-is-too)
- 2025 cut back to a single AI-powered feature (a "listening archive" of your most memorable streaming days) — [CHCH](https://www.chch.com/chch-news/spotify-wrapped-2025-drops-with-new-listening-age-and-music-trend-clubs/)

**2024 backlash: what went wrong**
- The AI podcast (built with Google NotebookLM) was called unnecessary and inaccurate. Users described the AI commentary as robotic and generic, and "AI overkill" trended — [Several](https://several.com/news/spotify-wrapped-2024-backlash); [The Modems](https://themodems.com/tech/spotify-wrapped-2024-slammed-as-boring-and-ai-overkill/); [Forbes (via search summary)](https://www.forbes.com/sites/danidiplacido/2024/12/05/spotify-wrapped-2024-backlash-controversy-and-memes/)
- "Music Evolution" described taste with nonsense micro-genre names such as "Pink Pilates Princess Strut Pop" and "Surf Crush Beach Reggae". Users also missed dropped features (audio aura, Sound Town, top genres) — [Several](https://several.com/news/spotify-wrapped-2024-backlash); [MediaShower](https://blog-origin.mediashower.com/blog/spotify-wrapped-2024/)
- Some users blamed the drop in creativity on Spotify's layoffs and a heavier reliance on AI (this is user speculation, not confirmed) — [Several](https://several.com/news/spotify-wrapped-2024-backlash)
- Accuracy complaints in 2024: minute counts much lower than expected, months missing, and top artists that didn't match habits. Spotify itself pointed to shared accounts, smart speakers and background playback as distorting factors. Community threads titled "My Wrapped content is inaccurate" ran to 20+ pages — [Spotify Community](https://community.spotify.com/t5/Your-Library/My-Wrapped-content-is-inaccurate/td-p/7242372); [ResetEra](https://www.resetera.com/threads/is-anyone-else%E2%80%99s-spotify-wrapped-2024-inaccurate.1051656/); [Alibaba product-insights (low quality, aggregator)](https://www.alibaba.com/product-insights/spotify-wrapped-sucked-in-2024-reasons-for-disappointment.html)
- Forbes reported pressure on Spotify going into 2025 "after the panned 2024 edition" — [Forbes](https://www.forbes.com/sites/conormurray/2025/12/01/spotify-wrapped-could-drop-this-week-as-fan-pressure-mounts-after-panned-2024-edition/)

**Academic framing**
- Annabell & Rasmussen (2025, *New Media & Society*) call Wrapped an "algorithmic event". Their analysis of user responses finds four themes: the *resonance* of Wrapped, the *limits of the Wrapped self* (where the data-self doesn't match the felt self), the ambience of music, and contestation of Spotify's governance. Reactions range from celebrating personalisation to criticising data capture — [Annabell & Rasmussen 2025 (SAGE)](https://journals.sagepub.com/doi/10.1177/14614448251391301); [LSE open-access PDF](https://researchonline.lse.ac.uk/id/eprint/129812/1/annabell-rasmussen-2025-an-algorithmic-event-the-celebration-and-critique-of-spotify-wrapped.pdf)
- Related work describes "wrappification" (repackaging behavioural data about one activity as a yearly identity artefact) and "algorithmic self-making and performances of taste" — [Information, Communication & Society 2026](https://doi.org/10.1080/1369118X.2026.2647352); [Utrecht/Cardiff workshop study](https://research-portal.uu.nl/ws/files/281397677/Spotify_Un_wrapped_how_ordinary_users_critically_reflect_on_Spotify_s_datafication_of_the_self_within_creative_workshops.pdf)

### Inferences
- The pattern that works: **one exact, big, personal number** (minutes / messages), **ranked lists of the things you love** (artists / people / stickers), and **one or two playful identity labels that come with a visible reason** ("because you…"). Labels with no derivation (Music Evolution micro-genres), or with a derivation users can't check (Sound Town), produce mockery. Sometimes the mockery is good engagement (Sound Town memes), but it also erodes trust.
- "Listening age" is a direct analogue of the current "vibe age" slide. Its success suggests vibe age is worth keeping, **if the derivation is explainable on the slide** (e.g. "your slang, emoji and punctuation look like a typical 22-year-old's: lots of 💀, few full stops"). A derivation the user can't check has the Sound Town problem.
- Generic AI text is now a known negative signal. Any LLM-generated narrative in Telegram Wrapped should be optional, short, and grounded in the user's numbers.
- Accuracy matters most for the headline number: users notice when "minutes" or "messages" feel wrong. The `accuracy` block the app already has (mode, coverage) is an asset. Exact counts should headline, and estimated stats should be labelled.

### Gaps
- Could not read Spotify Newsroom primary posts, or the full text of Forbes/TechCrunch (blocked). Share-rate per card type (which Wrapped card is shared most) is not public in any source I found.
- Pre-2023 share numbers (2020–2023) come only from aggregators. I found no primary Spotify figure.

## 2. Other recaps (Apple Music Replay, YouTube Music, Duolingo, Strava, GitHub, Reddit, Discord, messaging-wrapped tools): what landed

### Takeaway
Successful imitators copy the same three ingredients: an exact headline total, a ranked "favourites" list, and an assigned persona/card, often with a percentile ("top X%") or a collectible reward. Messaging-specific Wrapped tools (Messages Wrapped for iMessage, WhatsApp-wrapped repos) show that **people-centric stats** (who texts first, who leaves you on read, fastest/slowest responders, most active group chats) are the main draw, and that "runs locally / reads no message text" is a selling point.

### Cited Findings
- **Discord Checkpoint (first edition, Dec 2025):** messages sent, voice-chat time, most-used emoji, top server, the DM friend you talked with most, and top 5 games compared against a global leaderboard. At the end each user is matched to **one of 10 Checkpoint cards**, each with a matching **avatar decoration** you can wear until 15 Jan 2026 — [How-To Geek](https://www.howtogeek.com/discord-checkpoint-is-the-end-of-year-recap-you-never-knew-you-needed/); [Player.one](https://www.player.one/discord-wrapped-2025-how-get-your-first-ever-checkpoint-recap-161777); [LADbible](https://www.ladbible.com/news/technology/discord-checkpoint-spotify-wrapped-how-to-052445-20251205)
- PC Gamer's headline framed Checkpoint as "yet more needless features": there is fatigue with Wrapped copycats — [PC Gamer](https://www.pcgamer.com/software/adding-yet-more-needless-features-discord-joins-the-wrapped-crew-with-a-yearly-stat-recap-called-checkpoint/)
- **Messages Wrapped (iMessage, Dec 2024):** launched with "Apple would never make an iMessage Wrapped. So I did it myself". It reportedly had 15,000+ users within days. Stats: who texts you most, **who leaves you on read**, **who you ignore most**, most active group chats, **fastest/slowest responders**, **% of conversations you start**. It is a local Mac app that reads metadata (timestamps, sender) plus emoji, **not message text** — [X launch post](https://x.com/sabziz/status/1867308611925684560); [Product Hunt](https://www.producthunt.com/products/messages-wrapped)
- An informal developer brainstorm for an iMessage Wrapped listed total sent/received, average text length, day-of-week/time-of-day patterns, and "who initiates" as the obvious fun stats — [X: Ethan Wei](https://x.com/ethanweii/status/1871326532809216248). A Dec 2025 post praised an "iMessage wrapped, using local AI on your macbook" — [X: Jackson Dahl](https://x.com/jacksondahl/status/1997127417627136323)
- Open-source **whatsapp-wrapped** offers message stats, emoji analysis and calendar heatmaps, and markets itself as "privacy-first: runs on your device or Google Colab" — [GitHub Duelion/whatsapp-wrapped](https://github.com/Duelion/whatsapp-wrapped). A Telegram/WhatsApp Python analyser also exists — [GitHub AndreaRiboni/Telegram-Whatsapp-Wrapped](https://github.com/AndreaRiboni/Telegram-Whatsapp-Wrapped). Typical analyser features are activity timelines, activity maps, word clouds, most common words, emoji, and sentiment — [GitHub amitkedia007/Whatsapp-chat-analyzer](https://github.com/amitkedia007/Whatsapp-chat-analyzer)
- **Duolingo Year in Review:** lessons, XP, **global percentile ranking**, minutes learned, peak learning period, and a personal "learner style" (persona) since 2020. It is shared most by people with long streaks — [Digital Trends](https://www.digitaltrends.com/phones/duolingo-year-in-review-2024-how-to-find-yours/); [Lingoly](https://lingoly.io/duolingo-year-in-review-2024/); [Ditto](https://dittoditto.io/insights/end-of-year-campaigns-inspiration)
- **Strava Year in Sport:** a personalised recap with "unique data insights, meaningful social engagements and stand-out moments", sharing straight to Instagram/TikTok/messaging, and customisable summary images — [Strava Support](https://support.strava.com/en-us/articles/15401959-your-year-in-sport). Strava put the full recap behind its subscription, which drew negative press ("behind an $80 paywall") — [Harvard TagTeam mirror of Ars Technica](https://tagteam.harvard.edu/hub_feeds/3415/feed_items/17132945/content)
- **Apple Music Replay:** top songs/artists/albums/genres with play counts, a shareable recap, and a year-end highlight reel — [How-To Geek](https://www.howtogeek.com/services-for-an-epic-wrapped-collection/)
- **GitHub Unwrapped** (by Remotion) renders a personalised year-in-review **video** — [GitHub remotion-dev/github-unwrapped](https://github.com/remotion-dev/github-unwrapped)
- **Reddit Recap** shows which parts of Reddit you visited most — [Digital Trends](https://www.digitaltrends.com/phones/duolingo-year-in-review-2024-how-to-find-yours/)

### Inferences
- A **collectible or comparative ending** (Discord's 10 cards + avatar decoration, Duolingo percentile, Spotify fan leaderboard) gives people a reason to post. Telegram Wrapped's equivalent: an archetype card at the end, plus a percentile against other app users ("you sent more messages than 87% of Telegram Wrapped users"). The percentile needs aggregate stats from past runs, which the app does not store yet.
- Messaging Wrapped tools converge on **relationship dynamics** rather than text mining. Word clouds and phrase lists are standard in analyser repos, but none of the viral messaging recaps I found led with them.
- "Doesn't read your message text" is a selling point (Messages Wrapped). Telegram Wrapped runs server-side with a phone login, so trust is a bigger barrier. Slides that need full-text analysis raise the privacy cost and should earn their place.
- Paywalls and recap fatigue are real: the recap must feel worth the login effort.

### Gaps
- No public data on share rates per stat type for any imitator. No primary source on the Messages Wrapped user count beyond the launch thread and press-like summaries.
- Could not verify YouTube Music Recap, Snapchat or Instagram recap contents (no useful search results within budget).

## 3. People-centric stats in messaging recaps: appeal vs. privacy/sensitivity

### Takeaway
Relationship stats (who texts first, fastest responder, top friend, who leaves you on read) are the most compelling part of messaging recaps. They are also the riskiest: they name third parties, can resurface exes or people who have died (Facebook's 2014 Year in Review incident), and some ("left on read") can't be computed accurately from Telegram's history. Show names privately in the deck. Share cards should default to hiding or initialling contact names, and the app should never auto-surface "faded" relationships on a shareable card.

### Cited Findings
- Messages Wrapped's feature list centres on people: most texts, left you on read, who you ignore, fastest/slowest responders, % of conversations started — [Product Hunt](https://www.producthunt.com/products/messages-wrapped); [X launch post](https://x.com/sabziz/status/1867308611925684560)
- Discord Checkpoint names the friend you DM'd most — [LADbible](https://www.ladbible.com/news/technology/discord-checkpoint-spotify-wrapped-how-to-052445-20251205)
- **Facebook Year in Review (Dec 2014):** Eric Meyer was shown a photo of his daughter, who had died that year. He wrote that people who lived through deaths, hospital stays, divorce or job loss "might not want another look at this past year". The post went viral and Facebook apologised — [Phys.org/AP](https://phys.org/news/2015-01-facebook-year-feature-painful.html); [CBS News](https://www.cbsnews.com/amp/news/facebook-apologizes-for-year-in-review-that-highlighted-family-tragedy); [IBTimes](https://www.ibtimes.co.uk/facebook-apologises-year-review-feature-it-brings-painful-memories-user-1481194)
- Facebook's 2015 fix: it "applied a unique set of filters" so that deceased family members and ex-partners would not appear, and added editing to the recap — [TechCrunch 2015](https://techcrunch.com/2015/12/16/no-more-tears-in-review); [Jacobsen 2021, "Sculpting digital voids"](https://doi.org/10.1177/1354856520907390)
- Wrapped has also been critiqued as "the intersection of leisure and surveillance" — [Phoenix New Times](https://www.phoenixnewtimes.com/music/spotify-wrapped-the-intersection-of-leisure-and-surveillance-40633304/)
- **This repo's current share card** (`frontend/src/components/slides/SummarySlide.tsx`, lines 83–88) renders `topChat.name` and the avatar on the summary card that `navigator.share` exports. A contact's real name is on the default shareable image (verified in the codebase).

### Inferences
- **Recommended sensitivity tiers** (my synthesis):
  - *Safe to share:* aggregates about the user only (totals, hours, streaks, sticker packs, emoji, call minutes, vibe age, archetype).
  - *Show in deck, mask on share by default:* named top friends, fastest responder, conversation-starter per friend, most active group (offer a toggle to show first name, initials, or avatar only).
  - *Private only, opt-in or drop:* "left on read", "who you ignore", ghosting, "faded friends", a "lost streak" with a specific person. All of these can surface exes, fallings-out or deceased contacts. Telegram's equivalent of Facebook's filter is impossible (the app can't know who died). Use soft heuristics instead: don't feature a chat as "top" in the recap if it has had no messages for the last ~3 months of the year, or label it neutrally ("your year started with…"), and let users hide a person.
- **Accuracy limits on Telegram:** "left on read" can't be reconstructed historically. Telegram exposes only the *current* read pointers per dialog (`read_inbox_max_id` / `read_outbox_max_id` on the dialog), not per-message read times. A slide claiming "X left you on read 40 times" would be invented. Double-texting (consecutive outgoing messages with no reply within N hours) *is* computable from fetched windows, but only in exact-fetch mode or within sampled windows.
- The existing "conversation starter %" and "reply speed" slides match the most-cited messaging-Wrapped stats and should stay. Reframing them per person ("fastest replier: Alex, 2 min median") is more engaging than a global average, but it falls into the "mask on share" tier.
- Group chats are a lower-risk people slide: "your most active group" plus "you wrote 31% of all messages in it" (your count ÷ group total from the both-sides `limit=1` search) is funny, social and not about one individual.

### Gaps
- I found no quantitative user study on discomfort with named contacts on share cards. The recommendation rests on the Facebook precedent and general privacy reasoning.
- No source found on how Messages Wrapped handles masking names on its share images.

## 4. Telegram-specific data that can power unique slides (verified against the TL schema)

### Takeaway
Telegram exposes far richer, *exactly countable* data than generic chat exports. That includes a server-side call log with durations and missed/video flags, voice and round-video notes with durations, reactions on each message, sticker-pack identity, custom emoji, dice games, forwards with origin channel, quotes, message effects, polls, stories archive, gifts/Stars, and "contact joined Telegram" service messages. Many of these can be counted with the same cheap `messages.search` + filter pattern the pipeline already uses.

### Cited Findings
(Verified by introspecting Telethon 1.45.0's generated TL layer — [Telethon on PyPI](https://pypi.org/project/Telethon/). The canonical docs are at core.telegram.org, e.g. [messageActionPhoneCall](https://core.telegram.org/constructor/messageActionPhoneCall), [messages.search](https://core.telegram.org/method/messages.search) and [messages.getSearchCounters](https://core.telegram.org/method/messages.getSearchCounters), but those pages were blocked for fetching.)
- **Calls:** `MessageActionPhoneCall(call_id, video, reason, duration)`. `reason` is one of `PhoneCallDiscardReasonMissed/Busy/Hangup/Disconnect/MigrateConferenceCall`, and `Message.out` gives direction. A search filter `InputMessagesFilterPhoneCalls` exists, as does `MessageActionGroupCall(call, duration)` for group voice chats and `MessageActionConferenceCall`. → total call minutes, video vs voice, longest call, missed calls, top call partner, call-hour heatmap.
- **Voice / round video notes:** `DocumentAttributeAudio(duration, voice, …)` and `DocumentAttributeVideo(duration, round_message, …)`, with search filters `InputMessagesFilterVoice`, `InputMessagesFilterRoundVoice` and `InputMessagesFilterRoundVideo`. `messages.search` accepts `from_id` and `min_date`/`max_date` together with `filter`. → exact count of voice notes sent; total minutes requires reading each voice message (100 per page).
- **Per-filter counters in one call:** `messages.GetSearchCountersRequest(peer, filters, …)`. It has **no `from_id` parameter**, so it returns both-sides counts per chat (photos, videos, voice, links, polls, …), not just the user's.
- **Reactions:** `Message.reactions` is `MessageReactions(results=[ReactionCount(reaction, count, chosen_order)], recent_reactions=[MessagePeerReaction(peer_id, date, reaction, big, unread, my)], top_reactors, …)`. `chosen_order` / `my` mark reactions the user gave. Also `GetMessageReactionsListRequest`, `GetTopReactionsRequest` and `GetRecentReactionsRequest` (account-level, not year-bounded). → most-reacted message (existing), reactions received in total, your go-to reaction.
- **Stickers & custom emoji:** `DocumentAttributeSticker(alt, stickerset, …)` gives the pack identity → "top sticker *pack*". `MessageEntityCustomEmoji(offset, length, document_id)` and `DocumentAttributeCustomEmoji` → custom (Premium) emoji usage. Account-level `GetRecentStickersRequest` and `GetFavedStickersRequest` also exist.
- **Forwards:** `MessageFwdHeader(from_id, from_name, channel_post, saved_from_peer, date, …)` → "channels you forward from most" (your news/meme diet). These are public entities, so they are safe on a share card.
- **Replies / quotes / threads:** `MessageReplyHeader(reply_to_msg_id, quote, quote_text, forum_topic, reply_to_top_id, …)`. **Edits:** `Message.edit_date`. **Effects:** `Message.effect` (message effects). **Self-destruct:** `Message.ttl_period`. **Pinned:** `Message.pinned` and `InputMessagesFilterPinned`. **Via bot:** `Message.via_bot_id` (inline bots used).
- **Polls / dice / location / todo:** `MessageMediaPoll`, `MessageMediaDice(value, emoticon, …)` (🎲🎯🏀⚽🎰🎳 mini-games with outcomes), `MessageMediaGeoLive`, `MessageMediaToDo`, `MessageMediaStory`, `MessageMediaPaidMedia`.
- **Service actions available** (selection): `MessageActionContactSignUp` (a contact joined Telegram), `MessageActionChatJoinedByLink`, `MessageActionChatAddUser`, `MessageActionChatCreate` / `MessageActionChannelCreate`, `MessageActionGiftPremium`, `MessageActionStarGift` / `MessageActionStarGiftUnique`, `MessageActionGiftStars`, `MessageActionPrizeStars`, `MessageActionSetChatTheme` / `SetChatWallPaper`, `MessageActionTopicCreate`, `MessageActionScreenshotTaken`, `MessageActionSuggestBirthday`, `MessageActionTodoCompletions`.
- **Stories:** `stories.GetStoriesArchiveRequest(peer, offset_id, limit)` → stories the user posted (`StoryItem` carries view/reaction counts).
- **Saved Messages:** `GetSavedDialogsRequest` and `GetSavedHistoryRequest` → "notes to self" and what you saved from where. The pipeline currently skips Saved Messages.
- **Top peers:** `contacts.GetTopPeersRequest` with categories `correspondents`, `phone_calls`, `forward_users`, `forward_chats`, `groups`, `channels`, `bots_inline`, `bots_pm`, `bots_app`. This is a cheap Telegram-computed ranking, but it is a decayed rating, not a yearly count, and it is empty if the user disabled "suggest frequent contacts".
- **Common chats:** `messages.GetCommonChatsRequest(user_id, …)` → "you and Alex share 7 groups".

### Inferences
- **Calls are the biggest untapped, Telegram-native, exact, and emotionally resonant stat.** "You spent 41 hours on Telegram calls; the longest was 3h12m with Sam on 14 Feb" mirrors Discord's voice-time stat. If Telethon's `client.get_messages(None, filter=InputMessagesFilterPhoneCalls)` or `messages.search` with an empty peer works for a global call log (as official clients appear to use it), this costs only a few pages. Needs a live check with `scripts/live_check.py`.
- **Voice-note minutes** ("you recorded 6.2 hours of voice messages"), **sticker packs** and **forward sources** are cheap, accurate and Telegram-flavoured.
- **Year-over-year** is cheap: repeat the per-dialog count search with last year's dates (one extra `limit=1` search per top dialog) → "+23% vs 2024", "new people this year" (chats with no messages before Jan 1). It gives a "Music Evolution"-style narrative from exact data instead of invented labels.
- "Contacts who joined Telegram this year" (`MessageActionContactSignUp`), "groups you created/joined", and "gifts/Stars sent and received" are niche but distinctive. Good as optional slides, shown only when non-zero.
- `ScreenshotTaken` (mostly secret chats) and `ttl_period` are too niche or creepy. Skip.

### Gaps
- Not verified live: whether a global (`InputPeerEmpty`) phone-call search returns the full-year call log for all users, and how many pages it costs. Whether call service messages show up in `messages.search(from_id=self)` (the direction comes from `out`). Needs `scripts/live_check.py`.
- Telegram does not expose per-message read timestamps or "typing" history, so read-receipt and ghosting stats can't be computed (inference from the absence of such fields in the schema).

## 5. Pacing, accessibility and shareable-card design

### Takeaway
Use a 9:16 story format with tap/swipe navigation, one idea per card, a strong closing summary card, and per-slide share images. Default the share image to privacy-safe content (no contact names, no message text). Keep the deck tight: Wrapped-style decks lean on 10–15 cards, and copycat fatigue is real. Slides with nothing interesting to say should be skipped automatically.

### Cited Findings
- Strava lets users share images directly from the report to Instagram/TikTok/messaging, with customisable summary images — [Strava Support](https://support.strava.com/en-us/articles/15401959-your-year-in-sport)
- Designs are made to catch attention on social feeds. If people "see themselves in the story" they are more likely to share — [Ditto](https://dittoditto.io/insights/end-of-year-campaigns-inspiration)
- Wrapped presents a year of data "in a series of audiovisual slides", and identity labels are central — [Annabell & Rasmussen 2025](https://journals.sagepub.com/doi/10.1177/14614448251391301)
- Recap fatigue: PC Gamer called Discord's Checkpoint "yet more needless features" — [PC Gamer](https://www.pcgamer.com/software/adding-yet-more-needless-features-discord-joins-the-wrapped-crew-with-a-yearly-stat-recap-called-checkpoint/)

### Inferences
- **Card checklist (synthesis):** 1080×1920 export; one hero number or label per card; a short caption explaining the derivation ("based on 12,430 messages you sent"); a small "estimated" badge when `accuracy.mode` is estimated; Telegram Wrapped branding + URL in the footer (the viral loop); high-contrast text that never relies on colour alone; respect `prefers-reduced-motion` for animated numbers; tap zones plus keyboard arrows (already present); alt text / aria-live for the revealed number.
- **Share-safety defaults:** a share-mode toggle with "Show names / Initials / Hide". Hide by default on the summary card. Never put message text (most-reacted message, phrases) on an exported image unless the user explicitly reveals it.
- **Pacing:** ~10–12 core slides, with optional slides appearing only when the data is notable (e.g. a calls slide only if >30 min of calls; stickers only if ≥N sent). This avoids "boring" slides such as "you sent 3 voice notes".

### Gaps
- No primary source found with an optimal slide count or completion/drop-off rates for Wrapped decks. The 10–15 figure is my estimate from typical Wrapped decks, not a cited measurement.
- No accessibility audit of Spotify Wrapped found within budget.

## 6. Recommended slide list: keep / rework / drop / new

### Takeaway
Keep the exact, people- and Telegram-native slides. Merge the overlapping rhythm/streak/peak-hour slides. Keep at most two persona slides (archetype + vibe age), each with a visible "because". Demote phrase mining to private-only or drop it. Add calls, voice-note minutes, sticker packs, groups, year-over-year/new people, and an optional forwards/"news diet" slide.

### Cited Findings
- Explainable playful metrics succeeded (listening age, 2025), while unexplained or AI-generic labels were mocked (Music Evolution and the AI podcast, 2024) — [Music Ally](https://musically.com/2025/12/05/clubs-fan-leaderboards-listening-age-wrapped-2025-reveals-a-new-set-of-features/); [Fast Company](https://www.fastcompany.com/91454685/spotify-wrapped-2025-eagerly-checking-your-listening-age-everyone-else-is-too); [Several](https://several.com/news/spotify-wrapped-2024-backlash)
- Personas with a collectible ending (Discord's 10 cards + avatar decoration; Spotify's 12 "Me in 2023" characters; Duolingo learner styles) are standard — [How-To Geek](https://www.howtogeek.com/discord-checkpoint-is-the-end-of-year-recap-you-never-knew-you-needed/); [Time](https://time.com/6340656/spotify-wrapped-guide-2023/); [Lingoly](https://lingoly.io/duolingo-year-in-review-2024/)
- Messaging recaps that went viral centred on who-texts-first, response speed and top people/groups, from metadata only — [Product Hunt](https://www.producthunt.com/products/messages-wrapped)
- Telegram data fields supporting the new slides: see Section 4 (Telethon 1.45.0 schema; [PyPI](https://pypi.org/project/Telethon/))

### Inferences
The table below is my synthesis. "Data" says whether the stat comes from exact counts (E), weighted/estimated records (W), or advanced text/ML analysis (A).

| # | Slide | Verdict | Data | Rationale |
|---|---|---|---|---|
| 1 | Total messages sent | **Keep** (hero opener) | E | Exact Σ of per-chat search counts; the Wrapped "minutes" equivalent. Add a YoY delta. |
| 2 | Year in rhythm (monthly chart, busiest day, active days) + **longest streak** | **Keep, merge** streak into it | W/E | Rhythm, streak and active days are one story. Streak as a separate slide is thin. Busiest day and streak only from exact windows (already the case). |
| 3 | Peak hour / night owl | **Keep, merge** with rhythm *or* turn into a persona chip | W | A well-understood persona ("Night owl: 31% after midnight"). Add "3 a.m. club": messages sent 1–5 am. |
| 4 | Top conversations | **Keep** (core) | E | Most compelling messaging stat. Mask names on share by default. Skip chats that went silent late in the year as "top" (ex/deceased risk). |
| 5 | Conversation starter % | **Keep** | W (sampled windows) | Matches the viral "who texts first" stat. Per-friend framing is better; label as estimate. |
| 6 | Reply speed | **Keep / rework** to "fastest replier" + your median | W | Matches "fastest/slowest responders". A global average alone is dull. |
| 7 | Most-reacted message | **Keep** (Telegram-unique) | E (per fetched msg) | Funny and specific. Message text must be blurred on export by default. Only shown if reactions ≥ threshold. |
| 8 | Media mix | **Rework** → "How you talk": text vs voice vs video notes vs stickers, with **voice-note minutes** as the hero | E | Exact counts via filters; minutes are memorable. Plain percentages are boring. |
| 9 | Top stickers | **Keep, upgrade** to top sticker **pack** + top sticker | E | Visual, Telegram-native, safe to share. |
| 10 | Emoji personality | **Merge** with stickers/reactions into "Your emoji & reactions" | E/W | Emoji alone overlaps with stickers. Add "your go-to reaction" and custom emoji. |
| 11 | Texter personality (16 MBTI-like types) | **Rework**: fewer, clearer archetypes (≈8–10), each with a 1-line "because" from 2–3 visible stats; make it the collectible end card | A | Personas drive shares, but 16 opaque codes from z-scored features risk the "Music Evolution / Sound Town" credibility problem. The EVTM×INRD code adds jargon. |
| 12 | Vibe age | **Keep** (direct analogue of 2025's hit "listening age"), show 2–3 driving signals | A | Explainability is the difference between a hit and a meme of the bad kind. |
| 13 | Vocabulary / most used phrases | **Demote or drop**: private-only, never on share cards; drop entirely in estimated mode or when phrases are generic | A | Highest risk of generic ("i think that") or privacy-leaking output. Viral messaging recaps avoided reading text. Expensive (full-text). |
| 14 | Summary card | **Keep, fix privacy** | — | Currently renders `topChat.name` on the share image (SummarySlide.tsx L83–88). Default to masked, add archetype + vibe age + 3 exact numbers. |
| N1 | **Calls** (minutes, longest call, video vs voice, top call buddy, missed calls) | **New** | E | Telegram-native and exact; analogous to Discord voice time. Only shown if ≥ threshold. Needs live verification of the global call-log search. |
| N2 | **Group life** (most active group; "you wrote X% of its messages"; groups joined/created) | **New** | E | Social but not about one person; uses the both-sides total already fetched for top chats. |
| N3 | **Year-over-year / new people** ("+23% vs 2024", "7 new people you talk to weekly") | **New** | E | Cheap extra `limit=1` searches. A data-grounded alternative to "Music Evolution". Avoid a shareable "faded friends" list. |
| N4 | **Forwards / your feed** (top channels you forward from) | **New, optional** | E (from fetched msgs) | Public entities, safe and fun ("you're the #1 distributor of @memes"). Needs `fwd_from` on fetched records. |
| N5 | **Saved Messages / notes to self** | **New, optional** | E | Relatable ("you texted yourself 412 times"). Saved Messages is currently excluded from selection, so it needs a separate count. |
| N6 | **Mini-games & extras** (🎲 dice rolls, polls, stories posted, gifts/Stars, friends who joined Telegram) | **Optional, auto-hide if small** | E | Distinctive Telegram flavour. Only show the 1–2 most notable for the user. |
| N7 | **Percentile** ("more messages than 87% of users") | **New, later** | E + aggregate | Duolingo/Spotify-style comparison. Needs anonymised aggregates across runs. |

**Drop/avoid list:** "left on read" or ghosting (can't be computed accurately on Telegram), "who you ignore most" (hurtful and unshareable), a "faded friends" share card (ex/deceased risk, Facebook 2014), word clouds and sentiment scores (generic, error-prone), and LLM-written narrative paragraphs (2024 Wrapped backlash).

**Simple exact counts vs advanced analysis:**
- *Exact / cheap:* total, per-chat counts, YoY, calls, voice/round counts (and minutes from fetched docs), stickers/packs, reactions, groups, Saved Messages, forwards, dice/polls/stories/gifts.
- *Weighted / sampled:* hourly/weekday/monthly distributions, starters, reply speed.
- *Advanced (A):* archetype, vibe age, phrases/inside jokes, topics. "Inside jokes" (phrases distinctive to one chat vs. your global usage) is technically possible with the existing LLR×TF-IDF machinery per chat. But it requires reading text and can expose private content, so it should be private-only if built at all.

### Gaps
- No user-testing data for this app: the verdicts above should be validated with a small A/B test or slide-level analytics (completion and per-slide share/download rates). The app's PNG downloads could be instrumented for this.
- Calls and global Saved Messages queries need cost and accuracy checks with `scripts/live_check.py` before committing to them.
