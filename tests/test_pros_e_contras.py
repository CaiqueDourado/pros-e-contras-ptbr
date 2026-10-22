from pros_e_contras import (Review, canonical_forms, is_filler, label, opinion_key, parse_tagged, score, split,
                            split_tagged, summarize)


def test_split_by_rule():
    assert split("Bonito, mas trava muito e esquenta. Não recomendo!") == ["Bonito", "trava muito", "esquenta",
                                                                         "Não recomendo"]


def test_split_keeps_que_se_como():
    assert split("Achei que era maior, se quiser algo bom compre outro") == ["Achei que era maior",
                                                                              "se quiser algo bom compre outro"]


def test_split_tagged_is_the_2020_rule():
    tagged = "Não/ADV Recomendo/VERB ,/. vão/VERB entre/ADP as/DET gavetas/NOUN e/CONJ entre/ADP a/DET estrutura/NOUN ./."
    assert split_tagged(parse_tagged(tagged)) == ["Não Recomendo", "vão entre as gavetas", "entre a estrutura"]


def test_split_tagged_follows_the_tagger_even_when_wrong():
    # a mistagged conjunction does not cut, as in 2020
    assert split_tagged(parse_tagged("bom/ADJ e/NOUN barato/ADJ")) == ["bom e barato"]


def test_negation_flips_polarity():
    assert score("Funciona muito bem") > 0
    assert label("Não funciona") == "negative"
    assert label("Não recomendo") == "negative" and label("Recomendo") == "positive"


def test_fillers_are_neutral():
    assert is_filler("Fora isso") and is_filler("No mais")
    assert label("Fora isso") == "neutral"


def test_opinion_key_keeps_negation_and_order():
    assert opinion_key("Não recomendo") != opinion_key("Recomendo")
    assert opinion_key("Produto de ótima qualidade") != opinion_key("Produto de péssima qualidade")
    assert opinion_key("Ótimo produto!") == opinion_key("otimo produtos")


def test_canonical_prefers_frequent_then_accented():
    canon = canonical_forms(["Otimo produto", "Ótimo produto", "Ótimo produto", "Otimo produto!"])
    assert set(canon.values()) == {"Ótimo produto"}


def test_canonical_never_merges_opposites():
    canon = canonical_forms(["Produto de ótima qualidade", "Produto de péssima qualidade"])
    assert canon["Produto de ótima qualidade"] != canon["Produto de péssima qualidade"]


REVIEWS = [
    Review(1, "Ótimo produto, entrega rápida.", 5, "POSITIVE"),
    Review(2, "Ótimo produto. Entrega rápida!", 5, "POSITIVE"),
    Review(3, "A entrega foi rápida, mas não funciona. Fora isso, não recomendo.", 1, "NEGATIVE"),
    Review(4, "Não funciona e esquenta muito. Não recomendo", 1, "NEGATIVE"),
]


def test_clause_mode_scores_each_clause():
    s = summarize(REVIEWS)
    pros, cons = [i.clause for i in s.pros], [i.clause for i in s.cons]
    assert "Ótimo produto" in pros and "Não funciona" in cons and "Não recomendo" in cons
    assert all("entrega" not in c.lower() for c in cons)      # a positive clause of a negative review
    assert "Fora isso" not in cons                             # filler
    assert s.cons[0].mentions == 2 and s.cons[0].score < 0


def test_2020_mode_inherits_the_review_sentiment():
    s = summarize(REVIEWS, mode="2020")
    assert "A entrega foi rápida" in [i.clause for i in s.cons]   # the documented 2020 limit


def test_given_clauses_and_canonical_are_used():
    r = [Review(1, clauses=["Muito bom", "Bem embalado"], sentiment="POSITIVE")]
    s = summarize(r, mode="2020", canonical={"Bem embalado": "Muito bem embalado"})
    assert {i.clause for i in s.pros} == {"Muito bom", "Muito bem embalado"}


def test_cli(capsys):
    from pros_e_contras.cli import main
    main(["score", "Não funciona"])
    assert "negative" in capsys.readouterr().out
