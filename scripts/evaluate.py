"""Recompute every reported result from the released model outputs (CPU only, a few minutes).

Writes to results/reproduced/ and compares with the released result files:
  results_per_seed.csv               all systems x 3 seeds (Tables 3 and 5, Figure 2)
  significance_vs_direct.csv         paired bootstrap vs Direct
  oracle_restoration.csv             restorers on gold toneless references (Table 4)
  legacy_vs_unicode_per_seed.csv     legacy- vs Unicode-trained models (Table 6)
  legacy_vs_unicode_significance.csv
  human_eval_summary.csv             native-speaker evaluation, unblinded

Usage:
    python scripts/evaluate.py            # full run (1,000 bootstrap resamples)
    python scripts/evaluate.py --quick    # skip bootstrap tests
"""
import argparse
import os
import re
import sys
import unicodedata as ud

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from legacy_to_unicode import legacy_to_unicode, norm_quotes  # noqa: E402
from tone_metrics import CHRF_M, Lexicon, chrf, full_eval, load_lines, strip_tones, tone_eval  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNI = os.path.join(ROOT, "outputs", "unicode")
LEG = os.path.join(ROOT, "outputs", "legacy")
OUT = os.path.join(ROOT, "results", "reproduced")
SEEDS = [1, 2, 3]
LABEL = {"Direct": "Direct", "Explicit": "Explicit tone tokens", "Strip": "Toneless, no restoration",
         "StripLex": "Toneless + lexical restore", "StripByT": "Toneless + ByT5 restore",
         "StripByTSrc": "Toneless + source-aware ByT5"}


def boot_vs(hA, hB, refs, lexicon, n, seed, with_contested=False):
    """Paired bootstrap over test sentences: B minus A for chrF++ and tone accuracy."""
    rng = np.random.default_rng(seed)
    N = len(refs)
    sa = np.array(CHRF_M._extract_corpus_statistics(hA, [refs]))
    sb = np.array(CHRF_M._extract_corpus_statistics(hB, [refs]))
    _, ta = tone_eval(hA, refs, lexicon, per_sentence=True)
    _, tb = tone_eval(hB, refs, lexicon, per_sentence=True)

    def get(T, c, m):
        return np.array([[t[c], t[m]] for t in T], float)

    pairs = {"TAcc": (get(ta, "c_all", "m_all"), get(tb, "c_all", "m_all"))}
    if with_contested:
        pairs["TAccAmb"] = (get(ta, "c_amb", "m_amb"), get(tb, "c_amb", "m_amb"))
    d = {"chrfT": [], **{k: [] for k in pairs}}
    for _ in range(n):
        i = rng.integers(0, N, N)
        d["chrfT"].append(CHRF_M._compute_score_from_stats(sb[i].sum(0).tolist()).score
                          - CHRF_M._compute_score_from_stats(sa[i].sum(0).tolist()).score)
        for k, (A, B) in pairs.items():
            a, b = A[i].sum(0), B[i].sum(0)
            d[k].append(100 * (b[0] / b[1] - a[0] / a[1]))
    res = {}
    for k, v in d.items():
        v = np.array(v)
        res[f"d_{k}"] = float(v.mean())
        res[f"p_{k}"] = float((v <= 0).mean())
    return res


def convert_legacy_output(s):
    """Same mapping as the data, plus the tone-mark repair."""
    tm = "̀̂̌"
    d = ud.normalize("NFD", norm_quotes(legacy_to_unicode(s)))
    d = re.sub(rf"([mnŋMNŊ]) ([{tm}])", r"\1\2", d)
    d = re.sub(rf"([{tm}])\1+", r"\1", d)
    d = re.sub(rf"(^|\s)[{tm}]+", r"\1", d)
    return ud.normalize("NFC", re.sub(r"\s+", " ", d).strip())


def compare(name, new, ref_path, key_cols, tol=1e-6):
    if not os.path.exists(ref_path):
        return
    ref = pd.read_csv(ref_path)
    num = [c for c in new.columns if c in ref.columns and c not in key_cols
           and pd.api.types.is_numeric_dtype(new[c]) and pd.api.types.is_numeric_dtype(ref[c])]
    m = new.merge(ref, on=key_cols, suffixes=("", "_ref"))
    diff = max((m[c] - m[c + "_ref"]).abs().max() for c in num) if len(m) else float("nan")
    ok = len(m) == len(ref) and diff < tol
    print(f"  {name}: {len(m)}/{len(ref)} rows matched, max abs difference {diff:.2e} -> "
          f"{'REPRODUCED' if ok else 'CHECK'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="skip bootstrap tests")
    ap.add_argument("--bootstrap", type=int, default=1000)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    data = pd.read_csv(os.path.join(ROOT, "data", "split.csv"), dtype=str)
    train, test = data[data.split == "train"], data[data.split == "test"]
    refs, engs = list(test.lmp), list(test.eng)
    lexicon = Lexicon(train.lmp)
    print(f"Test set: {len(refs)} sentences; {len(lexicon.contested)} contested word types")

    # ---- system outputs ----
    hyps = {k: {} for k in LABEL}
    for s in SEEDS:
        for sysname, folder in [("Direct", "direct"), ("Explicit", "explicit"), ("Strip", "stripped")]:
            hyps[sysname][s] = load_lines(os.path.join(UNI, "runs", f"{folder}_seed{s}", "test_hyp.txt"))
        hyps["StripLex"][s] = [lexicon.restore(h) for h in hyps["Strip"][s]]
        for sysname, r in [("StripByT", "byt5_seed1"), ("StripByTSrc", "byt5_src_seed1")]:
            hyps[sysname][s] = load_lines(os.path.join(UNI, "restorers", r, f"on_stripped_seed{s}.txt"))

    rows = [dict(system=k, seed=s, **full_eval(h, refs, lexicon)) for k, per in hyps.items() for s, h in per.items()]
    per_seed = pd.DataFrame(rows)
    per_seed.to_csv(os.path.join(OUT, "results_per_seed.csv"), index=False)

    cols = ["chrfT", "chrfS", "Delta", "bleuT", "TAcc", "TAccM", "TAccAmb", "TAccUnamb",
            "TAccNonfinal", "TAccFinal", "MarkRatio", "Coverage"]
    agg = per_seed.groupby("system")[cols].agg(["mean", "std"]).reindex(list(LABEL))
    pd.set_option("display.width", 200)
    print("\nMain results (mean over 3 seeds):")
    print(agg.xs("mean", axis=1, level=1).rename(index=LABEL).round(2).to_string())

    # ---- oracle restoration ----
    gold_toneless = [strip_tones(r) for r in refs]
    oracle = {"Lexical": [lexicon.restore(x) for x in gold_toneless],
              "ByT5": load_lines(os.path.join(UNI, "restorers", "byt5_seed1", "oracle_hyp.txt")),
              "Source-aware ByT5": load_lines(os.path.join(UNI, "restorers", "byt5_src_seed1", "oracle_hyp.txt"))}
    orc = pd.DataFrame([dict(restorer=k, **full_eval(h, refs, lexicon)) for k, h in oracle.items()])
    orc.to_csv(os.path.join(OUT, "oracle_restoration.csv"), index=False)
    print("\nOracle restoration (gold toneless input):")
    print(orc.set_index("restorer")[["TAcc", "TAccM", "TAccAmb", "chrfT"]].round(1).to_string())

    # ---- legacy vs Unicode ----
    leg_rows, leg_sig = [], []
    for system in ["direct", "explicit"]:
        for s in SEEDS:
            hl = [convert_legacy_output(x) for x in load_lines(os.path.join(LEG, "runs", f"{system}_seed{s}", "test_hyp.txt"))]
            hu = load_lines(os.path.join(UNI, "runs", f"{system}_seed{s}", "test_hyp.txt"))
            for name, h in [("legacy-trained", hl), ("unicode-trained", hu)]:
                m = full_eval(h, refs, lexicon)
                nq = [re.sub(r"\s+", " ", x.replace('"', " ")).strip() for x in h]
                m["chrfT_noquotes"] = chrf(nq, [re.sub(r"\s+", " ", x.replace('"', " ")).strip() for x in refs])
                leg_rows.append(dict(system=system, training_text=name, seed=s, **m))
            if not a.quick:
                leg_sig.append(dict(system=system, seed=s, **boot_vs(hl, hu, refs, lexicon, a.bootstrap, s, True)))
    leg = pd.DataFrame(leg_rows)
    leg.to_csv(os.path.join(OUT, "legacy_vs_unicode_per_seed.csv"), index=False)

    # ---- significance vs Direct ----
    if not a.quick:
        sig = [dict(system=k, seed=s, **boot_vs(hyps["Direct"][s], hyps[k][s], refs, lexicon, a.bootstrap, s))
               for k in LABEL if k != "Direct" for s in SEEDS]
        pd.DataFrame(sig).to_csv(os.path.join(OUT, "significance_vs_direct.csv"), index=False)
        pd.DataFrame(leg_sig).to_csv(os.path.join(OUT, "legacy_vs_unicode_significance.csv"), index=False)

    # ---- human evaluation ----
    he_path = os.path.join(ROOT, "human_eval", "Limbum_tone_evaluation_annotated.xlsx")
    if os.path.exists(he_path):
        ev = pd.read_excel(he_path, sheet_name="Evaluation")
        key = pd.read_csv(os.path.join(ROOT, "human_eval", "assignment_key.csv"))
        ev = ev.merge(key, on="Item")
        cnt = {"Direct": dict(errors=0, sentences=0, meaning=0), "Restore": dict(errors=0, sentences=0, meaning=0)}
        pref = {"Direct": 0, "Restore": 0, "tie": 0}
        for _, r in ev.iterrows():
            for side in "AB":
                sysname = "Direct" if r[side] == "Direct" else "Restore"
                e = int(pd.to_numeric(r[f"{side}: number of tone errors"], errors="coerce") or 0)
                mean = str(r[f"{side}: does a tone error change the meaning? (yes/no)"]).strip().lower()
                cnt[sysname]["errors"] += e
                cnt[sysname]["sentences"] += e > 0
                cnt[sysname]["meaning"] += mean == "yes"
            p = str(r["Which output is better? (A / B / same)"]).strip().upper()
            pref[("Direct" if r[p] == "Direct" else "Restore") if p in ("A", "B") else "tie"] += 1
        he = pd.DataFrame(cnt).T
        he["preferred"] = [pref["Direct"], pref["Restore"]]
        he.loc["tie", "preferred"] = pref["tie"]
        he.to_csv(os.path.join(OUT, "human_eval_summary.csv"))
        print("\nNative-speaker evaluation (100 sentences):")
        print(he.fillna("").to_string())

    # ---- comparison with released results ----
    R = os.path.join(ROOT, "results")
    print("\nComparison with released results:")
    compare("results_per_seed", per_seed, os.path.join(R, "results_per_seed.csv"), ["system", "seed"])
    compare("legacy_vs_unicode_per_seed", leg, os.path.join(R, "legacy_vs_unicode_per_seed.csv"),
            ["system", "training_text", "seed"])
    if not a.quick:
        compare("significance_vs_direct", pd.read_csv(os.path.join(OUT, "significance_vs_direct.csv")),
                os.path.join(R, "significance_vs_direct.csv"), ["system", "seed"])
        compare("legacy_vs_unicode_significance", pd.read_csv(os.path.join(OUT, "legacy_vs_unicode_significance.csv")),
                os.path.join(R, "legacy_vs_unicode_significance.csv"), ["system", "seed"])


if __name__ == "__main__":
    main()
