from __future__ import annotations

import re
from collections import Counter

STOPWORDS = {
    "and",
    "or",
    "of",
    "the",
    "for",
    "in",
    "on",
    "with",
    "to",
    "using",
    "based",
    "study",
    "studies",
    "research",
    "analysis",
    "approach",
    "methods",
    "method",
    "systems",
    "system",
}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{2,}", normalize_text(text))
        if token not in STOPWORDS
    ]


def keyword_set(texts: list[str], limit: int = 60) -> set[str]:
    counts: Counter[str] = Counter()
    for text in texts:
        counts.update(tokenize(text))
    return {word for word, _ in counts.most_common(limit)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def phrase_overlap(query: str, document: str) -> float:
    query_terms = keyword_set([query], limit=25)
    document_terms = keyword_set([document], limit=120)
    return jaccard(query_terms, document_terms)


def sentence_case(text: str) -> str:
    if not text:
        return text
    return text[0].upper() + text[1:]
