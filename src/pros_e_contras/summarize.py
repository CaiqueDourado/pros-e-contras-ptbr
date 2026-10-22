"""Top pros and cons of one product from its reviews.

mode="2020" reproduces the original rule: every clause takes the sentiment of its whole review
(POSITIVE -> pro candidate, NEGATIVE -> con candidate, MIXED and NEUTRAL ignored), clauses need
two words, clauses are grouped by any of the legacy keys, and the 4 most frequent win, ties broken
by how common the clause is in the whole corpus.

mode="clause" (default) scores each clause on its own, so a positive clause inside a negative review
is not a con, MIXED reviews contribute, and clauses without an opinion word ("No mais", "O box")
never make the list. Groups use negation-safe keys; ranking counts distinct reviews, then the strength
of the opinion. With min_mentions=2 a clause must come from two reviews: shorter lists, fewer one-off
stories.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from . import clauses as cl
from .keys import canonical_forms
from .polarity import is_filler, load_lexicon, score



@dataclass
class Review:
    review_id: object
    text: str = ""
    rating: int | None = None
    sentiment: str | None = None          # POSITIVE / NEGATIVE / NEUTRAL / MIXED (2020 mode)
    clauses: list[str] | None = None      # already cut (e.g. from the dataset); else cut from text


@dataclass
class Item:
    clause: str
    mentions: int
    example_review_id: object
    score: float | None = None


@dataclass
class Summary:
    pros: list[Item] = field(default_factory=list)
    cons: list[Item] = field(default_factory=list)


def _clauses(review: Review, tagger) -> list[str]:
    if review.clauses is not None:
        return [c for c in review.clauses if c]
    return [cl.sentence_case(c) for c in cl.split(review.text or "", tagger)]


def summarize(reviews: list[Review], mode: str = "clause", top: int = 4, min_mentions: int | None = None,
              frequency: Counter | None = None, threshold: float = 1.5, tagger=None, canonical: dict | None = None, lexicon=None) -> Summary:
    if mode not in ("clause", "2020"):
        raise ValueError("mode must be 'clause' or '2020'")
    rows = []  # (review_id, clause, polarity, score)
    lex = lexicon if lexicon is not None else (load_lexicon() if mode == "clause" else None)
    for r in reviews:
        for c in _clauses(r, tagger):
            if len(c.split()) < 2:
                continue
            if mode == "2020":
                pol = {"POSITIVE": "pro", "NEGATIVE": "con"}.get((r.sentiment or "").upper())
                rows.append((r.review_id, c, pol, None))
            else:
                if is_filler(c):
                    continue
                s = score(c, lex)
                pol = "pro" if s >= threshold else "con" if s <= -threshold else None
                rows.append((r.review_id, c, pol, s))
    canon = canonical_forms([c for _, c, _, _ in rows], legacy=(mode == "2020"), frequency=frequency)
    if canonical:  # e.g. the 2020 `canonical` column of the dataset, for an exact reproduction
        canon.update({c: canonical[c] for c in canon if c in canonical})
    if min_mentions is None:
        min_mentions = 1
    out = Summary()
    for kind in ("pro", "con"):
        count, reviewers, scores, example = Counter(), defaultdict(set), defaultdict(list), {}
        for rid, c, pol, s in rows:
            if pol != kind:
                continue
            key = canon[c]
            count[key] += 1
            reviewers[key].add(rid)
            example.setdefault(key, rid)
            if s is not None:
                scores[key].append(s)
        if mode == "2020":
            ranked = sorted(count, key=lambda k: (-count[k], -(frequency or {}).get(k, 0), k))
            items = [Item(k, count[k], example[k]) for k in ranked]
        else:
            ranked = sorted(reviewers, key=lambda k: (-len(reviewers[k]), -abs(sum(scores[k]) / len(scores[k])), k))
            items = [Item(k, len(reviewers[k]), example[k], round(sum(scores[k]) / len(scores[k]), 2))
                     for k in ranked if len(reviewers[k]) >= min_mentions]
        setattr(out, "pros" if kind == "pro" else "cons", items[:top])
    return out
