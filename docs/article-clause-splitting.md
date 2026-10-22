# Splitting reviews into clauses: Google Cloud NL, Stanford, and 15 lines of rules

[Leia em português](artigo-divisao-de-clausulas.md)

To get pros and cons out of reviews, you first cut each text into pieces that say one thing. "Bonito, mas trava muito e esquenta" ("Nice-looking, but it freezes a lot and heats up") holds three opinions: *bonito*, *trava muito*, *esquenta*.

In 2020 I split the reviews I had collected from Brazilian stores this way; they now number 2.87 million. I used three tools, one after the other, and the third only came now, in 2026. This post covers what each one did and why the last one stays.

## The rule never changed

All three versions cut with the same rule:

- **at punctuation**, meaning a token with no letters: `,` `.` `!` `;`
- **at a conjunction**: *e, mas, ou, porém, pois…* (and, but, or, however, because…)

Some conjunctions do not cut and stay inside the clause: *que, se, como, quando, quanto, enquanto* and *apenas* (that, if, as, when, how much, while, only). They introduce an idea that cannot stand alone: "achei **que** era maior" ("I thought **that** it was bigger").

What changes between the versions is **who decides what is a conjunction**.

## 1. Google Cloud Natural Language (until January 2020)

The first version sent each review to Google Cloud NL's `AnalyzeSyntax` in Portuguese. It cut at the tokens tagged `PUNCT` and `CONJ`. Quality was good, but Google charges per text analysed, and there were millions of reviews, with more arriving every day. A comment in the code reads **"January 9, 2020. Stopped. Way too expensive!!!"**

## 2. Stanford POS tagger (2020)

The replacement was Stanford's MaxentTagger, running inside .NET, with a third-party Portuguese model (`corenlp-model-pt`). It was free and ran locally. It cut the 12.9 million clauses published in the [reviews dataset](https://github.com/CaiqueDourado/reviews-produtos-ptbr).

The price became the model's mistakes. It mislabels capitalised and colloquial words:

```text
não/PNOUN Recomendo/PNOUN     gostei/NOUN     dão/ADP     aguenta/ADJ
```

The cut depends on the tag, so a tagging error becomes a cutting error. These examples come from the data:

| Review | Stanford (2020) |
|---|---|
| entrega rápida antes **do** previsto | *entrega rápida antes* · *previsto* |
| é um produto **q** responde as expectativas | *é um produto* · *responde as expectativas* |
| **porém** trava muito | *porém trava muito* (no cut) |

The model also needed preprocessing for cases it got wrong:

- a period added at the end, because "…Super indico" was tagged as punctuation;
- slashes protected, so "DANFE/XML" was not cut;
- periods glued to words separated ("obrigado.de nada").

## 3. Rules, no tagger (2026)

When I published the method as a library, I asked a simple question. The tagger was only used to recognise punctuation and conjunctions, and Portuguese coordinating conjunctions are a short list. So is the tagger needed at all?

```python
CUT = {"e", "mas", "ou", "porém", "porem", "contudo", "todavia", "entretanto", "pois"}
KEEP = {"que", "se", "como", "quando", "quanto", "enquanto", "apenas"}
```

The [`split`](../src/pros_e_contras/clauses.py) of [pros-e-contras-ptbr](https://github.com/CaiqueDourado/pros-e-contras-ptbr) tokenises the text and cuts at punctuation and at the words in `CUT`. That is all it does. On the example from the 2020 presentation, its output is identical to Stanford's:

> Não Recomendo, vão entre as gavetas e entre a gaveta e a estrutura. A parte inferior da gaveta não dá encaixe e com isso fica impossível fechar a parte traseira do mesmo. Produto de BAIXA QUALIDADE!

→ *Não Recomendo* · *vão entre as gavetas* · *entre a gaveta* · *a estrutura* · *A parte inferior da gaveta não dá encaixe* · *com isso fica impossível fechar a parte traseira do mesmo* · *Produto de BAIXA QUALIDADE*

The example also shows the limit of both versions. "entre a gaveta" ("between the drawer") and "a estrutura" ("the frame") mean nothing on their own. An "e" that joins two nouns gets cut as if it joined two clauses.

## How often the rules agree with Stanford

I compared the rules with the 2020 clauses on 15,100 reviews of the public sample. Reviews whose text was changed by the accent restoration were left out.

| | Rules | spaCy `pt_core_news_sm` |
|---|---:|---:|
| 2020 clauses also produced (recall) | 95.3% | 93.9% |
| Clauses that exist in 2020 (precision) | 94.9% | 94.9% |
| Reviews cut exactly the same | 88.1% | 86.3% |
| Speed | 22,000 reviews/s | 260 reviews/s |

I also added a modern tagger, spaCy's Portuguese model, cutting with the same rule. It does not get closer to Stanford than the rules do, and it is 85 times slower.

Reading the differences, most are tagger errors the rules do not make: Stanford cuts at "q" and at "do", and misses "porém" without its accent or at the start of a sentence. The other way round, the rules miss cuts that needed understanding of the sentence. One example is an unaccented "e" used as the verb "é" ("e lento", "is slow"), which the rules cut.

One deliberate choice: the rules do **not** cut at "nem" ("nor"). In reviews it is almost always a negation ("nem liga", "it doesn't even turn on"). Separating the negation from its verb flips the opinion.

## Comparison

| | Google Cloud NL | Stanford + PT model | Rules |
|---|---|---|---|
| Cost | paid per text | free, local | free, local |
| Dependencies | API and key | Java via IKVM, third-party model | none |
| Speed | one network call per review | tags every word | about 22,000 reviews per second (2.87 million in about 2 minutes) |
| Typical errors | few | capitals, colloquial words | "e" joining nouns |

For this task, cutting opinions out of reviews, the tagger was not worth its cost. The library uses the rules by default. It also accepts a tagger, `spacy_tagger("pt_core_news_sm")`, for anyone who wants grammar-guided cuts. [`split_tagged`](../src/pros_e_contras/clauses.py) reproduces the 2020 rule on text that is already tagged.

Cutting well is half the job. The other half, deciding whether each clause is a pro or a con, is in the [article on pros and cons](article-pros-and-cons.md).

*Code and evaluation: [evaluation/splitter_agreement.py](../evaluation/splitter_agreement.py). Data: [reviews-produtos-ptbr](https://github.com/CaiqueDourado/reviews-produtos-ptbr) ([Kaggle](https://www.kaggle.com/datasets/caiquedourado/reviews-produtos-ptbr)).*
