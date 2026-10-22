"""Cut a review into clauses, as the 2020 pipeline did.

The 2020 rule (Stanford POS tagger, Portuguese model): walk the tagged tokens and close the clause at
a punctuation token that has no letters, or at a conjunction, except the conjunctions
que, se, como, quando, quanto, enquanto, apenas, which stay inside the clause. Brackets are dropped.

`split_tagged` applies that rule to tokens that are already tagged (the `tagged` column of the
reviews dataset, "word/TAG word/TAG"). `split` needs no tagger: it recognises punctuation and the
Portuguese coordinating conjunctions by spelling, which is what the tagger was used for.
"""

from __future__ import annotations

import re
from typing import Iterable

KEEP = {"que", "se", "como", "quando", "quanto", "enquanto", "apenas"}
CUT = {"e", "mas", "ou", "porém", "porem", "contudo", "todavia", "entretanto", "pois"}
BRACKETS = {"-LRB-", "-RRB-", "-LCB-", "-RCB-", "-LSB-", "-RSB-", "(", ")", "[", "]", "{", "}"}
TOKEN = re.compile(r"\w+(?:[-'/]\w+)*|[^\w\s]", re.UNICODE)
HAS_LETTER = re.compile(r"[A-Za-zÀ-ÿ]")


def preprocess(text: str) -> str:
    """The 2020 clean-up: separate punctuation glued to words ("obrigado.de nada"), collapse spaces."""
    text = re.sub(r"(?<=[A-Za-zÀ-ÿ])([.:!?;])(?=[A-Za-zÀ-ÿ])", r"\1 ", text)
    return re.sub(r"\s+", " ", text).strip()


def sentence_case(text: str) -> str:
    """How 2020 stored clauses: first letter upper case, the rest lower case."""
    return text[:1].upper() + text[1:].lower() if text else text


def split_tagged(tokens: Iterable[tuple[str, str]], keep_case: bool = True) -> list[str]:
    """Clauses from (word, tag) pairs, with the exact 2020 rule."""
    clauses, current = [], []
    for word, tag in tokens:
        if word in BRACKETS or tag in BRACKETS:
            continue
        cut = (tag in (".", "PUNCT") and not HAS_LETTER.search(word)) or (
            tag in ("CONJ", "CCONJ") and word.lower() not in KEEP)
        if cut:
            if current:
                clauses.append(" ".join(current))
            current = []
        else:
            current.append(word)
    if current:
        clauses.append(" ".join(current))
    return [c if keep_case else sentence_case(c) for c in clauses]


def parse_tagged(tagged: str) -> list[tuple[str, str]]:
    """'Produto/PNOUN excelente/ADJ' -> [('Produto', 'PNOUN'), ('excelente', 'ADJ')]."""
    pairs = []
    for item in tagged.split():
        word, _, tag = item.rpartition("/")
        pairs.append((word or item, tag))
    return pairs


def tag_by_rule(text: str) -> list[tuple[str, str]]:
    """Tags that matter for cutting, without a model: punctuation '.', conjunctions 'CONJ', other 'X'."""
    out = []
    for tok in TOKEN.findall(preprocess(text)):
        if not HAS_LETTER.search(tok) and not tok.isdigit():
            out.append((tok, "."))
        elif tok.lower() in CUT:
            out.append((tok, "CONJ"))
        else:
            out.append((tok, "X"))
    return out


def split(text: str, tagger=None) -> list[str]:
    """Clauses of a review. `tagger(text) -> [(word, tag)]` can be any POS tagger (spaCy, Stanford);
    by default the rule above is used."""
    if not text:
        return []
    return split_tagged((tagger or tag_by_rule)(text))


def spacy_tagger(model: str = "pt_core_news_sm"):
    """Optional adapter for spaCy (pip install spacy && python -m spacy download pt_core_news_sm)."""
    import spacy

    nlp = spacy.load(model, disable=["ner", "lemmatizer", "parser"])

    def tag(text: str) -> list[tuple[str, str]]:
        return [(t.text, "." if t.pos_ == "PUNCT" else t.pos_) for t in nlp(preprocess(text))]

    return tag
