"""Learn src/pros_e_contras/data/lexicon.tsv from the clauses of portuguese-product-reviews.

A clause of a 4-5 star review counts as positive evidence, of a 1-2 star review as negative; 3 stars
are left out. Stars, not the AWS label, because stars are the customer's own judgement. For every
feature (a word, or NOT_word after a negation) the weight is the smoothed log-odds of the two rates,
kept only when its z-score is high enough (Monroe, Colaresi and Quinn 2008, "Fightin' Words"). The
products in evaluation/eval_groups.txt are excluded, so the evaluation never sees its own clauses.

Two stages, because counting the full dataset (12.9M clauses) takes a while and the weighting is quick:

    # count: the sample in the dataset repository, or the full Parquet files from Kaggle (needs duckdb)
    python tools/learn_lexicon.py count --sample ../portuguese-product-reviews/sample --out counts.tsv
    python tools/learn_lexicon.py count --parquet D:/kaggle/portuguese-product-reviews --out counts.tsv
    # weigh
    python tools/learn_lexicon.py weigh counts.tsv   # tools/word_counts.tsv holds the counts of the full dataset
"""

import argparse
import math
from collections import Counter
from pathlib import Path

import dedupkit_br as dk
from pros_e_contras.polarity import NEGATORS, features

ROOT = Path(__file__).resolve().parents[1]


def clause_features(text: str) -> set[str]:
    return {f for f in features(text) if f in NEGATORS or f.removeprefix("NOT_") not in dk.STOPWORDS}


def rows_from_sample(folder: Path, held: set[int]):
    import pandas as pd
    rev = pd.read_csv(folder / "reviews_sample.csv", usecols=["review_id", "rating"])
    sen = pd.read_csv(folder / "sentences_sample.csv", usecols=["review_id", "group_id", "text"])
    sen = sen[~sen.group_id.isin(held)].merge(rev, on="review_id")
    yield from zip(sen.text.astype(str), sen.rating)


def rows_from_parquet(folder: Path, held: set[int]):
    import duckdb
    con = duckdb.connect()
    con.execute("CREATE TEMP TABLE held(g BIGINT)")
    con.executemany("INSERT INTO held VALUES (?)", [(g,) for g in held])
    cur = con.execute(f"""
        SELECT s.text, r.rating FROM '{(folder / "sentences.parquet").as_posix()}' s
        JOIN '{(folder / "reviews.parquet").as_posix()}' r USING (review_id)
        WHERE r.rating IN (1, 2, 4, 5) AND s.group_id NOT IN (SELECT g FROM held)""")
    while batch := cur.fetchmany(200_000):
        yield from batch


def count(a):
    held = {int(x) for x in (ROOT / "evaluation/eval_groups.txt").read_text().split()}
    rows = rows_from_sample(Path(a.sample), held) if a.sample else rows_from_parquet(Path(a.parquet), held)
    pos, neg, n = Counter(), Counter(), Counter()
    for i, (text, rating) in enumerate(rows):
        if rating not in (1, 2, 4, 5):
            continue
        side = "pos" if rating >= 4 else "neg"
        n[side] += 1
        (pos if side == "pos" else neg).update(clause_features(str(text)))
        if i and i % 1_000_000 == 0:
            print(f"{i:,} clauses")
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(f"#clauses\t{n['pos']}\t{n['neg']}\n")
        for w in sorted(set(pos) | set(neg)):
            if pos[w] + neg[w] >= 5:
                f.write(f"{w}\t{pos[w]}\t{neg[w]}\n")
    print(f"{n['pos']:,} positive and {n['neg']:,} negative clauses -> {a.out}")


def weigh(a):
    pos, neg = {}, {}
    n_clauses = None
    for line in Path(a.counts).read_text(encoding="utf-8").splitlines():
        w, p, q = line.split("\t")
        if w == "#clauses":
            n_clauses = (int(p), int(q))
            continue
        pos[w], neg[w] = int(p), int(q)
    vocab = [w for w in pos if pos[w] + neg[w] >= a.min_count and w not in NEGATORS]
    n_pos, n_neg = sum(pos[w] for w in vocab), sum(neg[w] for w in vocab)
    alpha, rows = 0.5, []
    for w in vocab:
        p, q = pos[w] + alpha, neg[w] + alpha
        delta = math.log(p / (n_pos + alpha * len(vocab) - p)) - math.log(q / (n_neg + alpha * len(vocab) - q))
        if abs(delta) >= a.min_weight and abs(delta / math.sqrt(1 / p + 1 / q)) >= a.z:
            rows.append((w, round(delta, 3), pos[w], neg[w]))
    rows.sort(key=lambda r: -r[1])
    head = [
        "# feature\tweight\tclauses_4_5_stars\tclauses_1_2_stars",
        f"# portuguese-product-reviews: {n_clauses[0]:,} clauses of 4-5 star and {n_clauses[1]:,} of 1-2 star reviews, "
        f"evaluation products excluded; z >= {a.z}, |weight| >= {a.min_weight}, min count {a.min_count}",
    ]
    Path(a.out).write_text("\n".join(head + ["\t".join(map(str, r)) for r in rows]) + "\n", encoding="utf-8")
    print(f"{len(rows)} features ({sum(r[1] > 0 for r in rows)} positive) -> {a.out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("count")
    src = c.add_mutually_exclusive_group(required=True)
    src.add_argument("--sample", help="folder with reviews_sample.csv and sentences_sample.csv")
    src.add_argument("--parquet", help="folder with reviews.parquet and sentences.parquet")
    c.add_argument("--out", default="counts.tsv")
    w = sub.add_parser("weigh")
    w.add_argument("counts")
    w.add_argument("--out", default=str(ROOT / "src/pros_e_contras/data/lexicon.tsv"))
    w.add_argument("--z", type=float, default=4.0)
    w.add_argument("--min-count", type=int, default=100)
    w.add_argument("--min-weight", type=float, default=0.7, help="drop words that lean only slightly to one side")
    a = ap.parse_args()
    count(a) if a.cmd == "count" else weigh(a)


if __name__ == "__main__":
    main()
