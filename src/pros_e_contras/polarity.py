"""Polarity of one clause, from a lexicon learned on the reviews themselves.

The lexicon (data/lexicon.tsv) was learned by tools/learn_lexicon.py from the clauses of the
portuguese-product-reviews dataset: a word's weight is how much more often it appears in clauses of
4-5 star reviews than in clauses of 1-2 star reviews (smoothed log-odds, classes balanced). Words
after a negation ("não", "nunca", "nem", "sem") are learned and scored as separate features
("NOT_funciona"), so "não funciona" is negative even though "funciona" is positive.
"""

from __future__ import annotations

from functools import lru_cache
from importlib import resources
from pathlib import Path

import dedupkit_br as dk

NEGATORS = {"nao", "nunca", "nem", "sem", "jamais", "nenhum", "nenhuma"}
WINDOW = 3


def features(clause: str) -> list[str]:
    """Words of a clause, accents folded, with up to 3 words after a negation marked NOT_."""
    out, left = [], 0
    for w in dk.normalize(clause).split():
        if w in NEGATORS:
            out.append(w)
            left = WINDOW
            continue
        out.append(f"NOT_{w}" if left else w)
        left = max(left - 1, 0)
    return out


# Discourse markers and greetings that the clause cut leaves on their own. They carry the tone of
# the sentence around them, not an opinion about the product ("Fora isso", "No mais", "Boa noite").
FILLERS = {
    "ainda assim", "alem disso", "alias", "assim", "boa noite", "boa tarde", "bom dia", "com isso", "dessa forma",
    "desta forma", "de resto", "do mais", "enfim", "entao", "fora isso", "mesmo assim", "na verdade", "no entanto",
    "no mais", "no geral", "ou seja", "por exemplo", "por isso", "por enquanto", "sendo assim", "tirando isso",
    "tirando esse detalhe", "fora esse detalhe", "fora isto", "tirando isto", "de qualquer forma", "de qualquer jeito",
    "ate agora", "ate o momento", "por enquanto", "so isso", "apenas isso", "obrigado", "obrigada",
}


def is_filler(clause: str) -> bool:
    return dk.normalize(clause) in FILLERS


@lru_cache(maxsize=4)
def load_lexicon(path: str | None = None) -> dict[str, float]:
    text = (Path(path).read_text(encoding="utf-8") if path else
            resources.files("pros_e_contras").joinpath("data/lexicon.tsv").read_text(encoding="utf-8"))
    lex = {}
    for line in text.splitlines():
        if line and not line.startswith("#"):
            word, weight = line.split("\t")[:2]
            lex[word] = float(weight)
    return lex


def score(clause: str, lexicon: dict[str, float] | None = None) -> float:
    """Sum of the weights of the clause's words: > 0 positive, < 0 negative, 0 no opinion word."""
    lex = lexicon if lexicon is not None else load_lexicon()
    return sum(lex.get(f, 0.0) for f in features(clause))


def label(clause: str, threshold: float = 1.5, lexicon: dict[str, float] | None = None) -> str:
    if is_filler(clause):
        return "neutral"
    s = score(clause, lexicon)
    return "positive" if s >= threshold else "negative" if s <= -threshold else "neutral"
