# Limbum–English corpus (Unicode version)

## Files

| File | Rows | Description |
|---|---|---|
| `split.csv` | 8,829 | Converted, cleaned corpus with the split used in the paper |
| `split_how.txt` | – | How the split was made |
| `excluded_mixed_encoding.csv` | 13 | New Testament verses removed because they mix encodings |
| `raw/nt_legacy_encoding.csv` | – | New Testament as received (legacy font encoding) |
| `raw/dictionary.csv` | – | Dictionary sentences as received (already Unicode) |

`split.csv` columns: `lmp` (Limbum, Unicode NFC, tone-marked), `eng` (English), `source`
(`nt` = New Testament, `dict` = dictionary), `split` (`train` / `dev` / `test`).

| | train | dev | test |
|---|---|---|---|
| New Testament | 5,897 | 738 | 738 |
| Dictionary | 1,165 | 146 | 145 |

The New Testament is split into 20 contiguous blocks of verses (16 train, 2 dev, 2 test), so
test verses never sit next to training verses; the dictionary is split randomly (80/10/10).
Random seed 0 throughout.

## Orthography

Tone is marked on vowels and syllabic nasals with combining diacritics:

| Mark | Unicode | Tone |
|---|---|---|
| grave (à) | U+0300 | low |
| circumflex (â) | U+0302 | falling |
| caron (ǎ) | U+030C | rising (dictionary only) |
| unmarked | – | high or mid |

Special letters: ɛ, ʉ, ŋ (and capitals Ɛ, Ʉ, Ŋ). The apostrophe `'` is a letter (glottal stop).

## The legacy font encoding

The New Testament text was typed with an 8-bit font in which special letters and tone marks
were mapped onto French accented characters, with each tone glyph typed *after* its vowel.
`scripts/legacy_to_unicode.py` converts it:

| Legacy | Unicode | Role |
|---|---|---|
| á, Á | ɛ, Ɛ | vowel letter |
| ú, Ú | ʉ, Ʉ | vowel letter |
| ñ, Ñ | ŋ, Ŋ | consonant letter |
| ï, Ï | i, I | base for a following tone glyph |
| è, ì (after a vowel) | combining grave | low tone |
| ê, â, î, û (after a vowel) | combining circumflex | falling tone |

Example (Luke 11:2): `E m laèa neè woweèe enáê` → `E m làa nè wowèe enɛ̂`, identical to the
Unicode text published on Omniglot.

Cleaning steps after conversion (all in `scripts/build_corpus.py`):

1. 102,442 tone glyphs attached to their vowels; 13 could not be attached. All 13 are in 13
   training verses that mix legacy glyphs with genuine Unicode accented letters (à, ù, é, …);
   these verses are excluded.
2. 43 rows repaired where a tone mark was duplicated or separated from a syllabic nasal by a
   space (29 dictionary, 14 New Testament).
3. Curly quotation marks replaced with ASCII quotes (NLLB-200's tokenizer maps them to `<unk>`).

If you work with other Limbum Bible-derived text, check its character inventory first: legacy
text contains á, ú, ñ and no ɛ, ʉ, ŋ.

## Terms of use

> **TODO (authors):** state the licence before making the repository public. It must match the
> terms under which the corpus was originally released with Ntohsi et al. (2026) and any terms
> set by the rights holders of the Limbum New Testament translation and the dictionary. The
> English side (American Standard Version, 1901) is in the public domain.

## Source

Corpus first released with: Ntohsi, Tuyishimire, Kafesu, Ogore, Babalola and Ankeli (2026),
*Embedding Initialization for Unseen Low-resource Languages in Multilingual NMT: A Case Study on
Limbum–English Translation*, arXiv:2608.07629.
