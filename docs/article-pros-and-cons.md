# Pros and cons from reviews: what the 2020 method got wrong

[Leia em português](artigo-pros-e-contras.md)

From 2020 on, the product pages of my sites showed "Prós" and "Contras" (pros and cons) taken from store reviews. The Samsung Expert X23 notebook, with 1,947 reviews, looked like this:

| Pros | Cons |
|---|---|
| Muito bom · Produto muito bom · Otimo produto · Entrega rápida | Nao recomendo · Muito lento · **A entrega foi bem rápida** · Me arrependi |

"A entrega foi bem rápida" ("delivery was really fast") appears among the cons. This post covers why that happened, how often, and what changed when I rebuilt the method as a library in 2026.

## The 2020 method

My presentation from back then summed it up as a formula: **sentence splitting + sentiment analysis = pros and cons**. There were five steps:

1. AWS Comprehend gives the sentiment of each review: POSITIVE, NEGATIVE, NEUTRAL or MIXED.
2. The Stanford POS tagger tags every word.
3. The text is cut into clauses at punctuation and conjunctions ([post on that part](article-clause-splitting.md)).
4. Similar clauses of each product are grouped by phonetic and fingerprint keys.
5. The 4 most repeated clauses of the POSITIVE reviews become pros, and those of the NEGATIVE reviews become cons.

It sounds reasonable. Four flaws hide in those steps.

## Four flaws

**1. Sentiment belonged to the review, not the clause.** A negative review says "delivery was really fast, but the product is slow", and both clauses inherit NEGATIVE. MIXED reviews, the very ones that have pros *and* cons, were not used at all.

**2. Any two-word piece counted.** The cut leaves connectives and greetings behind. The cons of a DVD box set were *No mais · Ainda assim · O box · Desta forma* ("Other than that · Even so · The box · That way"). Products with few negative reviews suffered most, because anything repeated twice reached the top 4.

**3. Grouping joined opposites.** Two clauses became one as soon as any one of six keys matched. One key sorted the words and, because of a bug, skipped every other word. So "Produto de péssima qualidade" and "Produto de ótima qualidade" (terrible quality and great quality) could end up in the same group.

**4. Ties favoured the generic.** Between two clauses with the same count, the one most frequent across the whole site won. That is the opposite of IDF, so "Muito bom" almost always won.

## What changed

**Each clause gets its own score.** The score comes from a lexicon learned from the dataset itself, with no hand labelling:

- a clause from a 4–5 star review is positive evidence;
- a clause from a 1–2 star review is negative evidence;
- 3-star reviews are left out.

Each word's weight is the smoothed log-odds between the two sides, as in Monroe, Colaresi and Quinn's "Fightin' Words" (2008). I used stars rather than the AWS label because stars are the customer's own judgement. That gave 9.8 million positive and 1.9 million negative clauses, and a lexicon of 6,854 words.

Negation makes a new word: the three words after "não", "nunca", "nem" or "sem" (not, never, nor, without) count as `NOT_word`. This is what the lexicon learned on its own (words weighing less than 0.7 are left out and count as zero):

| word | weight | | word | weight |
|---|---:|---|---|---:|
| funciona (works) | +0.32 (weak, left out) | | NOT_funciona | −3.35 |
| recomendo (I recommend) | +3.47 | | NOT_recomendo | −3.88 |
| rápida (fast) | +2.30 | | troca (exchange) | −2.18 |
| atendeu (met my needs) | +3.25 | | NOT_atendeu | −3.58 |

**Filler is not an opinion.** A clause is listed only if its score reaches 1.5 on one side. A short list of markers ("fora isso", "no mais", "boa noite") never gets in.

**Grouping is exact** after removing accents, plurals and stopwords. Negations are kept, so "não recomendo" never joins "recomendo".

**Ranking counts distinct reviews.** Repeating a phrase in one review does not add up. Ties go to the stronger opinion, not to the phrase most frequent on the site.

## How much better

I held 51 products out of the lexicon training. Then I labelled every listed clause as *right*, *wrong side* or *no opinion*, both in the 2020 output as published and in the library's. Both use the same 2020 clauses.

| | right | wrong side | no opinion |
|---|---:|---:|---:|
| cons 2020 | 64.7% | 9.3% | 26.0% |
| cons 2026 | **89.7%** | 2.5% | 7.8% |
| pros 2020 | 97.1% | 0.5% | 2.5% |
| pros 2026 | **99.5%** | 0.0% | 0.5% |

The notebook from the start became:

| Pros | Cons |
|---|---|
| Muito bom · Otimo produto · Produto muito bom · Entrega rápida | Não recomendo · Achei um pouco lento · Não recomendo o produto além de ser muito lento… · O hd deu problema… |

The DVD box set went from *No mais · Ainda assim · O box · Desta forma* to *Rasga a toa · …ter vindo com defeito · A capa do box veio rasgada* ("tears easily · …arrived defective · the box cover arrived torn").

## What still goes wrong

- **Sentences, not words.** The box set's fourth con is "De descobrir o que virá em seguida". It comes from "ansiosa de descobrir o que virá em seguida" ("can't wait to find out what comes next"), which is praise. Sarcasm and double negation get through too.
- **Long cons.** When a product has few repeated complaints, the slots fill with clauses said only once, which are longer and more specific. With `min_mentions=2` the list is short and repeated: 2 cons per product, 89.4% right.
- **One labeller.** Claude (Anthropic's model) wrote the labels. They are in the repository for anyone to check, but a second human annotator would give an agreement measure I don't have yet.

## Why a lexicon and not an LLM

An LLM would write better pros and cons for a single product. For 222,000 products, a rule you can audit word by word, that runs on an ordinary machine with no per-call cost, still makes sense. And the 2020 question still stands: what do customers *repeat* about the product? That is counting, not generating.

*Code, lexicon and evaluation: [pros-e-contras-ptbr](https://github.com/CaiqueDourado/pros-e-contras-ptbr). Data: [portuguese-product-reviews](https://github.com/CaiqueDourado/portuguese-product-reviews) ([Kaggle](https://www.kaggle.com/datasets/caiquedourado/reviews-produtos-ptbr)). The story of the site the reviews were collected for: [case study É bom? Vale a pena?](https://github.com/CaiqueDourado/portuguese-product-reviews/blob/main/docs/case-study-e-bom-vale-a-pena.md).*
