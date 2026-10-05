# Phrase and Inside-Joke Extraction from Informal Chat (Telegram Wrapped)

Context: how the current code works. These are observations from reading `backend/app/text_analysis.py` and `backend/app/stats.py` in this repo, not web sources.
- `_process_text_batch` builds 2–5-grams over *all* of the user's sent texts pooled together, after deleting punctuation and dropping 1-character tokens and digits. Scoring is `min pairwise bigram LLR × log2(1 + user_freq/bg_freq) × (1 + 0.3·(n−2)) × log2(1+count)`, and the background is an English-only bigram list.
- **Ordering bug.** Candidates are sorted `(-len(words), -score)` and accepted until 15 are reached. Every passing 5-gram is therefore considered before any 4-, 3- or 2-gram. The 15 slots fill with long fragments (often overlapping windows of one copy-pasted message), and the length bonus and dedup make this worse. This alone probably explains much of the "nonsensical" output.
- **Distinctiveness is broken for longer phrases.** The background has bigrams only, so every 3–5-gram gets `bg_freq=0`, which gives maximal "distinctiveness". The code comment admits this. Non-English bigrams are also always "distinctive".
- **Forwards and bots are not filtered.** `stats.py:215` passes `r.message` for every record. `ActivityRecord.forward` exists but is not used for filtering, so forwarded texts are treated as the user's own words. Code blocks, bot commands and quoted text are not removed either.
- **Subsampling hides rare items.** Texts are capped at 25,000 by random subsample (`MAX_TEXTS_FOR_ANALYSIS`). This keeps the head of the distribution but makes rarer per-chat inside jokes statistically invisible.
- **No per-chat contrast.** Records carry `dialog`, but phrase scoring pools all chats, so inside jokes cannot be found. The pipeline fetches only the user's own messages (`from_id=self`). Friends' text is not available (HistoryMsg stores only date/out), so "you vs. friend" contrast is currently impossible without extra fetching.
- **Emoji counting is per codepoint.** `EMOJI_RE` matches single codepoints in a few ranges. ZWJ families, skin-toned emoji and flags get split, and ranges such as ❤ U+2764 are only partly covered.

## 1. How do classic collocation/keyphrase methods (PMI, LLR, t-score, YAKE, RAKE, TextRank, KeyBERT, KeyLLM, PatternRank) perform on short informal chat? Failure modes?

### Takeaway
Collocation measures answer "do these words co-occur more than chance?", which is not the same question as "is this phrase characteristic of this person?". Each measure has a known frequency bias: PMI favours rare pairs, t-score favours frequent ones, and LLR sits in between. Single-document keyphrase extractors (YAKE, RAKE, TextRank, KeyBERT) are built to find a document's *topic*, so they surface nouns and topics, not catchphrases, and they degrade on short, noisy text. They suit "what did you talk about" slides, not "signature phrases".

### Cited Findings
- PMI favours low-frequency collocations and t-score favours high-frequency ones. In one evaluation, log-likelihood (G² = 56.8%) and t-score (52.5%) gave the best results. — [LADAL collocations tutorial](https://ladal.edu.au/tutorials/collocations/collocations.html); [Evert, Corpora and collocations](https://lexically.net/downloads/corpus_linguistics/Evert2008.pdf)
- "Effect-size" measures such as PMI and Dice measure association strength but generally fail to account for sampling variation. Significance measures (LLR, t-score) are proposed as alternatives. — [LADAL](https://ladal.edu.au/tutorials/collocations/collocations.html); see also [Evert et al. 2017 large-scale evaluation](https://purl.org/stefan.evert/PUB/EvertUhrigEtc2017.pdf) and [Pecina-style re-examination of association measures (Kan et al., MWE'09)](https://www.comp.nus.edu.sg/~kanmy/papers/mwe09a.pdf)
- Normalized PMI (Bouma) bounds PMI to [−1, 1], which reduces the rare-pair bias. gensim implements it as `npmi_scorer` next to Mikolov's `original_scorer`: `(count(ab) − min_count) / (count(a)·count(b)) · |V|`. gensim's `Phrases` also accepts `connector_words` (e.g. `ENGLISH_CONNECTOR_WORDS`), so phrases such as "bank of america" may contain function words inside but cannot start or end with them. — [gensim phrases.py source](https://github.com/piskvorky/gensim/blob/develop/gensim/models/phrases.py)
- YAKE is an unsupervised, single-document, "language and domain independent" extractor that uses statistical features. It needs no corpus or dictionary and is configured with `n` (max n-gram), `dedupLim`, `dedupFunc` (`leve|jaro|seqm`) and `windowsSize`. — [YAKE README](https://github.com/LIAAD/yake)
- One comparison reports YAKE performing better than KeyBERT on a Twitter dataset and KeyBERT better on a different (Mohler) dataset. KeyBERT is noted as "limited in capturing the full context of the text due to the short nature of the sentences". In another task KeyBERT was slightly more accurate (F1 73.3% vs 71.1%) but took 360 s vs 13 s. — [Evaluation of Keyword Extraction using YAKE and KeyBERT (ResearchGate)](https://www.researchgate.net/publication/394789438_Evaluation_of_Keyword_Extraction_using_YAKE_and_KeyBERT_in_Text_Preprocessing_for_Hoax_News_Detection_Based_on_Bi-LSTM); [journal version](https://jurnal.usk.ac.id/riwayat/article/view/48626/24657)
- "Keyphrase extraction from tweets is a non-trivial task due to the tweets' informal nature, noisiness and short length, which limits the utility of many existing unsupervised keyword extraction techniques designed to work on longer text." — [Keyphrase Extraction from Disaster-related Tweets (arXiv 1910.07897)](https://arxiv.org/pdf/1910.07897)
- Social-media discourse work uses theme-driven keyphrase extraction because generic extractors miss the themes analysts care about. — [Theme-driven Keyphrase Extraction to Analyze Social Media Discourse (arXiv 2301.11508)](https://arxiv.org/pdf/2301.11508)
- Scattertext (Kessler) can use PyTextRank phrases as features and then rank them by category association. This is a "candidate generator + contrastive scorer" design. — [scattertext README](https://github.com/JasonKessler/scattertext)

### Inferences
- **Why LLR scores look "boring or nonsensical" in chat:**
  - LLR rewards *fixed* bigrams, which are mostly generic: "of course", "right now", "let me know", "good morning", "new york", plus names ("anna said").
  - LLR does not reward "this person says it unusually often". A person's catchphrase built from common words ("i mean", "no way") has low LLR because its parts are frequent.
  - Taking the minimum pairwise LLR across a 4–5-gram is fine as a coherence filter. As a ranking score it mixes up "sticky" with "characteristic".
- **Failure modes to expect in chat** (from the code review plus the sources above):
  - Stopword-only phrases ("i don't know if").
  - Fragments that cross clause boundaries, because punctuation is deleted before n-gramming, so "ok. see you" becomes "ok see you".
  - URL remnants and domain tokens.
  - Names, @mentions and addresses.
  - Forwarded posts, bot output and copy-pasted templates (one long forwarded message generates dozens of passing 3–5-grams).
  - Repeated stretched laughter ("ахахахах", "jajaja", "hahahah") that is never normalized.
  - Numbers and codes.
- **Recommendation:** use collocation statistics (NPMI or LLR) only as a *coherence filter* for whether a multiword candidate is a unit. Rank with frequency + dispersion + contrast (section 2).
- YAKE, RAKE, TextRank, KeyBERT and PatternRank are topic extractors. They are reasonable for a "topics of the year" slide but are the wrong tool for catchphrases. KeyBERT also needs a sentence-embedding model (~100–400 MB, GPU or slow CPU) per user run, which costs too much for a signature-phrase slide.

### Gaps
- I found no published benchmark that evaluates these extractors on *private chat* (WhatsApp/Telegram) for "catchphrase" quality. Evidence comes from tweets and news, not 1:1 chat. arxiv.org and aclanthology.org were blocked by the egress proxy, so paper details come from search snippets only.
- PatternRank: no primary source retrieved. It is a KeyBERT + POS-pattern (KeyphraseVectorizers) variant and is topic-oriented like KeyBERT.

## 2. Distinctiveness/contrast methods: Fightin' Words, scaled F-score, TF-IDF across chats — for (1) user vs general language, (2) inside jokes (one chat vs the user's other chats), (3) user vs friends

### Takeaway
The right core is a **weighted log-odds ratio with an informative Dirichlet prior** (Monroe, Colaresi & Quinn 2008, "Fightin' Words"), computed as a z-score. It shrinks noisy rare terms toward zero and gives the same machinery for all three contrasts:
- you vs. a background corpus;
- one chat vs. your other chats (inside jokes);
- you vs. a friend (needs their text).

Scaled F-score is a good alternative that is robust and frequency-aware. Plain TF-IDF across chats is the simplest version of the per-chat contrast, but it over-rewards one-off rare strings unless support thresholds are added.

### Cited Findings
- Fightin' Words (Monroe, Colaresi, Quinn 2008, *Political Analysis*) is a log-odds ratio with a Dirichlet prior for finding the words that separate two corpora. It addresses overfitting in the plain log-odds ratio by "incorporating prior knowledge from a larger dataset". — [Fightin' Words paper (ResearchGate)](https://www.researchgate.net/publication/228277150_Fightin'_Words_Lexical_Feature_Selection_and_Evaluation_for_Identifying_the_Content_of_Political_Conflict)
- With an informative prior, "each word's prior is its background count plus alpha … Words that are common in the background get a large prior and are shrunk hard toward zero". The output is a per-word z-score: positive means characteristic of corpus 1, near zero means not distinguishing. Defaults are `alpha=0.01` and an optional `min_count`. — [logodds (dependency-free Python implementation, adapted from Jack Hessel's)](https://github.com/juliamendelsohn/logodds)
- The statistic is variance-adjusted, so "a rare term cannot outrank a frequent one at the same rate ratio". — search summary of [m-sean/log-odds](https://github.com/m-sean/log-odds) / [logodds](https://github.com/juliamendelsohn/logodds)
- Formula, standard form from the paper:
  - δ_w = log[(y_w^i + α_w)/(n^i + α_0 − y_w^i − α_w)] − log[(y_w^j + α_w)/(n^j + α_0 − y_w^j − α_w)]
  - σ²(δ_w) ≈ 1/(y_w^i + α_w) + 1/(y_w^j + α_w)
  - rank by z = δ_w / σ
  - — [Monroe et al. 2008](https://www.researchgate.net/publication/228277150_Fightin'_Words_Lexical_Feature_Selection_and_Evaluation_for_Identifying_the_Content_of_Political_Conflict)
- Practical showcases include Obama's favoured and disfavoured SOTU words, LOTR vs. Dickens word frequencies, and the uniqueness of presidential discourse. — [Language Log SOTU](https://languagelog.ldc.upenn.edu/nll/?p=10073); [Language Log LOTR vs Dickens](https://languagelog.ldc.upenn.edu/nll/?p=73293); [arXiv 2401.01405](https://arxiv.org/pdf/2401.01405)
- **Scaled F-score** (Kessler, scattertext):
  - It takes the harmonic mean of a term's *precision* (share of its occurrences in the target category) and its *frequency share* within the category.
  - The raw harmonic mean is dominated by very frequent words with average precision, so both components are first transformed by the normal CDF: `normcdf(x) = norm.cdf(x, x.mean(), x.std())`. Then `hmean([precision_normcdf, freq_pct_normcdf])` is taken.
  - Positive and negative versions are combined as `2·(score − 0.5)`.
  - `get_scaled_f_scores_vs_background()` compares a corpus to a general-language background.
  - — [scattertext README, "Understanding Scaled F-Score"](https://github.com/JasonKessler/scattertext)
- Scattertext also includes the log-odds ratio with uninformative and informative Dirichlet priors (Monroe 2008) as term scorers. — [scattertext README](https://github.com/JasonKessler/scattertext)
- Idiolect research: word n-grams can attribute anonymised Enron emails to a case-study author with success rates "as high as 100%" (176 authors, 2.5M words). Distinctive n-gram "textbites" approximate idiolect. — [Wright 2017, Using word n-grams to identify authors and idiolects (Semantic Scholar)](https://www.semanticscholar.org/paper/Using-word-n-grams-to-identify-authors-and-a-corpus-Wright/802c27f566f183f0a37c79084f48de77d44cf4cd); [Wright 2013 textbite approach](https://www.researchgate.net/publication/299134045_Identifying_idiolect_in_forensic_authorship_attribution_an_n-gram_textbite_approach)
- Idiolect work also finds that author differences often come from the *combination of many common grammatical constructions* rather than a few noticeably idiosyncratic phrases. — search summary citing [Wright 2017](https://www.jbe-platform.com/content/journals/10.1075/ijcl.22.2.03wri) and [Idiosyncratic but not Arbitrary (arXiv 2109.03158)](https://arxiv.org/pdf/2109.03158)

### Inferences
**(1) User vs. general language ("signature phrases").** Use Fightin' Words z-scores with an informative prior from a *chat-register, per-language* background. Do not use Google Books / news bigrams: against a formal background, every chat-ism ("lol", "gonna", "ахах") looks distinctive. Background options, cheapest first:
- **(a) Best fit for this product: aggregate n-gram counts across all users** of Telegram Wrapped, per language. Store only counts of n-grams that appear for ≥ k distinct users (k ≥ 20–50), which gives k-anonymity. These are exactly the "everyone says this" phrases to dampen.
- **(b) Open chat-like corpora** such as OpenSubtitles or Reddit/Twitter n-gram counts per language, pruned to the top ~200k n-grams per language (a few MB of JSON each).
- **(c) Short term:** frequency-only ranking plus a curated "generic phrase" blocklist per language.

**(2) Inside jokes** (phrase distinctive to chat c vs. the user's other chats). Run log-odds with prior = the user's own total counts across all chats (the "informative prior" is the user's global usage), target = chat c, rest = other chats. Also require:
- support in chat c ≥ 3 occurrences on ≥ 2–3 distinct days (dispersion; see section 5);
- ≥ 60–70% of the user's total uses of the phrase in that one chat (precision, as in the scaled F-score);
- not a name or @mention of that chat's partner (otherwise the top "inside joke" with Anna is "anna").

This works on the user's own messages only, which the pipeline already fetches per dialog. Inside jokes are mostly *shared* vocabulary, so the user's side alone usually shows them.

**(3) User vs. friend.** This needs the friend's text, which the pipeline does not collect today. If both sides are fetched for the top N private chats, the same log-odds gives "you say X, they say Y" comparisons. A phrase used by *both* sides heavily and almost nowhere else (high count on both sides, low elsewhere) is the strongest inside-joke signal.

**TF-IDF across chats** (each chat = document) is a fast first approximation. Use sublinear tf and idf over the user's chats. It has no variance control, so it needs the same support thresholds.

### Gaps
- No primary-source evaluation was found comparing Fightin' Words vs. scaled F-score vs. TF-IDF specifically for *catchphrases* or *inside jokes*. The recommendation is an inference from method properties.
- No open, chat-register background n-gram corpus per language was found during this search.

## 3. Using LLMs to curate, rank and label candidate phrases; evidence on quality; prompt design; avoiding hallucinated phrases

### Takeaway
Zero-shot LLM keyphrase extraction beats classic *unsupervised* extractors on benchmark F1 but is not perfect, and LLMs will "create" phrases that are not in the text unless constrained. The robust pattern is **statistics propose, LLM disposes**:
1. Extract verified candidates with counts and example contexts.
2. Ask the LLM only to choose, group and label from that list.
3. Validate the LLM output programmatically against the candidate IDs.

Consumer "Wrapped for chats" products already use LLMs (Claude) for quotes and inside jokes.

### Cited Findings
- Under zero-shot settings ChatGPT "outperforms all other unsupervised keyphrase extraction methods" in F1@5 and F1@M but is "still inferior to existing SOTA supervised models on almost all datasets". — [Large Language Models as Zero-Shot Keyphrase Extractors (arXiv 2312.15156)](https://arxiv.org/pdf/2312.15156)
- An empirical study compared vanilla, role, candidate-based and hybrid prompting. Llama3-8B-Instruct with vanilla prompting beat SOTA unsupervised methods by +9.43 / +7.68 / +4.82 F1@5/10/15 on average. — [Empirical Study of Zero-shot Keyphrase Extraction with LLMs, COLING 2025](https://aclanthology.org/2025.coling-main.248/) (via search snippet; page blocked)
- Specialized instructions and multi-sample aggregation (sampling several times and aggregating) improve zero-shot keyphrase generation. — [Zero-Shot Keyphrase Generation (NAACL Findings 2025, arXiv 2503.00597)](https://arxiv.org/html/2503.00597)
- KeyBERT's KeyLLM has three modes:
  - **Create:** the LLM invents keywords that "do not necessarily need to appear in the input documents".
  - **Extract:** the prompt says "Make sure to only extract keywords that appear in the text", combined with `check_vocab=True`, which drops any keyword not found in the document.
  - **Fine-tune candidates:** a `[CANDIDATES]` placeholder passes pre-extracted candidates, with the prompt "Based on the information above, improve the candidate keywords…".
  - KeyLLM can also be combined with KeyBERT embeddings to cluster similar documents and call the LLM once per cluster, saving calls.
  - — [KeyLLM guide (KeyBERT docs source)](https://github.com/MaartenGr/KeyBERT/blob/master/docs/guides/keyllm.md)
- LLM humour understanding is still limited. A 2025 dataset and analysis finds gaps in LLM comprehension of unpredictable, context-dependent humour. — [Comparing Apples to Oranges: LLM Humour Understanding (EMNLP Findings 2025)](https://aclanthology.org/2025.findings-emnlp.505.pdf) (title and abstract only via search)
- Consumer precedents:
  - "Text Unwrapped" analyses WhatsApp chats with Anthropic's Claude API across multiple prompts.
  - Claude Code–based "iMessage Wrapped" writes per-contact summaries with direct quotes and inside jokes.
  - WhatsApp Wrapped / WhatsWrapped apps advertise "inside jokes" via AI.
  - — [Show HN: 2025 Wrapped for WhatsApp](https://news.ycombinator.com/item?id=46428595); [Jake Spurlock, I Built My Own iMessage Wrapped](https://jakespurlock.com/2026/02/i-built-my-own-imessage-wrapped-and-so-can-you/); [threadrecap WhatsApp Wrapped](https://www.threadrecap.com/en/whatsapp-wrapped); [WhatsWrapped AI (App Store)](https://apps.apple.com/np/app/whatswrapped-ai-chat-analyzer/id6744784832) (details from search snippets; pages blocked)

### Inferences
**Recommended LLM stage (optional, behind a feature flag and consent, because message text leaves the server):**
- **Input:** about 60–120 candidates in total:
  - top 40 signature candidates by z-score;
  - top 5–8 per top-8 chat for inside jokes;
  - top whole-message catchphrases.
  Each candidate is `{id, phrase, count, distinct_days, n_chats, top_chat_share, z, 2–3 short anonymised example messages ≤ 120 chars}`. Replace names and handles with placeholders before sending.
- **Prompt:** "From the candidates below, pick up to 5 signature phrases and up to 3 inside jokes per chat that a friend would instantly recognise as this person's way of talking. Prefer quirky, specific, funny phrases. Reject generic phrases (e.g. 'see you tomorrow'), names, logistics, URLs/addresses, and anything sensitive (health, sexual, financial, self-harm). Return JSON `[{id, title (≤6 words, playful), why (≤15 words)}]`. Use ONLY ids from the list. Do not rewrite phrases."
- **Validation:** discard unknown ids. Display the phrase *from our candidate table* (exact original casing and the count from our stats), never the LLM's echo. Only `title` and `why` come from the LLM. This removes phrase hallucination by construction, the same idea as KeyLLM's `check_vocab`.
- **Cost:** about 3–6k input tokens and ~500 output tokens per user, one call. A small or fast model is adequate because it is a selection task. The deterministic ranking must remain a complete fallback.
- **Self-consistency:** optionally sample 2–3 times and keep items chosen at least twice (the multi-sample aggregation idea in arXiv 2503.00597). This reduces arbitrary picks.

### Gaps
- No quantitative evaluation was found of LLM *curation of chat catchphrases* (as opposed to document keyphrases), or of "funniness" judgements on private chat. Quality claims for consumer Wrapped apps are marketing, not evaluated.
- Privacy and regulatory considerations of sending private messages to an LLM API are out of scope here but material.

## 4. Multilingual and code-mixed chat: tokenization, emoji handling, stopwords per language, language identification on short texts

### Takeaway
Do not run a heavy NLP pipeline per message. The practical stack is:
- Unicode-aware regex tokenization (Python `regex` with `\X` / `\p{L}` classes);
- casefold plus elongation normalization;
- per-message language ID with a short-text-capable detector (Lingua in low-accuracy mode, restricted to likely languages; or fastText lid.176 on longer messages);
- per-language stopword or connector lists (stopwords-iso);
- optional cheap lemmatization (simplemma) only for single-word stats, never for display.

Short-text language ID is unreliable, so assign language per *user* or per *chat* by majority vote, not per message.

### Cited Findings
- Lingua:
  - Most detectors "only work with quite lengthy text fragments. For very short text snippets such as Twitter messages, they do not provide adequate results". Lingua uses 1- to 5-gram character models plus rules.
  - Reported accuracy: about 74% on single words (average 9 chars), ~94% on word pairs (18 chars) and ~99.7% on sentences across 75 languages. These are the project's own benchmark figures.
  - Runtime: 3,000 texts × 75 languages took 11.81 s in low-accuracy mode vs 21.13 s in high-accuracy mode, multi-threaded (CLD2 8.65 s, CLD3 16.77 s, langdetect 10 min 44 s). Memory is "only a few dozen megabytes" (Rust backend).
  - Restricting to a subset of languages improves accuracy. `detect_multiple_languages_of` exists for mixed-language text but is "experimental" and works best with long words.
  - — [lingua-py README](https://github.com/pemistahl/lingua-py)
- fastText lid.176: one comparison rates it "good general accuracy, low accuracy on short text" and CLD3 "medium / low on short text". On WiLI, lid.176.bin scored 86.55%, .ftz 83.05%, and CLD3 74.74%. On Tatoeba, fastText scored 98.27% vs gcld3 87.11%. — [modelpredict language-identification survey](https://modelpredict.com/language-identification-survey); [fastText R package benchmark](https://mlampros.github.io/2021/05/14/fasttext_language_identification/)
- For texts under 70 characters, LSTM and fastText models had the highest accuracy in one short-message study, and models converged above 70 chars. — [Language Identification for very short texts: a review (Besedo)](https://medium.com/besedo-engineering/language-identification-for-very-short-texts-a-review-c9f2756773ad). Note that this conflicts with the modelpredict rating of fastText as weak on short text, so evidence is mixed.
- Closely related languages remain hard even for modern LID. OpenLID-v3 focuses on that precision problem. — [OpenLID-v3 (arXiv 2602.13139)](https://arxiv.org/pdf/2602.13139); [FastSpell (arXiv 2404.08345)](https://arxiv.org/pdf/2404.08345)
- stopwords-iso is "the most comprehensive collection of stopwords for multiple languages", keyed by ISO 639-1 code, with a single JSON file and the `stopwordsiso` pip package. — [stopwords-iso](https://github.com/stopwords-iso/stopwords-iso)
- simplemma is a dependency-free lemmatizer for 54 languages: a 19 MB install, 0.91–0.97 accuracy for 34 languages, with language chaining such as `lang=('de','en')` for mixed text. — [simplemma README](https://github.com/adbar/simplemma)
- The emoji library supports emoji names in 13 languages including Russian and Spanish (`demojize`). — [emoji README](https://github.com/carpedm20/emoji)

### Inferences
- **Tokenizer recipe:**
  - `regex.findall(r"\X", s)`-aware splitting.
  - Words are `[\p{L}\p{M}\p{N}'’_-]+`, with letters of any script.
  - Emoji graphemes are separate tokens.
  - Keep punctuation as **boundary markers**: never form an n-gram across `.,!?;:\n` or across messages.
- **Normalization:**
  - casefold;
  - `ё→е` for Russian;
  - strip diacritics only for *matching*, never for display;
  - collapse character elongations (`(.)\1{2,}` → `\1\1`) so "sooo/soooooo" merge;
  - canonicalize laughter families (`[ах]{4,}`, `(ha){2,}`, `(ja){2,}`, `(kk){2,}`, `(хах)+`, `lo+l`, `ахах+`) into one "laugh:<lang>" token. Laughter is a fun stat on its own ("you laughed 'ахахах' 3,214 times") but is a top-phrase polluter.
- **Language assignment:** detect on messages ≥ 20 chars only, then majority vote per chat and per user. Use the per-user language mix to choose stopword/connector lists and the background prior. Lingua low-accuracy mode restricted to the ~10–15 most likely languages handles ~100k+ messages in seconds to tens of seconds (scaling from the README timing; an estimate).
- **Transliteration:** Russian written in Latin letters ("privet", "kak dela") will not match the Cyrillic stopwords or background. A cheap mitigation is to add translit variants of the top ~200 Russian stopwords to the stopword set.
- **Do not use the stopword list to filter *display* phrases outright.** Instead apply the gensim connector-word rule: no phrase may start or end with a stopword or connector, but stopwords inside are fine ("piece of cake", "ну и что").
- **spaCy/stanza:** multilingual pipelines are heavy (hundreds of MB per language; stanza is slow on CPU) and buy little for catchphrases. Not recommended in the per-user hot path.

### Gaps
- No head-to-head benchmark was found on *chat* messages (as opposed to tweets, sentences or Wikipedia) comparing Lingua, fastText and CLD3. Lingua's numbers are self-reported.
- No reliable source was found on automatic transliteration detection for Russian/Ukrainian in chat.

## 5. Pre-processing that matters: forwarded messages, links, code, bot commands, quoted replies, auto-generated text, copy-paste dedup, minimum distinct-days / distinct-chats support

### Takeaway
Most "nonsense phrase" output comes from text the user did not compose: forwards, bot output, pasted templates and links, plus a single spammed message dominating counts. Telegram gives structured signals to drop these: `fwd_from`, `via_bot_id`, and entities for URL, code, pre, bot command and blockquote. Ranking by **dispersion** (distinct days, distinct messages) instead of raw count is the single best guard against one spammed message.

### Cited Findings
- Telegram's MTProto schema defines `messageEntityUrl`, `messageEntityTextUrl`, `messageEntityCode`, `messageEntityPre` (with language), `messageEntityBotCommand` and `messageEntityBlockquote` (with `collapsed`). The `message` constructor carries `fwd_from`, `via_bot_id`, `reply_to` and related fields. — [Telethon api.tl schema](https://github.com/LonamiWebs/Telethon/blob/v1/telethon_generator/data/api.tl)
- This repo already detects URL entities (`fetcher._has_link`) and sets `ActivityRecord.forward = fwd_from is not None` (`backend/app/fetcher.py`), but `stats.py` feeds all texts, forwards included, into phrase extraction. (Repo observation.)
- Corpus linguistics stresses dispersion/range alongside frequency for lexical bundles. Evert's collocation tutorial notes the effect of frequency thresholds and sampling variation on association scores. — [Evert, Corpora and collocations](https://lexically.net/downloads/corpus_linguistics/Evert2008.pdf)
- gensim `Phrases` uses `min_count` and `threshold` to prune candidates before scoring. — [gensim phrases.py](https://github.com/piskvorky/gensim/blob/develop/gensim/models/phrases.py)
- The Omar Files (a WhatsApp group-chat analyzer covering 300k+ messages) reports "most repeated words and phrases" and "running jokes". It needed identity resolution (alias table) and deduplication on merge, which shows the same dedup and identity concerns. — [The Omar Files README](https://github.com/Akif-b-Atif/The-Omar-Files)

### Inferences
**Concrete filters, in order:**
1. Drop messages with `fwd_from`, `via_bot_id` or `post`, and those whose `media` is a game, poll or invoice.
2. Drop messages that start with `/` (bot commands) or that contain `messageEntityPre` or `messageEntityCode` spans covering > 30% of the text.
3. Cut out (do not drop the whole message for) these spans: URLs and TextUrl spans, emails, phone numbers, @mentions, hashtags (keep as a separate stat), numbers with ≥ 3 digits, long hex/base64-like tokens, and `messageEntityBlockquote` spans (quoted text).
4. **Copy-paste and template dedup.** Hash the normalized message, then:
   - count a given long message (> 8 tokens) at most once per day per chat;
   - drop messages > 300 chars with ≥ 3 identical copies across chats (chain letters and invites);
   - optionally use MinHash/SimHash on 5-shingles for near-duplicates.
5. **Language-agnostic "machine text" heuristics:** a message where > 50% of tokens are non-letters; lines that look like `Key: value` lists; very long messages (> 1,000 chars) are excluded from the *phrase* stage (still counted for totals).

**Support thresholds (dispersion).** A phrase is eligible only if all of these hold:
- count ≥ max(5, 0.0005 × #user messages) for signature phrases;
- **distinct days ≥ 3** (better: ≥ 5 for signature phrases);
- **distinct messages ≥ 4**;
- it is not > 50% attributable to a single day.

For inside jokes: ≥ 3 uses on ≥ 3 distinct days in that chat. Rank by a dispersion-weighted count (e.g. `count × min(1, days/10)`) inside the statistical score.

**Do not subsample** to 25k random texts for phrases. Instead stream all eligible texts through a bounded counter (see section 7). Random subsampling destroys exactly the mid-frequency, per-chat phrases that make inside jokes.

### Gaps
- No published study quantifying how much forwards or bots degrade chat phrase extraction was found. The recommendations are engineering inference plus the code review.

## 6. Emoji and sticker analysis best practices (sequences, skin tones, ZWJ, grapheme segmentation)

### Takeaway
Count emoji as **grapheme clusters** (UAX #29) and not as codepoints, using the `regex` module's `\X` or the `emoji` library's tokenizer. Then normalize: strip skin-tone modifiers for the "top emoji" ranking (and report tone separately if desired), strip VS16 (U+FE0F), and keep ZWJ sequences and flags whole. Treat repeated runs (😂😂😂) both as one "use" and as a run-length stat.

### Cited Findings
- UAX #29 defines grapheme cluster boundaries, including rules for regional-indicator pairing (flags) and emoji ZWJ sequences (GB11). — [UAX #29 Unicode Text Segmentation](http://www.unicode.org/reports/tr29/)
- In Python, `\X` matches a full extended grapheme cluster (combining marks, ZWJ sequences, regional indicators), but only in the third-party `regex` module, not `re`. The family emoji 👨‍👩‍👧‍👦 is seven codepoints joined by ZWJ yet one grapheme, and `len()` counts codepoints. — [SymbolFYI grapheme clusters guide](https://symbolfyi.com/guides/grapheme-clusters-explained/); [SymbolFYI Unicode regex guide](https://symbolfyi.com/guides/unicode-regex-guide/)
- Skin tones are Fitzpatrick modifiers U+1F3FB–U+1F3FF that combine with a base emoji. ZWJ sequences expand the repertoire without new codepoints. — [Emoji ZWJ Sequence glossary](https://unicodefyi.com/glossary/emoji-zwj-sequence/)
- The `emoji` Python library provides:
  - `emoji_list`, `distinct_emoji_list`, `emoji_count(unique=…)`, `purely_emoji`;
  - `analyze(string, join_emoji=True)`, which merges emoji separated only by ZWJ into a single `EmojiMatchZWJNonRGI` token, so non-RGI (not "recommended for general interchange") ZWJ combos are kept;
  - `demojize` for names in 13 languages.
  - — [emoji core.py](https://github.com/carpedm20/emoji/blob/master/emoji/core.py); [emoji README](https://github.com/carpedm20/emoji)

### Inferences
- **Recipe:**
  - `for g in regex.findall(r'\X', text): if emoji.is_emoji(g) or emoji.purely_emoji(g): …`
  - Normalize `g` by removing U+FE0F and U+1F3FB–1F3FF for the base-emoji ranking, and keep a separate counter of skin tone used.
  - Count per message *presence* (an emoji appearing anywhere in a message counts once) for the "top emoji" list, and total occurrences for a "spam" stat. This stops 😂×20 messages dominating.
- **Emoji sequences as phrases:** feed emoji graphemes into the same n-gram and contrast machinery (treat each emoji as a token, collapse runs of the same emoji to one). This surfaces "🙏🏻❤️"-style signatures and per-chat emoji inside jokes (e.g. 🦆 only with one friend). Fightin' Words over emoji per chat is a cheap "your emoji with X" slide.
- **Stickers:** count by `sticker_id` (document id), group by sticker set for "favourite pack", and use `sticker_emoji` (the alt emoji, already in `ActivityRecord`) to merge stickers into the emoji-sentiment view. Per-chat sticker contrast gives sticker inside jokes.
- **Emoji-only messages** (`emoji.purely_emoji`) are good "whole-message catchphrases" in their own right (e.g. "👀").

### Gaps
- No academic best-practice paper on emoji counting for user-facing stats was found. The guidance comes from the Unicode standard plus library docs.

## 7. Concrete recommended pipeline with parameters, and examples of projects that did this well

### Takeaway
Replace the "LLR × English background × length bonus" ranker with a three-track pipeline:
- **(A) whole-message catchphrases** (short messages repeated verbatim; the most recognisable chat signatures);
- **(B) in-message n-gram phrases** with boundary-aware, connector-rule candidates ranked by dispersion-weighted frequency × log-odds distinctiveness against a chat-register background;
- **(C) per-chat inside jokes** via log-odds of chat vs. the user's other chats with dispersion and precision thresholds.

Then optionally (D) have an LLM select and label from verified candidates. Everything except D is pure counting and runs in seconds on 500k messages with bounded memory.

### Cited Findings
- Fightin' Words z-scores with informative prior, and the scaled F-score, as above. — [logodds](https://github.com/juliamendelsohn/logodds); [scattertext](https://github.com/JasonKessler/scattertext)
- gensim-style phrase pruning (`min_count`, `threshold`, NPMI scorer, connector words). — [gensim phrases.py](https://github.com/piskvorky/gensim/blob/develop/gensim/models/phrases.py)
- The KeyLLM candidate-constrained prompt with `check_vocab`. — [KeyLLM guide](https://github.com/MaartenGr/KeyBERT/blob/master/docs/guides/keyllm.md)
- Typical open-source WhatsApp analyzers offer word clouds, "most common words" (frequency after stopword removal), emoji counts and per-user splits. None of the surveyed READMEs describe distinctiveness scoring. — [amitkedia007/Whatsapp-chat-analyzer](https://github.com/amitkedia007/Whatsapp-chat-analyzer); [pcsingh/WhatsApp-Chat-Analyzer](https://github.com/pcsingh/WhatsApp-Chat-Analyzer); [The Omar Files](https://github.com/Akif-b-Atif/The-Omar-Files)
- Commercial and hobby "Wrapped" tools increasingly delegate inside jokes and quotes to LLMs (Claude). — [threadrecap](https://www.threadrecap.com/en/whatsapp-wrapped); [Show HN WhatsApp Wrapped](https://news.ycombinator.com/item?id=46428595); [iMessage Wrapped blog](https://jakespurlock.com/2026/02/i-built-my-own-imessage-wrapped-and-so-can-you/)
- Fine-tuning an LLM on 240k personal text messages reproduced a person's texting style. This is evidence that personal chat style is strongly idiosyncratic and learnable. — [Edward Donner, fine-tuning an LLM on 240k text messages](https://edwarddonner.com/2024/01/02/fine-tuning-an-llm-on-240k-text-messages/)

### Inferences
**Recommended pipeline** (parameters are starting points to tune on real accounts with `scripts/live_check.py`):

**0. Filter** (section 5). Input: the user's own non-forward, non-bot, non-code messages, with URL, mention and quote spans cut out. Keep `(chat_id, day, text, weight)`.

**1. Normalize and tokenize.** Casefold, elongation collapse, laughter canonicalization, `\X`-aware tokens. Split into "segments" at sentence punctuation and newlines. Detect language per user and chat (Lingua low-accuracy, restricted languages, messages ≥ 20 chars).

**2. Track A: whole-message catchphrases.**
- Key = normalized full message, 1–6 tokens, or emoji-only.
- Eligible if count ≥ 5, distinct days ≥ 4, and not purely a stopword/greeting from a small per-language blocklist ("ok", "yes", "да", "ок", "thanks", "спасибо", "hi").
- Rank by `days × log(count)` × log-odds z vs. the background of all users' whole-message counts once available.
- This finds "ну такое", "sounds like a plan", "LMAOOO", "👀", "bro what", and is often the most recognisable output.

**3. Track B: in-segment n-grams (n = 1..4; 5-grams rarely add value).**
- Candidate rules:
  - must not start or end with a stopword/connector (gensim rule);
  - ≥ 1 content token;
  - no token that is a name in the user's contacts or dialog titles (strip the user's contacts' first names);
  - count ≥ max(5, 0.0005·N_msgs);
  - distinct days ≥ 3.
- Coherence for n ≥ 2: NPMI of the weakest adjacent split ≥ 0.2–0.3, or LLR ≥ 10.83 (p < 0.001) as a *filter* only.
- **Score** = `z_logodds(user vs background) × min(1, days/10)`. Rank top-K with *subsumption*: keep the longer phrase only if `count(long) ≥ 0.7 × count(short)` (otherwise the shorter one is the real phrase), and drop shorter phrases whose count is ≥ 80% explained by one longer phrase.
- **Fix the current ordering bug.** Sort by score, not by length first.

**4. Track C: inside jokes per chat** (top ~10 chats by message count).
- `z = logodds(chat c vs. user's other chats, prior = user's totals × scale)`.
- Thresholds: count in c ≥ 3, days in c ≥ 3, share of user's total uses in c ≥ 0.6, not the partner's name or nickname, not in the top 500 of the global background (too generic).
- Show 1–3 per chat with first-used date ("since March") and count. Optionally include the friend's side if both sides are fetched for those chats.

**5. Emoji/sticker** tracks (section 6) through the same per-chat contrast.

**6. (Optional) Track D: LLM curation** (section 3). The deterministic Tracks A–C are the fallback and the source of truth for phrase text and counts.

**Compute and memory** (estimates, not measured):
- 500k messages × ~8 tokens is about 4M tokens, and n = 1..4 gives ~16M n-gram increments.
- In pure Python with dict counters this is roughly 10–30 s and ~1–2 GB worst case for unique keys.
- Mitigations:
  - **two-pass pruning**: count unigrams and bigrams first, and only extend to 3- and 4-grams whose prefix bigram passed min_count (Apriori-style);
  - or hash n-grams to 64-bit ints in a `collections.Counter` / numpy `unique`;
  - per-chat counts only for n-grams that pass the global min_count.
- Log-odds and z-scores are vectorizable over the surviving ~10–50k candidates in milliseconds.
- The background prior is a static per-language JSON or msgpack of a few MB, loaded once per process.

**Quick wins on the existing code** (the smallest diff that should visibly improve output):
1. Exclude `r.forward` records and messages with code or bot entities from `weighted_texts` (`stats.py:215`).
2. Sort candidates by score instead of `(-len, -score)` in `_process_text_batch`, and cap n at 4.
3. Do not form n-grams across punctuation or newlines (split into segments before `PUNCT_RE` removal).
4. Add a distinct-days requirement. This needs the record date passed with each text.
5. Collapse elongations and laughter.
6. Use grapheme-aware emoji counting.
7. Drop the English-only background distinctiveness term until a chat-register, multilingual background exists. Until then, rank by dispersion-weighted frequency with the connector rule.

### Gaps
- I found no public project with a documented, evaluated recipe that produces *good* chat catchphrases or inside jokes. Open-source analyzers stop at frequency word clouds, and commercial ones use opaque LLM prompts.
- The parameter values above are engineering starting points, not values validated in literature. They should be tuned against a few real accounts.
- The egress proxy blocked arxiv.org, aclanthology.org, news.ycombinator.com, jakespurlock.com and maartengr.github.io. Claims from those sources rest on search-result snippets, and GitHub-hosted sources were read directly.
