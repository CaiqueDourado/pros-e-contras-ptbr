"""Pros and cons of a product from its reviews in Brazilian Portuguese.

>>> from pros_e_contras import Review, summarize
>>> s = summarize([Review(1, "Ótimo produto, entrega rápida"), Review(2, "Bonito, mas trava muito")])
"""

from .clauses import parse_tagged, sentence_case, spacy_tagger, split, split_tagged, tag_by_rule
from .keys import canonical_forms, legacy_keys, opinion_key
from .polarity import FILLERS, features, is_filler, label, load_lexicon, score
from .summarize import Item, Review, Summary, summarize

__all__ = ["FILLERS", "Item", "Review", "Summary", "canonical_forms", "features", "is_filler", "label", "legacy_keys", "load_lexicon",
           "opinion_key", "parse_tagged", "score", "sentence_case", "spacy_tagger", "split", "split_tagged",
           "summarize", "tag_by_rule"]
__version__ = "0.1.0"
