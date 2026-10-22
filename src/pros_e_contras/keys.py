"""Keys that decide which clauses are the same opinion, and the canonical spelling of each group.

2020 grouped clauses that shared ANY of six keys, including an order-free fingerprint that put
"produto de péssima qualidade" with "produto de ótima qualidade". The default here only joins
clauses whose words are the same once accents, case, plurals and stopwords are ignored, and it keeps
negations ("não", "sem", "nunca", "nem") as words, so "não recomendo" never joins "recomendo".
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable

import dedupkit_br as dk

NEGATIONS = {"nao", "não", "sem", "nunca", "nem", "jamais", "nenhum", "nenhuma"}
ACCENTED = set("áàâãéêíóôõúç")


def opinion_key(clause: str) -> str:
    """token_key with negations kept and word order preserved."""
    words = dk.normalize(clause).split()
    kept = [w if w in NEGATIONS else dk.singular(w) for w in words if w in NEGATIONS or w not in dk.STOPWORDS]
    return " ".join(kept)


def legacy_keys(clause: str) -> list[str]:
    """The 2020 key set (approximated with DedupKit): soft, phonetic, tokens, sorted tokens, fingerprint."""
    soft = dk.normalize(clause)
    return [k for k in (soft, dk.phonetic_key(clause), dk.token_key(clause), dk.legacy_fingerprint(clause)) if k]


def canonical_forms(clauses: Iterable[str], legacy: bool = False, frequency: Counter | None = None) -> dict[str, str]:
    """clause -> canonical spelling inside one product. The canonical spelling is the most frequent one
    (`frequency` = counts over the whole corpus, like 2020's `quantidade`, else counts in this product);
    ties go to the spelling with accents."""
    clauses = list(clauses)
    local = Counter(clauses)
    freq = frequency or local
    rank = lambda c: (freq.get(c, 0), any(ch in ACCENTED for ch in c.lower()), -len(c))  # noqa: E731
    if legacy:
        # 2020: each clause takes the most frequent spelling among the clauses that share one of its keys,
        # one hop only, so chains of loosely similar clauses do not collapse into one.
        holders: dict[str, list[str]] = defaultdict(list)
        for clause in local:
            for key in legacy_keys(clause):
                holders[key].append(clause)
        best_of = {k: max(v, key=rank) for k, v in holders.items()}
        return {c: max([c] + [best_of[k] for k in legacy_keys(c)], key=rank) for c in local}
    parent: dict[str, str] = {c: c for c in local}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    owner: dict[str, str] = {}
    for clause in local:
        for key in [opinion_key(clause)]:
            if not key:
                continue
            if key in owner:
                a, b = find(owner[key]), find(clause)
                if a != b:
                    parent[b] = a
            else:
                owner[key] = clause
    groups: dict[str, list[str]] = defaultdict(list)
    for clause in local:
        groups[find(clause)].append(clause)
    out = {}
    for members in groups.values():
        best = max(members, key=rank)
        for m in members:
            out[m] = best
    return out
