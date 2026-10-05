# Models, LLM cost and privacy for Telegram Wrapped analysis (topics, mood, personality, vibe age, friend summaries)

Research date: 2026-10-05. Context: user with up to ~500k messages across ~200 chats, possibly mixed Russian/English. The current codebase already ships a deterministic 16-type "EVTM x INRD" personality classifier and a z-score "vibe age" (13-75) model (`backend/app/ml/inference.py`, `vibe_age.py`), and LLR x TF-IDF phrase extraction, all server-side (per repo CLAUDE.md). Note: several primary sources (core.telegram.org, huggingface.co, gdpr-info.eu, privacy.claude.com, opentermsarchive.org) were blocked by this session's network proxy; claims about them come from search-result summaries and are flagged where relevant.

## Topic modeling for short, informal, multilingual chat messages

### Takeaway
Classic LDA is a poor fit for one-line chat messages; embedding-based clustering (BERTopic-style: multilingual sentence embeddings -> UMAP -> HDBSCAN or k-means -> c-TF-IDF keywords) is the evidence-backed default for short multilingual text, ideally run on *conversation sessions* rather than single messages, with an optional small LLM pass only to turn cluster keywords + a few sample lines into a human label. multilingual-e5-small (47M params, 384-d) is the best size/quality trade-off for on-device; bge-m3 (568M, 1024-d) is the quality ceiling but ~12x larger.

### Cited Findings
- LDA struggles on short text because of data sparseness, and performs poorly on unconventional/short documents; BERTopic outperforms LDA and NMF in topic coherence and diversity, especially in low-resource and short-text settings — [Multilingual transformer and BERTopic for short text topic modeling: The case of Serbian (arXiv 2402.03067)](https://arxiv.org/pdf/2402.03067)
- On low-resource, morphologically rich languages (Serbian, Marathi), BERTopic with a monolingual or robust multilingual SBERT outperforms LDA and NMF in coherence and diversity; unlike LDA, BERTopic needs language-appropriate (or multilingual) sentence embeddings — [arXiv 2402.03067](https://arxiv.org/pdf/2402.03067); [Springer chapter version](https://link.springer.com/chapter/10.1007/978-3-031-50755-7_16)
- BERTopic applied to tweets (with NMF and LDA as baselines) achieved high coherence, the highest on lightly preprocessed tweets — [arXiv 2402.03067](https://arxiv.org/pdf/2402.03067)
- A comparison of LDA vs BERTopic with HDBSCAN and with k-means on short student comments/news found BERTopic+HDBSCAN had the highest coherence and diversity — [Experiments on Generalizability of BERTopic on Multi-Domain Short Text (arXiv 2212.08459)](https://arxiv.org/pdf/2212.08459)
- LDA/NMF require the number of topics up front (needs tuning); BERTopic (HDBSCAN) does not — [arXiv 2402.03067](https://arxiv.org/pdf/2402.03067)
- Further short-text replications: Hindi short texts [arXiv 2501.03843](https://arxiv.org/pdf/2501.03843); adolescent-health short text optimisation of BERTopic [PMC12378273](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12378273/)
- Embedding model sizes: multilingual-e5-small = 47M params / 384 dims; paraphrase-multilingual-MiniLM-L12-v2 = 118M / 384 dims; bge-m3 = 568M / 1024 dims — [aimultiple: Top multilingual embedding models](https://aimultiple.com/multilingual-embedding-models) (secondary aggregator; sizes consistent with model cards, which could not be fetched here)
- Quality: on Polish MTEB (small-model class <150M), multilingual-e5-small averaged 46.00 vs 30.40 for paraphrase-multilingual-MiniLM-L12-v2 — [PL-MTEB (arXiv 2405.10138)](https://arxiv.org/html/2405.10138v2). On French MTEB, bge-m3 0.88 reranking / 0.60 retrieval vs multilingual-e5-small 0.82 / 0.52, with performance correlating with dimension and parameter count — [MTEB-French (arXiv 2405.20468)](https://arxiv.org/pdf/2405.20468)
- e5 models use asymmetric "query:/passage:" prefixes; bge-m3 is hybrid (dense+sparse+multi-vector); paraphrase-multilingual-MiniLM is a symmetric similarity model — [aimultiple](https://aimultiple.com/multilingual-embedding-models)
- Broad multilingual benchmark for choosing embedders (250+ languages, incl. Russian): [MMTEB (arXiv 2502.13595)](https://arxiv.org/html/2502.13595v1)

### Inferences
- Recommended pipeline: (1) **sessionise** each chat: split on idle gaps (e.g. >30-60 min with no message from either side; tune on real data) and concatenate a session's messages (both sides, or own side only if privacy-limited) into one "document" of ~50-300 tokens. This directly fixes LDA's/embeddings' sparsity problem on 3-word messages and matches how people perceive "a conversation about X". (Gap-based sessionisation is a common heuristic; I found no chat-specific paper benchmarking the threshold — see Gaps.) (2) Embed sessions with multilingual-e5-small (or bge-m3 server-side). (3) UMAP + HDBSCAN (or k-means with k~15-30 if you want a fixed number of slide topics). (4) c-TF-IDF keywords per cluster, filtering stop-words in both RU and EN. (5) Optional LLM labelling: send only cluster keywords + 5-10 *redacted* example lines per cluster to get a 2-4 word label/emoji.
- Mixed RU/EN code-switching is handled natively by multilingual embedders (shared embedding space), which LDA cannot do without per-language vocabularies.
- For 500k messages, sessionisation probably yields on the order of 10k-50k sessions (estimate, depends on chat style), which keeps embedding cost manageable even in the browser (see on-device section).
- Pure "LLM summarisation of sampled conversation windows" is the most readable option but the most privacy-exposing and costly; best reserved as an opt-in enhancement on top of clustering, not the backbone.

### Gaps
- No paper found that benchmarks topic models specifically on private messenger chats (Telegram/WhatsApp) or on RU/EN code-switched chat; evidence comes from tweets, comments and news.
- No source found giving an empirically validated idle-gap threshold for chat sessionisation.
- Hugging Face model cards (exact multilingual-e5-small / bge-m3 file sizes, ONNX quantised sizes) could not be fetched (egress blocked).

## Sentiment / emotion on informal multilingual chat

### Takeaway
Use a small fine-tuned multilingual classifier (cardiffnlp twitter-xlm-roberta-base-sentiment, 3-class) for "mood over the year", aggregated per week/month, plus an emoji-sentiment lexicon as a cheap extra signal; for Russian specifically, rubert-tiny2 emotion models are tiny and fast. Expect only moderate per-message accuracy (macro-F1 ~0.56-0.77 depending on language), which is fine for aggregate trends but not for judging single messages. Zero-shot LLMs are competitive on plain polarity but fine-tuned small models win on emotion categories.

### Cited Findings
- XLM-T: XLM-R further pre-trained on ~200M tweets in 30+ languages, then fine-tuned for 3-class (positive/negative/neutral) sentiment on the UMSAB benchmark of 8 languages (Arabic, English, French, German, Hindi, Italian, Spanish, Portuguese); can be used for other languages — [XLM-T paper, LREC 2022](https://aclanthology.org/2022.lrec-1.27.pdf); [arXiv 2104.12250](https://arxiv.org/pdf/2104.12250); [model card](https://huggingface.co/cardiffnlp/twitter-xlm-roberta-base-sentiment)
- Reported macro-F1 for XLM-Twitter multilingual fine-tuning ranges from 56.4 (Hindi) to 77.3 (German), 69.4 overall; XLM-Twitter beat XLM-R in 6 of 8 languages — [XLM-T GitHub](https://github.com/cardiffnlp/xlm-t); [arXiv 2104.12250](https://arxiv.org/pdf/2104.12250)
- Russian is *not* among the 8 sentiment fine-tuning languages (it is in the 30+ pre-training languages) — [XLM-T GitHub](https://github.com/cardiffnlp/xlm-t)
- Russian-specific: rubert-tiny2 fine-tuned on the CEDR dataset (Sboev et al.) for multi-label emotion (no_emotion, joy, sadness, surprise, fear, anger) — [cointegrated/rubert-tiny2-cedr-emotion-detection](https://huggingface.co/cointegrated/rubert-tiny2-cedr-emotion-detection); variants with 9 emotions + neutral — [Aniemore/rubert-tiny2-russian-emotion-detection](https://huggingface.co/Aniemore/rubert-tiny2-russian-emotion-detection); Russian sentiment — [seara/rubert-tiny2-russian-sentiment](https://huggingface.co/seara/rubert-tiny2-russian-sentiment)
- GoEmotions is 28 fine-grained labels, English-only; multilingual classifiers with GoEmotions labels exist (e.g. a model claiming English + 35 languages) — [arXiv 2604.12633: Multilingual Multi-Label Emotion Classification at Scale with Synthetic Data](https://arxiv.org/abs/2604.12633); [Horizon-Labs/multilingual-emotions-small](https://huggingface.co/Horizon-Labs/multilingual-emotions-small)
- In that 2026 paper, XLM-R-Large (560M) reached 0.868 F1-micro in-domain but only 0.534 F1-micro on GoEmotions — i.e. fine-grained emotion transfer is much weaker than polarity — [arXiv 2604.12633](https://arxiv.org/html/2604.12633)
- LLMs (ChatGPT) show strong zero-shot performance on simple sentiment classification, comparable to fine-tuned T5, but lag on more complex/structured sentiment tasks — [Sentiment Analysis in the Era of LLMs: A Reality Check (arXiv 2305.15005)](https://arxiv.org/pdf/2305.15005)
- Fine-tuned smaller models consistently beat zero-shot prompting of larger models (incl. ChatGPT, Claude Opus) in text classification, with the gap larger for less standard tasks like emotion detection — [Fine-Tuned 'Small' LLMs (Still) Significantly Outperform Zero-Shot Generative AI Models (arXiv 2406.08660)](https://arxiv.org/html/2406.08660v1)
- Zero-shot multilingual aspect-based sentiment with LLMs generally falls short of fine-tuned task-specific models — [arXiv 2412.12564](https://arxiv.org/abs/2412.12564)
- Emoji as signal: Emoji Sentiment Ranking — lexicon of 751 emojis from 1.6M tweets in 13 European languages (incl. Russian), 70k tweets labelled by 83 annotators; most emojis are positive; no significant differences in emoji sentiment across the 13 languages; emojis tend to occur at message end — [Kralj Novak et al., PLoS ONE 2015](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0144296); [dataset (CLARIN.SI)](https://www.clarin.si/repository/xmlui/handle/11356/1048)

### Inferences
- "Mood over the year" should be an aggregate: mean (positive - negative) per week/month, smoothed, with emoji-lexicon score blended in. Aggregation averages out per-message errors; show trends and peaks, not "your saddest message".
- Language-route: detect language per message (cheap fastText/CLD3-style detector) and route Russian to rubert-tiny2 models and everything else to XLM-T; or use XLM-T for all and accept weaker Russian accuracy. Emoji lexicon is language-independent, which makes it valuable for code-switched text.
- Chat sarcasm, in-jokes and ")))" (Russian smiley convention) are likely failure modes; a custom rule for ")" / "(" runs would be worth testing on RU users.
- Sentiment/emotion trends could hint at mental-health states; presenting "your saddest month" is sensitive (and may edge toward GDPR Art. 9 health data — see privacy section). Framing as "your most emoji-happy month" is safer.

### Gaps
- No published accuracy for these models on private messenger chat text (all benchmarks are tweets or curated sentences).
- Did not find an evaluation of XLM-T on Russian tweets specifically.

## Personality / style ("texter personality") and "vibe age"

### Takeaway
Predicting validated Big Five traits from social-media language works only at a "moderate" correlation (r ~0.29-0.40), insufficient for individual assessment; MBTI-style 16 types are psychometrically weak (about half of people get a different 4-letter type on retest). A "16 types" slide is defensible only as an explicitly playful label built from transparent, descriptive style metrics (verbosity, emoji density, reply speed, initiator rate, night-owl share). Age-from-text has MAE of ~4-7 years in research settings, so "vibe age" must be framed as a style comparison, never as an estimate of real age.

### Cited Findings
- Meta-analysis: Big Five prediction from social-media digital footprints correlates r = 0.29 (agreeableness) to 0.40 (extraversion), similar to the typical "personality coefficient" (0.30-0.40) — [Azucar, Marengo & Settanni 2018, Personality and Individual Differences (meta-analysis)](https://www.sciencedirect.com/science/article/abs/pii/S0191886917307328); [PDF](https://www.almendron.com/tribuna/wp-content/uploads/2018/03/predicting-the-big-5-personality-traits-from-digital-footprints-on-social-media-a-meta-analysis.pdf)
- Digital footprints infer Big Five with moderate accuracy but still fall short of accuracy allowing assessment at the individual level — [Digital Psychology 2020](https://ejournals.facultas.at/index.php/digitalpsychology/article/download/1823/1584) (as summarised in search results)
- MBTI: ~50% of people get a different four-letter type on retest; the publisher itself acknowledges about 50% get the same whole type on retest while scale-level test-retest correlations exceed .80 — [The Myers-Briggs Company: MBTI Facts](https://ap.themyersbriggs.com/themyersbriggs-mbti-facts.aspx); critiques — [Pittenger, "Cautionary comments regarding the MBTI"](https://www.researchgate.net/publication/232494957_Cautionary_comments_regarding_the_Myers-Briggs_Type_Indicator); [Boyle, "MBTI: some psychometric limitations"](https://www.researchgate.net/publication/27827048_Myers-Briggs_Type_Indicator_MBTI_Some_psychometric_limitations)
- Root cause: MBTI dichotomises continuous scores, so people near the midpoint flip type with small changes; critiques also cite lack of bimodal distributions and weak predictive validity — [Pittenger](https://www.researchgate.net/publication/232494957_Cautionary_comments_regarding_the_Myers-Briggs_Type_Indicator) (summary via search; secondary blog sources not relied on)
- Age from text: linear regression on shallow text features reached correlations up to 0.74 and MAE of 4.1-6.8 years across blogs, telephone conversations and forum posts — [Nguyen, Smith & Rosé 2011, "Author Age Prediction from Text using Linear Regression"](https://aclanthology.org/W11-1515.pdf)
- Age/gender predictive lexica built from social media (Schwartz group) — [Sap et al. 2014, EMNLP](https://aclanthology.org/D14-1121.pdf); difficulties of age prediction from tweets — [Nguyen et al., COLING 2014, "Why Gender and Age Prediction from Tweets is Hard"](https://www.dongnguyen.nl/publications/nguyen-coling2014.pdf)

### Inferences
- The current EVTM x INRD classifier is fine as entertainment if the slide (a) shows the underlying metrics that drove each letter, (b) avoids MBTI branding/claims of psychological validity, and (c) uses wording like "your texting style" not "your personality". Continuous dimensions with near-midpoint users labelled "balanced" would reduce the type-flip problem MBTI suffers from.
- Safer, fun descriptive dimensions, all computed exactly from metadata already fetched by the pipeline: verbosity (median chars/message, message-burst length), emoji/sticker density, reply speed (median), initiator rate (share of conversation starts), night-owl share (% of messages 23:00-04:00), question rate, voice-message share, edit/forward rates.
- "Vibe age": research MAE 4-7 years on longer texts; private-chat one-liners in mixed languages would likely be worse. Present as "you text like someone who is ~X" with a joke tone, never infer/claim real age, avoid applying to contacts, and be careful with minors (implying a user is 13 could be sensitive). A safer variant: "your slang era" (e.g. which year's slang dominates) based on lexical markers.
- Personality/age inference about *contacts* (per-friend summaries) is more ethically fraught than about the user themself; keep friend summaries to relational facts (who starts, reply speed, shared topics, peak months).

### Gaps
- No study found validating any "texter type" taxonomy or predicting personality specifically from private messenger metadata (reply speed, initiation).
- No study found on age prediction accuracy for Russian or code-switched chat.

## On-device analysis in the browser (transformers.js / ONNX Runtime Web / WebGPU / WebLLM)

### Takeaway
Embedding models (e5-small class) and small classifiers run comfortably in-browser: with WebGPU and batching, ~190 documents/s on a laptop-class GPU (3.7-5.7x faster than WASM), so ~100k short texts take roughly 5-15 minutes; WASM is better for single, low-latency calls. Small LLMs (0.5-3B, 4-bit) run via WebLLM with 0.3-2 GB downloads and ~20-60 tokens/s on integrated GPUs, which is enough to *label* ~20-30 topic clusters or write a handful of short summaries, but not to read 100k messages.

### Cited Findings
- Transformers.js: for small embedding models on short inputs (<128 tokens), WASM matches or beats WebGPU per single call (M2 MacBook Air: WASM ~8-12 ms vs WebGPU ~15-25 ms per embedding) because of GPU buffer-transfer overhead — [SitePoint: WebGPU vs WebASM browser inference benchmarks](https://www.sitepoint.com/webgpu-vs-webasm-transformers-js/)
- Batched: encoding 1,000 Natural Questions documents at batch 64, browser WebGPU achieved 187 docs/s vs WASM 51 docs/s; WebGPU 3.7-5.7x faster for embeddings at scale — [Bekko Embedding (arXiv 2607.25180)](https://arxiv.org/pdf/2607.25180) (attribution via search summary; numbers for that paper's compact encoder)
- Hugging Face's Transformers.js WebGPU embedding benchmark: one developer reported a 64x speedup over WASM on their device (device-dependent outlier) — [Xenova post on Hugging Face](https://huggingface.co/posts/Xenova/906785325455792)
- Transformers.js v3 (Oct 2024) added WebGPU support — [MarkTechPost](https://www.marktechpost.com/2024/10/23/transformers-js-v3-released-bringing-power-and-flexibility-to-browser-based-machine-learning/); v4 + WebGPU usage guide — [vadimall.com](https://vadimall.com/posts/transformers-js-v4-webgpu-browser-ai-typescript)
- WebLLM (MLC): in-browser LLM inference via WebGPU + WASM; retains up to ~80% of native MLC-LLM decode throughput on the same device — [WebLLM paper (arXiv 2412.15803)](https://arxiv.org/html/2412.15803v2); [GitHub mlc-ai/web-llm](https://github.com/mlc-ai/web-llm)
- Example download sizes / VRAM: Qwen3 0.6B 335 MB / ~1.4 GB VRAM; Llama 3.2 1B 695 MB / ~880 MB; Qwen3.5 2B 1.06 GB / ~2.2 GB; Llama 3.1 8B 4.5 GB / ~5 GB — [pinggy.io: Run an LLM inside a browser tab (2026)](https://pinggy.io/blog/run_llm_in_browser_webgpu/) (blog; figures plausible but secondary)
- Qwen2.5-0.5B on a recent integrated GPU: time-to-first-token ~0.5-2 s, decode 20-60 tokens/s — [same pinggy.io / tinyweights.dev summaries](https://tinyweights.dev/posts/run-llm-in-browser-webllm/) (secondary)
- Llama 3.2 1B/3B need ~1-2 GB and suit browser deployment; Qwen2.5 1.5B ~1 GB and 3B ~2 GB at INT4 — [search summaries of WebLLM guides](https://www.programming-helper.com/tech/webllm-2026-running-large-language-models-entirely-in-browser-webgpu) (secondary)
- Recent research on memory-efficient multi-precision WebGPU LLM inference — [Llamas on the Web (arXiv 2605.20706)](https://arxiv.org/html/2605.20706v1)

### Inferences
- Throughput maths: 100k session-documents / 187 per s ≈ 9 min on WebGPU; ≈ 33 min on WASM at 51/s. Chat sessions are shorter than NQ passages, so real throughput for a 47M-param e5-small should be at or above these numbers on laptops; phones (and browsers without WebGPU, notably older iOS Safari) will be several times slower — embed sessions (tens of thousands), not raw messages (500k), and run in a Web Worker with progress UI.
- Sentiment with a ~280M XLM-R base classifier is ~6x heavier than e5-small; for on-device, prefer distilled/quantised variants or run sentiment only on a stratified sample (e.g. 20-50k messages) — trend estimates do not need every message.
- A key architectural tension: the current app fetches messages server-side via MTProto (Telethon), so "on-device" requires either shipping message text to the browser (then analysing locally and never storing it server-side) or moving MTProto into the client (e.g. a JS MTProto client). The privacy win of on-device ML is only real if text never persists on the server.
- A 1-3B browser LLM is adequate for labelling clusters from keywords/snippets in English; quality on Russian slang from 1B models is likely poor (not verified) — test before relying on it.

### Gaps
- No rigorous, first-party benchmark found for transformers.js throughput on phones for multilingual-e5-small, or for XLM-R-base sentiment in-browser.
- WebLLM per-model tokens/s tables on specific laptops/phones were not obtained from primary sources (only blogs).

## LLM API option: cost per user, batching/caching, latency

### Takeaway
If the LLM only sees aggregates, candidate phrases, cluster keywords and a small redacted sample, cost is a few cents per user: ~$0.05 on Claude Haiku 4.5 at list price (~$0.03 with Batch), ~$0.10-0.20 for a heavier "sampled windows" design; sending all 500k messages would cost several dollars on Haiku and is neither necessary nor defensible on privacy. Cheaper models (Gemini 2.5 Flash-Lite, GPT-5 nano) are ~10x cheaper on input but the cost is already small in the minimal design.

### Cited Findings
- Claude pricing (official, fetched 2026-10-05), per million tokens: **Haiku 4.5** $1 input / $5 output; 5-min cache write $1.25, 1-h cache write $2, cache hit $0.10. **Sonnet 5 / Sonnet 5.5** $2 / $10 (Sonnet 5's $2/$10 introductory price is now standard; planned rise to $3/$15 on 2026-09-01 will not occur). Sonnet 4.5/4.6 $3 / $15. Opus 5.5 $4 / $20 — [Anthropic pricing docs](https://platform.claude.com/docs/en/about-claude/pricing)
- Batch API: 50% discount on input and output (Haiku 4.5 batch $0.50 / $2.50); batch and caching discounts stack — [Anthropic pricing docs](https://platform.claude.com/docs/en/about-claude/pricing)
- Prompt caching: 5-min write 1.25x, 1-h write 2x, read 0.1x base input; pays off after one read (5-min) — [Anthropic pricing docs](https://platform.claude.com/docs/en/about-claude/pricing)
- Claude 4.7+ models use a newer tokenizer producing ~30% more tokens for the same text (Haiku 4.5 and Sonnet 4.6 and earlier use the previous tokenizer); ~4 characters or 0.75 English words per token, varying by language — [Anthropic pricing docs](https://platform.claude.com/docs/en/about-claude/pricing)
- US-only inference (`inference_geo: "us"`) costs 1.1x for Claude 4.6+ models — [Anthropic pricing docs](https://platform.claude.com/docs/en/about-claude/pricing)
- Anthropic's own example: ~10,000 support conversations at ~3,700 tokens each on Haiku 4.5 ≈ $37 — [Anthropic pricing docs](https://platform.claude.com/docs/en/about-claude/pricing)
- Competitors (2026, secondary aggregators): Gemini 2.5 Flash-Lite ~$0.10 / $0.40 per M tokens list (some providers $0.05 / $0.20); GPT-5 nano $0.05 / $0.40; GPT-5 mini $0.25 / $2.00 — [CloudZero Gemini pricing 2026](https://www.cloudzero.com/blog/gemini-pricing/); [pricepertoken.com](https://pricepertoken.com/pricing-page/model/google-gemini-2.5-flash-lite) (verify on ai.google.dev / openai.com before quoting)

### Inferences
Token budget per user (my estimates; Russian text typically tokenises less efficiently than English, so add ~1.5-2x for RU-heavy users — not verified with a tokenizer):

| Task | Input tokens | Output tokens |
|---|---|---|
| Label ~30 topic clusters (keywords + 5-10 redacted lines each) | ~12-15k | ~1k |
| Curate/rank ~200 candidate phrases already found by LLR | ~2-3k | ~0.5k |
| Per-friend summaries, top 10 (aggregate stats ~500 tok + ~40 redacted sample lines ~1k tok each) | ~15k | ~1.5k |
| Mood narrative from monthly sentiment aggregates | ~1k | ~0.3k |
| **Minimal design total** | **~35k** | **~3.5k** |

- Minimal design on Haiku 4.5: 0.035 x $1 + 0.0035 x $5 ≈ **$0.05/user** list; ≈ **$0.026/user** with Batch API. On Sonnet 5 ($2/$10): ≈ $0.11/user. At 100k users: ~$5k (Haiku list) / ~$2.6k (Haiku batch).
- "Heavy" design (summarise ~200 sampled conversation windows x ~400 tokens + 20 friends x 3k tokens ≈ 150k input, 10k output): Haiku ≈ $0.20/user list, ≈ $0.10 batch.
- "Send everything" (500k messages x ~15 tokens ≈ 7.5M input tokens): ≈ $7.5+ per user on Haiku 4.5 input alone; ~$0.40-0.75 on Flash-Lite/nano class — and maximally exposes third-party data. Not recommended.
- Prompt caching helps little here: the shared prefix (system prompt + output schema, ~1-2k tokens) is small relative to per-user content; it mostly matters when making ~10 per-friend calls that share the same user-level context (cache that context once, read it 10x at 0.1x).
- Latency: the minimal design is ~5-15 parallel calls of a few k tokens; with a fast small model this should add seconds, not minutes, to a pipeline that already takes minutes for MTProto fetching. The Batch API is asynchronous, so it fits only if the deck is delivered later (e.g. via the existing bot CTA / RESULT_TTL), not on the live progress screen.

### Gaps
- Batch API turnaround SLA and prompt-caching minimum cacheable length for Haiku 4.5 were not verified in this session (pricing page fetched; batch/caching docs not).
- Exact Russian vs English token ratios for Claude/Gemini tokenizers not measured.
- Google and OpenAI official pricing pages were not fetched; figures above are from aggregators.
- No official Anthropic latency (tokens/s, TTFT) figures obtained.

## Privacy, consent and legal (GDPR, DPAs, retention, Telegram API ToS)

### Takeaway
The app operator is a GDPR controller (the household exemption covers the user, not the service that provides the means), and messages contain contacts' personal data whose owners never consented; Telegram's terms also prohibit using data obtained from the platform to train/develop/deploy AI/ML except with explicit, per-context consent from *all* relevant users. This makes "send raw chats of user + contacts to a third-party LLM" high-risk. The defensible design is on-device/own-server deterministic analysis first, with any LLM call opt-in, limited to aggregates/candidate phrases/redacted snippets, under a DPA with no training and minimal (ideally zero) retention — and with legal review of whether even that is compatible with Telegram's AI clause.

### Cited Findings
- Telegram API ToS (summary of core.telegram.org/api/terms via search; page itself blocked here): users are prohibited from using, accessing or aggregating data obtained from the Telegram platform to train, fine-tune or otherwise engage in the development, enhancement or **deployment** of AI/ML models and similar technologies; exceptions may be granted where all relevant users individually provide explicit, informed, affirmative and continued consent strictly limited to the specific content and chat/context, and consent in one context is non-transferable — [Telegram API Terms of Service](https://core.telegram.org/api/terms); [Open Terms Archive memo: "Telegram prohibits collecting data for AI use"](https://opentermsarchive.org/en/memos/telegram-prohibits-collecting-data-for-ai-use/)
- Telegram bot developer terms: developers must not collect, store, aggregate or process data beyond what is essential for operating their service; always-prohibited uses include data collection aimed at creating datasets, ML models and AI products — [Telegram Bot Platform Developer ToS](https://telegram.org/tos/bot-developers) (relevant because the app also runs a bot)
- GDPR household exemption (Art. 2(2)(c)) must be interpreted narrowly and applies only to purely personal/household activity; CJEU Ryneš (C-212/13) and Lindqvist (C-101/01) — [GDPRhub: Article 2 GDPR](https://gdprhub.eu/Article_2_GDPR); [Handley Gill on Recital 18](https://www.handleygill.co.uk/handley-gill-blog/data-protection-personal-data-recital-18-article-2-material-scope-uk-gdpr-purely-personal-household-activity-domestic-purposes-exemption)
- GDPR Recital 18 states the Regulation does not apply to purely personal/household processing by a natural person, "However, this Regulation applies to controllers or processors which provide the means for processing personal data for such personal or household activities." — [GDPR Recital 18](https://gdpr-info.eu/recitals/no-18/) (quoted from the regulation text; page fetch was blocked in this session — verify wording)
- "Privacy externalities": one person's consent cannot cover data about others contained in their communications — [Internet Policy Review: Privacy self-management and the issue of privacy externalities](https://policyreview.info/articles/analysis/privacy-self-management-and-issue-privacy-externalities-thwarted-expectations-and)
- Anthropic commercial API (secondary sources, primary privacy.claude.com blocked): inputs/outputs deleted within 30 days by default; Commercial Terms state Anthropic may not train models on Customer Content; zero data retention (ZDR) available to eligible customers by agreement; safety-flagged content and classifier results may be retained longer (reported up to 2 years) — [getvoibe: Claude API data retention](https://www.getvoibe.com/resources/claude-api-data-retention/); [witness.ai 2026](https://witness.ai/blog/ai-data-retention/)
- Since June 2026, Anthropic's "Covered Models" (Fable 5/5.1, Mythos 5/5.1) reportedly carry a mandatory 30-day retention that overrides ZDR — [digitalapplied.com](https://www.digitalapplied.com/blog/fable-5-30-day-data-retention-zdr-enterprise-2026); [Axios, 2026-08-19](https://www.axios.com/2026/08/19/openai-previews-zero-retention-safety-system-as-anthropic-requires-data-logs) — implication: use Haiku/Sonnet-class models if ZDR matters (verify with Anthropic)
- Anthropic offers US-only inference geography at 1.1x price (no EU-only option listed on the pricing page) — [Anthropic pricing docs](https://platform.claude.com/docs/en/about-claude/pricing)

### Inferences
- Roles: the user is likely household-exempt for reading their own chats, but the Wrapped service (and its LLM vendor as processor) is a controller/processor under Recital 18. It needs a lawful basis for processing contacts' data (consent is impossible to obtain; legitimate interest with strict minimisation is the plausible basis), a privacy notice, a DPA (Art. 28) with the LLM provider, and a transfer mechanism for EU->US transfers. This is legal analysis to confirm with counsel, not established fact.
- Sentiment/mood and personality inferences may reveal health or other special-category data (Art. 9) — another reason to keep them aggregate, user-only, and not stored longer than RESULT_TTL.
- Telegram's AI clause covers "deployment" of AI on platform data, which on a plain reading could include running *any* ML (even the on-device classifiers and the existing ML module) over chats obtained via the API, not only third-party LLMs. The exception requires consent of "all relevant users" per chat, which the contacts cannot give. Treat this as the single biggest legal risk; get a legal read and consider asking Telegram. Deterministic counting statistics (message counts, hours, streaks) are least exposed.
- Minimisation patterns, in order of preference:
  1. Deterministic stats and phrase extraction (already in the app) — no ML model needed.
  2. On-device ML (browser) where text never leaves the user's device; server never persists text (already deletes the session after the pipeline).
  3. If an LLM is used: explicit, separate opt-in screen ("send X anonymised snippets to <vendor> to name your topics"); send only cluster keywords, candidate phrases the user's own LLR step produced, aggregate numbers, and a few redacted lines **authored by the user** (exclude contacts' messages where possible).
  4. Redact before sending: names (replace with "Friend A"), phone numbers, emails, URLs, @usernames, numbers/addresses; strip chat titles; per-friend summaries built from aggregate stats rather than their messages.
  5. Contract: commercial API terms (no training), DPA, ZDR if obtainable, avoid models with mandatory retention, choose region where possible; log nothing.
- Avoid "fun" features that profile contacts (personality or age of a friend), which multiplies third-party-data exposure for minimal product value.

### Gaps
- Could not fetch the verbatim Telegram API ToS (core.telegram.org blocked); section numbers, effective date and exact wording of the AI clause need to be checked directly by the team.
- No EDPB/ICO guidance specifically on apps that analyse a user's private message history including third parties was located in this session (EDPB Opinion 28/2024 on AI models and ICO legitimate-interest guidance would be the next sources to read).
- Anthropic retention/ZDR details are from secondary sources; confirm on privacy.claude.com and in the Commercial Terms / DPA.
