# Tone Generation in an Unsupported Language

Code, data and model outputs for

> **Tone Generation in an Unsupported Language: Evaluating English-to-Limbum Translation with NLLB-200**
> Samuel Babalola, Oche David Ankeli and Samiratu Ntohsi.
> *Proceedings of the 2026 AI for African Languages Conference (AfriLang AI)*, PMLR, 2026.

Limbum (Grassfields Bantu, Cameroon) marks tone with diacritics, so one wrong mark can change a
word's meaning: *làa* 'say' vs. *laa* 'cook'. We fine-tune NLLB-200, which has never seen Limbum,
on about 7,000 English–Limbum sentence pairs and measure how well it writes tone.

**Main findings**

* On words it translates correctly (about half of the reference words), the model marks tone
  correctly 98.5% of the time for words with a fixed tone pattern, but 88.1% of the time for
  *contested* words, whose tone marking varies with context.
* Removing every tone mark changes chrF++ by only 1.9 points, so the metric barely registers
  these errors.
* Encoding tone marks as separate tokens does not help, and translating without tone and then
  restoring it is significantly worse for tone.
* Most of the New Testament text was stored in a **legacy font encoding** that disguises vowel
  letters and tone marks as French accented characters. We release a verified Unicode conversion.

## Repository contents

```
data/
  split.csv                       converted corpus (8,829 pairs) with the train/dev/test split used in the paper
  split_how.txt                   how the split was made
  excluded_mixed_encoding.csv     13 New Testament verses excluded (mixed legacy/Unicode encoding)
  raw/nt_legacy_encoding.csv      New Testament as received, in the legacy font encoding
  raw/dictionary.csv              dictionary sentences (Unicode), as received
scripts/
  legacy_to_unicode.py            legacy font encoding -> Unicode converter (usable on any legacy Limbum text)
  build_corpus.py                 rebuilds data/split.csv from data/raw/ (identical output)
  tone_metrics.py                 tone-aware metrics: toned/toneless chrF++, tone accuracy, coverage
  evaluate.py                     recomputes every reported number from the released outputs (CPU)
notebooks/
  limbum_tone_experiments.ipynb   the notebook used for the paper (Colab T4), with its outputs
outputs/
  unicode/runs/<system>_seed<k>/  NLLB-200 test outputs (test_hyp.txt) and training logs (meta.json)
  unicode/restorers/              ByT5 restorer outputs on each seed's toneless output, and on gold input (oracle)
  unicode/audit/                  orthography and tokenizer audit, contested word list
  legacy/runs/                    outputs of models trained on the unconverted legacy text
results/                          per-seed metrics, significance tests, legacy-vs-Unicode comparison, word-level errors
human_eval/                       native-speaker evaluation workbook (annotated) and the A/B assignment key
```

System names in files differ slightly from the paper: `stripped` = *Toneless*, `byt5` = *ByT5 restore*,
`byt5_src` = *source-aware ByT5*. All test outputs have one line per sentence of the test split
(883 lines), in the order of `data/split.csv`.

## Reproducing the results

**Without a GPU (about a minute).** Recompute all tables, significance tests and the
human-evaluation summary from the released outputs:

```bash
pip install -r requirements.txt
python scripts/evaluate.py          # writes results/reproduced/ and checks it against results/
python scripts/build_corpus.py --check   # rebuilds the corpus from data/raw/ and checks it
```

Both scripts report whether their output is identical to the released files.

**Training from scratch.** `notebooks/limbum_tone_experiments.ipynb` is the notebook used for the
paper, kept as it was run in Colab (T4 GPU) with outputs saved to Google Drive. To re-run it,
open it in Colab and, in the configuration cell, point `DATA_PATH` to `data/split.csv` and
`OUT_DIR_DRIVE` to a new folder in your Drive. Each NLLB-200 run takes about 1 hour and each
restorer about 2 hours; finished runs are skipped on re-run, so an interrupted session can be
resumed. The cells that convert the legacy encoding and repair tone marks were run once and are
not needed when starting from `data/split.csv`, which is already converted.

Training restorer weights (about 1.2 GB each) are not included. GPU training is not bit-for-bit
deterministic, so retrained models will give slightly different numbers; the paper reports means
and standard deviations over three seeds.

## Main results

English→Limbum test set, mean over three seeds. Tone accuracy is measured on reference words the
system translated correctly ("coverage", about 50% of reference words).

| System | chrF++ (toned) | chrF++ (toneless) | Tone acc. | Fixed-pattern words | Contested words |
|---|---|---|---|---|---|
| Direct | 44.3 | 46.2 | 94.7 | 98.5 | 88.1 |
| Explicit tone tokens | 44.4 | 46.3 | 94.6 | 98.5 | 87.7 |
| Toneless + lexical restore | 41.1 | 47.0 | 86.0 | 98.2 | 64.2 |
| Toneless + ByT5 restore | 44.9 | 47.0 | 93.9 | 98.4 | 86.0 |
| Toneless + source-aware ByT5 | 44.9 | 47.0 | 94.0 | 98.4 | 86.1 |

## Data

The corpus pairs New Testament verses with the American Standard Version (English) and adds
sentences from a Limbum–English dictionary; it was first released with our earlier
Limbum→English work (Ntohsi et al., 2026, arXiv:2608.07629). Here the New Testament has been
converted from its legacy font encoding to Unicode; the conversion reproduces the published
Unicode text of Luke 11:2 letter for letter. See [`data/README.md`](data/README.md) for the
encoding table, the cleaning steps and the terms of use.

Machine-generated Limbum should not be used, for example in health or education materials,
without review by native speakers.

## Citation

```bibtex
@inproceedings{babalola2026tone,
  title     = {Tone Generation in an Unsupported Language: Evaluating English-to-Limbum Translation with {NLLB}-200},
  author    = {Babalola, Samuel and Ankeli, Oche David and Ntohsi, Samiratu},
  booktitle = {Proceedings of the 2026 AI for African Languages Conference},
  series    = {Proceedings of Machine Learning Research},
  publisher = {PMLR},
  year      = {2026}
}
```

## Licence

Code (`scripts/`, `notebooks/`) is released under the MIT licence (see `LICENSE`). The data and
model outputs are covered by the terms in [`data/README.md`](data/README.md).

This work was carried out at the Ruzivo Research Lab, African Leadership University.
