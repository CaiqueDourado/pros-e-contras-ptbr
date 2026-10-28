"""How often the rule splitter (no tagger) cuts a review exactly where the 2020 Stanford pipeline cut it.

Reference: the clauses of `sentences_sample.csv`, in order, per review. Only reviews whose text was not
changed by the ã/õ restoration are used, because the 2020 clauses were cut from the collected text.
Clauses are compared after accent folding and lower case (2020 stored them in sentence case).

    python evaluation/splitter_agreement.py ../portuguese-product-reviews/sample [--spacy]

With --spacy the cuts come from spaCy's pt_core_news_sm tags instead of the rule.
"""

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

import dedupkit_br as dk
from pros_e_contras import split

folder = Path(sys.argv[1])
use_spacy = "--spacy" in sys.argv
tagger = None
if use_spacy:
    from pros_e_contras import spacy_tagger
    tagger = spacy_tagger()
rev = pd.read_csv(folder / "reviews_sample.csv", usecols=["review_id", "text", "tilde_restored"])
sen = pd.read_csv(folder / "sentences_sample.csv", usecols=["sentence_id", "review_id", "text"])
ref = sen.sort_values("sentence_id").groupby("review_id").text.apply(lambda v: [dk.normalize(str(t)) for t in v])
rev = rev[(rev.tilde_restored != True) & rev.review_id.isin(ref.index) & rev.text.notna()]  # noqa: E712

tp = fp = fn = exact = 0
disagree = []
for rid, text in zip(rev.review_id, rev.text):
    gold = Counter(c for c in ref[rid] if c)
    pred = Counter(c for c in (dk.normalize(x) for x in split(text, tagger)) if c)
    hit = sum((gold & pred).values())
    tp, fp, fn = tp + hit, fp + sum(pred.values()) - hit, fn + sum(gold.values()) - hit
    if gold == pred:
        exact += 1
    elif len(disagree) < 30:
        disagree.append({"review_id": int(rid), "only_2020": sorted((gold - pred).elements()),
                         "only_rules": sorted((pred - gold).elements())})
res = {"reviews": len(rev), "clauses_2020": tp + fn, "clauses_rules": tp + fp,
       "precision": round(tp / (tp + fp), 4), "recall": round(tp / (tp + fn), 4),
       "reviews_cut_identically": round(exact / len(rev), 4)}
out = Path(__file__).with_name("results")
out.mkdir(exist_ok=True)
(out / ("splitter_agreement_spacy.json" if use_spacy else "splitter_agreement.json")).write_text(json.dumps({**res, "examples_of_disagreement": disagree},
                                                        ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(res, indent=1))
