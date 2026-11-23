# Results

All files are produced by the notebook and reproduced exactly by `python scripts/evaluate.py`.

| File | Contents |
|---|---|
| `results_per_seed.csv` | All metrics for every system and seed (`Strip` = Toneless; `TAccAmb` = contested words, `TAccUnamb` = fixed-pattern words) |
| `significance_vs_direct.csv` | Paired bootstrap (1,000 resamples) of each system against Direct; `p_*` is the share of resamples with no gain |
| `legacy_vs_unicode_per_seed.csv` | Models trained on legacy vs. Unicode text, scored on the same Unicode references |
| `legacy_vs_unicode_significance.csv` | Paired bootstrap, Unicode-trained minus legacy-trained |
| `ambiguous_word_errors.csv` | Every tone error on a contested word, per system (seed 1), with the training spellings |
