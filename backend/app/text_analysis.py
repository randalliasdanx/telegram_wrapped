"""Text analysis: word, emoji and phrase extraction.

Phrases are ranked by LLR (log-likelihood ratio) x TF-IDF distinctiveness
against a background English bigram corpus x a length bonus.
"""
from __future__ import annotations

import math
import re
from collections import defaultdict
from pathlib import Path

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "to", "of", "in", "on", "for",
    "is", "it", "this", "that", "i", "you", "we", "he", "she", "they", "me",
    "my", "your", "our", "us", "am", "are", "was", "were", "be", "been",
    "do", "does", "did", "have", "has", "had", "will", "would", "could", "should",
    "can", "may", "might", "shall", "not", "no", "so", "at", "by", "with",
    "from", "up", "out", "about", "into", "than", "then", "just", "like",
    "also", "very", "really", "too", "here", "there", "when", "what", "how",
    "who", "which", "where", "why", "all", "each", "every", "both", "few",
    "more", "most", "other", "some", "such", "only", "own", "same", "than",
    "its", "his", "her", "their", "him", "them", "these", "those",
    "im", "dont", "cant", "wont", "didnt", "doesnt", "isnt", "wasnt",
    "ok", "okay", "ya", "yah", "yeah", "yep", "nah", "nope",
    "lol", "haha", "hahaha", "hahahaha", "hehe", "lmao", "omg", "idk",
    "got", "get", "go", "going", "went", "come", "came", "say", "said",
    "know", "think", "see", "want", "need", "make", "take", "give",
    "tell", "ask", "try", "let", "keep", "put", "still", "even",
    "one", "two", "de", "la", "el", "en", "que", "es", "un", "lo",
    "ah", "oh", "eh", "um", "uh", "hmm", "mm",
}

URL_RE = re.compile(r"https?://\S+|www\.\S+")
PUNCT_RE = re.compile(r"[^\w\s'-]")
SPACE_RE = re.compile(r"\s+")
EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "]",
    flags=re.UNICODE,
)



def _clean_text(text: str) -> str:
    lower = text.lower()
    lower = URL_RE.sub(" ", lower)
    lower = PUNCT_RE.sub(" ", lower)
    lower = SPACE_RE.sub(" ", lower).strip()
    return lower


def _clean_text_preserve_case(text: str) -> str:
    """Clean but preserve original casing for display purposes."""
    cleaned = URL_RE.sub(" ", text)
    cleaned = PUNCT_RE.sub(" ", cleaned)
    cleaned = SPACE_RE.sub(" ", cleaned).strip()
    return cleaned


def _extract_emojis(raw_text: str) -> list[str]:
    return EMOJI_RE.findall(raw_text)


_BG_BIGRAMS_PATH = Path(__file__).resolve().parent / "ml" / "models" / "background_bigrams.json"
_bg_cache: dict[str, int] | None = None
_bg_total_cache: float = 0.0


def _load_background_bigrams() -> tuple[dict[str, int], float]:
    global _bg_cache, _bg_total_cache
    if _bg_cache is None:
        try:
            import json as _json
            with open(_BG_BIGRAMS_PATH) as f:
                _bg_cache = _json.load(f)
            _bg_total_cache = float(sum(_bg_cache.values())) or 1.0
        except FileNotFoundError:
            _bg_cache = {}
            _bg_total_cache = 1.0
    return _bg_cache, _bg_total_cache


def _llr_score(k_ab: float, k_a: float, k_b: float, N: float) -> float:
    """Log-likelihood ratio for bigram (a, b).
    More robust than PMI for informal text (ACL research-backed)."""
    def _H(k: float, n: float) -> float:
        if k <= 0 or k >= n or n <= 0:
            return 0.0
        p = k / n
        return k * math.log(p) + (n - k) * math.log(1 - p)

    return 2.0 * (_H(k_ab, k_a) + _H(k_b - k_ab, N - k_a) - _H(k_b, N))


def _process_text_batch(texts: list[tuple[str, float]]) -> dict[str, defaultdict]:
    # Non-stopword counts (for final word display)
    display_words: defaultdict[str, float] = defaultdict(float)
    # ALL unigram counts including stopwords (for LLR probability calculation)
    all_unigrams: defaultdict[str, float] = defaultdict(float)
    ngram_counts: defaultdict[str, float] = defaultdict(float)
    emojis: defaultdict[str, float] = defaultdict(float)
    # Track original casing: normalized -> most-common original form
    case_map: dict[str, str] = {}
    case_counts: defaultdict[str, float] = defaultdict(float)

    for text, weight in texts:
        for emo in _extract_emojis(text):
            emojis[emo] += weight

        cleaned = _clean_text(text)
        original = _clean_text_preserve_case(text)
        if not cleaned:
            continue

        tokens = cleaned.split()
        orig_tokens = original.split()
        filtered = [t for t in tokens if len(t) > 1 and not t.isdigit()]
        orig_filtered = [
            o for t, o in zip(tokens, orig_tokens)
            if len(t) > 1 and not t.isdigit()
        ] if len(tokens) == len(orig_tokens) else filtered

        for t in filtered:
            all_unigrams[t] += weight
            if t not in STOPWORDS:
                display_words[t] += weight

        for n in range(2, 6):
            for i in range(len(filtered) - n + 1):
                gram = " ".join(filtered[i: i + n])
                ngram_counts[gram] += weight
                orig_gram = " ".join(orig_filtered[i: i + n]) if i + n <= len(orig_filtered) else gram
                if gram not in case_map or weight > case_counts.get(gram, 0):
                    case_map[gram] = orig_gram
                    case_counts[gram] = weight

    total_unigrams = sum(all_unigrams.values()) or 1.0
    total_weighted = sum(ngram_counts.values()) or 1.0
    base_min_freq = max(4.0, total_weighted * 0.0003)

    candidates: dict[str, float] = {}
    for gram, count in ngram_counts.items():
        gram_words = gram.split()
        n_words = len(gram_words)
        # Longer phrases appear less often by nature — scale min_freq down
        # so 4-5 word phrases only need ~40% of the base threshold to qualify.
        length_scale = max(0.4, 1.0 - 0.15 * (n_words - 2))
        if count < base_min_freq * length_scale:
            continue
        non_stop = sum(1 for w in gram_words if w not in STOPWORDS)
        if non_stop < max(1, len(gram_words) // 2):
            continue
        candidates[gram] = count

    # Score using LLR * TF-IDF distinctiveness against background English corpus.
    # Phrases common in general English get dampened; personally distinctive ones get boosted.
    # Longer phrases get a length bonus to counteract LLR dilution.
    bg_bigrams, bg_total = _load_background_bigrams()

    scored: list[tuple[str, float, float]] = []
    for gram, count in candidates.items():
        gram_words = gram.split()
        n_words = len(gram_words)

        # LLR component: use minimum pairwise LLR (weakest link)
        # instead of geometric mean — a phrase is only as strong as its
        # weakest word-pair bond.
        pairwise_llrs = []
        for j in range(n_words - 1):
            bigram = f"{gram_words[j]} {gram_words[j+1]}"
            k_ab = ngram_counts.get(bigram, 0) if n_words > 2 else count
            k_a = all_unigrams.get(gram_words[j], 1.0)
            k_b = all_unigrams.get(gram_words[j+1], 1.0)
            pairwise_llrs.append(_llr_score(k_ab, k_a, k_b, total_unigrams))

        llr = min(pairwise_llrs) if pairwise_llrs else 0.0
        if llr <= 0:
            continue

        # TF-IDF distinctiveness: compare user frequency against background.
        # Background corpus only has bigrams, so longer phrases automatically
        # get high distinctiveness (they won't appear in the background).
        user_freq = count / total_weighted
        bg_freq = bg_bigrams.get(gram, 0) / bg_total
        distinctiveness = math.log2(1.0 + user_freq / max(bg_freq, 1e-8))

        # Length bonus: prefer longer phrases (they're more informative and
        # personal). A 4-word phrase with decent cohesion should beat a
        # 2-word phrase with similar LLR.
        length_bonus = 1.0 + 0.3 * (n_words - 2)

        score = llr * distinctiveness * length_bonus * math.log2(1 + count)
        scored.append((gram, score, count))

    # Sort by score descending, then deduplicate.
    # Key change: prefer LONGER phrases over shorter sub-phrases.
    # Sort by length DESC first (longer phrases get first chance), then score DESC.
    scored.sort(key=lambda x: (-len(x[0].split()), -x[1]))
    accepted: list[tuple[str, float, float]] = []
    accepted_strs: list[str] = []
    for gram, score, count in scored:
        # Skip if this phrase is contained within an already-accepted longer phrase
        is_sub = any(gram in a for a in accepted_strs)
        if is_sub:
            continue
        # If accepting this phrase, remove any already-accepted shorter sub-phrases
        accepted = [(g, s, c) for g, s, c in accepted if g not in gram]
        accepted_strs = [g for g, _, _ in accepted]
        accepted.append((gram, score, count))
        accepted_strs.append(gram)
        if len(accepted) >= 15:
            break

    # Re-sort by score for final display order
    accepted.sort(key=lambda x: -x[1])

    # Use original casing for display
    phrases: defaultdict[str, float] = defaultdict(float)
    for gram, _score, count in accepted:
        display_form = case_map.get(gram, gram)
        phrases[display_form] = count

    return {"words": display_words, "phrases": phrases, "emojis": emojis}
        

def _get_peak_personality(peak_hour: int) -> str:
    if peak_hour in (22, 23, 0, 1, 2, 3):
        return "Night Owl"
    if peak_hour in (4, 5, 6, 7, 8):
        return "Early Bird"
    if peak_hour in (9, 10, 11):
        return "Morning Messenger"
    if peak_hour in (12, 13, 14):
        return "Lunch Texter"
    if peak_hour in (15, 16, 17):
        return "Afternoon Chatter"
    return "Evening Communicator"


