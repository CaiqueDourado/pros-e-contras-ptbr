"""Command line.

    pros-e-contras split "Bonito, mas trava muito e esquenta."
    pros-e-contras score "Não funciona" "Entrega rápida"
    pros-e-contras summarize reviews.csv --text-column text --group-column group_id [--mode 2020 --sentiment-column sentiment]
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict

from . import __version__
from .clauses import split
from .polarity import label, score
from .summarize import Review, summarize


def _summarize(a) -> None:
    groups: dict[str, list[Review]] = defaultdict(list)
    with open(a.file, encoding="utf-8-sig", newline="") as f:
        for i, row in enumerate(csv.DictReader(f)):
            gid = row.get(a.group_column, "") if a.group_column else ""
            groups[gid].append(Review(row.get(a.id_column) or i, row.get(a.text_column, ""),
                                      sentiment=row.get(a.sentiment_column) if a.sentiment_column else None))
    w = csv.writer(sys.stdout, lineterminator="\n")
    w.writerow(["group", "kind", "rank", "clause", "mentions", "score", "example_review_id"])
    for gid, reviews in groups.items():
        s = summarize(reviews, mode=a.mode, top=a.top, min_mentions=a.min_mentions)
        for kind, items in (("pro", s.pros), ("con", s.cons)):
            for rank, it in enumerate(items, 1):
                w.writerow([gid, kind, rank, it.clause, it.mentions, "" if it.score is None else it.score,
                            it.example_review_id])


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="pros-e-contras", description="Pros and cons from reviews in Brazilian Portuguese.")
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("split", help="cut a text into clauses")
    p.add_argument("text", nargs="+")
    p = sub.add_parser("score", help="polarity of clauses")
    p.add_argument("clause", nargs="+")
    p = sub.add_parser("summarize", help="top pros and cons per product from a CSV of reviews")
    p.add_argument("file")
    p.add_argument("--text-column", default="text")
    p.add_argument("--group-column", default="group_id", help="product column; empty for one product")
    p.add_argument("--id-column", default="review_id")
    p.add_argument("--sentiment-column", help="review label POSITIVE/NEGATIVE, needed by --mode 2020")
    p.add_argument("--mode", choices=["clause", "2020"], default="clause")
    p.add_argument("--top", type=int, default=4)
    p.add_argument("--min-mentions", type=int)
    a = ap.parse_args(argv)
    if a.cmd == "split":
        for t in a.text:
            print(json.dumps(split(t), ensure_ascii=False))
    elif a.cmd == "score":
        for c in a.clause:
            print(f"{score(c):+.2f}\t{label(c)}\t{c}")
    else:
        _summarize(a)


if __name__ == "__main__":
    main()
