# Native-speaker evaluation

`Limbum_tone_evaluation_annotated.xlsx` holds the evaluation as completed by a native-speaker
author: 100 test sentences containing contested words, each with two outputs shown in random
order without system labels (A/B). For each output the annotator counted tone errors and marked
whether a tone error changes the meaning, then gave an overall preference. The `Questions` sheet
holds questions about Limbum tone used in the error analysis.

`assignment_key.csv` maps each item to the systems behind A and B (`test_index` is the row
in the test split). It was not shown to the annotator. The systems are Direct (seed 1) and
Toneless + source-aware ByT5 restoration (seed 1).

`python scripts/evaluate.py` unblinds and summarises the evaluation:

| | Tone errors | Sentences with an error | ...that change meaning | Preferred |
|---|---|---|---|---|
| Direct | 13 | 12 | 10 | 47 |
| Restoration | 10 | 9 | 6 | 51 |

(2 ties; sign test p = 0.76.) The same 100 sentences contain 62 (Direct) and 72 (restoration)
automatic tone mismatches against the single reference.
