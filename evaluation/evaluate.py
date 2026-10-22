"""Pros and cons of the 51 held-out products: the 2020 output (as published in the dataset) against the
clause mode of this library, both judged against evaluation/gold_labels.csv.

Each listed clause is labelled by hand as
  right           an opinion about the product or the purchase, on the correct side
  wrong_polarity  an opinion on the wrong side ("A entrega foi bem rápida" as a con)
  no_opinion      a filler or fragment that says nothing about the product ("No mais", "O box")
The labels were written by Claude (Anthropic's model) reading each clause and the product name.
"clause" is the default: clauses repeated in more reviews first, then single strong ones, filling the
4 slots like 2020 did. "clause, 2+ reviews" lists only clauses found in two or more reviews. The clause mode works on the same 2020 clauses (the `sentences` file), so the comparison isolates
polarity, grouping and ranking, not the cut. Clauses missing a label are written to
results/unlabelled.csv.

    python evaluation/evaluate.py ../reviews-produtos-ptbr/sample
"""

import json
import sys
from pathlib import Path

import pandas as pd

from pros_e_contras import Review, summarize

HERE = Path(__file__).parent
folder = Path(sys.argv[1])
groups = [int(x) for x in (HERE / "eval_groups.txt").read_text().split()]
rev = pd.read_csv(folder / "reviews_sample.csv", usecols=["review_id", "group_id", "rating", "sentiment"])
sen = pd.read_csv(folder / "sentences_sample.csv", usecols=["sentence_id", "review_id", "group_id", "text"])
pc = pd.read_csv(folder / "pros_cons_sample.csv")
names = pd.read_csv(folder / "groups_sample.csv").set_index("group_id").group_name
gold = pd.read_csv(HERE / "gold_labels.csv")

rows = []
for gid in groups:
    for _, r in pc[pc.group_id == gid].iterrows():
        rows.append(("2020", gid, r.kind, int(r["rank"]), r.clause, int(r.mentions)))
    s = sen[sen.group_id == gid].sort_values("sentence_id")
    clauses = s.groupby("review_id").text.apply(lambda v: [str(t) for t in v]).to_dict()
    r = rev[rev.group_id == gid]
    reviews = [Review(i, rating=ra, clauses=clauses.get(i, [])) for i, ra in zip(r.review_id, r.rating)]
    for mode, mm in (("clause", None), ("clause, 2+ reviews", 2)):
        out = summarize(reviews, min_mentions=mm)
        for kind, items in (("pro", out.pros), ("con", out.cons)):
            rows += [(mode, gid, kind, k, it.clause, it.mentions) for k, it in enumerate(items, 1)]
res = pd.DataFrame(rows, columns=["mode", "group_id", "kind", "rank", "clause", "mentions"])
# a child's first name inside one 2020 clause is not repeated here
res.loc[(res.group_id == 883940) & res.clause.str.startswith("Meu filhinho "), "clause"] = \
    "Meu filhinho [nome] aproveitou bastante"
res = res.merge(gold.drop_duplicates(["group_id", "kind", "clause"]), on=["group_id", "kind", "clause"], how="left")
(HERE / "results").mkdir(exist_ok=True)
res.assign(product=res.group_id.map(names)).to_csv(HERE / "results/pros_cons_both_modes.csv", index=False)
todo = res[res.label.isna()][["group_id", "kind", "clause"]].drop_duplicates()
if len(todo):
    todo.to_csv(HERE / "results/unlabelled.csv", index=False)

summary = {}
for (mode, kind), d in res.groupby(["mode", "kind"]):
    d = d[d.label.notna()]
    n = len(d)
    summary[f"{mode} {kind}s"] = {
        "listed": n, "per_product": round(n / len(groups), 2),
        "right": round((d.label == "right").mean(), 3),
        "right_per_product": round((d.label == "right").sum() / len(groups), 2),
        "wrong_polarity": round((d.label == "wrong_polarity").mean(), 3),
        "no_opinion": round((d.label == "no_opinion").mean(), 3)}
(HERE / "results/summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
print(pd.DataFrame(summary).T.to_string())
print(f"{len(todo)} clauses without a label -> results/unlabelled.csv")
