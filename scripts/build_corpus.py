"""Rebuild data/split.csv from the raw Limbum--English files (CPU only, a few seconds).

Pipeline, exactly as run for the paper:
  1. Merge the New Testament (legacy font encoding) and the dictionary (Unicode).
  2. Normalise (NFC, whitespace), de-duplicate, and split: the New Testament into
     20 contiguous verse blocks (16 train / 2 dev / 2 test), the dictionary 80/10/10 (seed 0).
  3. Convert the New Testament from the legacy font encoding to Unicode and replace
     curly quotation marks with ASCII ones (legacy_to_unicode.py).
  4. Exclude New Testament verses that mix legacy glyphs with real Unicode accented letters.
  5. Repair stranded or duplicated tone marks.

Usage:
    python scripts/build_corpus.py                 # writes to data/rebuilt/
    python scripts/build_corpus.py --check         # also compares with data/split.csv
"""
import argparse
import os
import random
import re
import sys
import unicodedata as ud

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from legacy_to_unicode import legacy_to_unicode, norm_quotes  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TONE_MARKS = "̀̂̌"            # low (grave), falling (circumflex), rising (caron)
SUSPECT = set("àòùéíóÀÒÙÉÍÓ")                # never produced by the legacy font


def nfc(s):
    return ud.normalize("NFC", s)


def clean_ws(s):
    return re.sub(r"\s+", " ", s).strip()


# ---------- 1. merge ----------
def merge(nt_path, dict_path):
    nt = pd.read_csv(nt_path).rename(columns={"Limbum": "lmp", "English": "eng"})
    dic = pd.read_csv(dict_path).rename(columns={"Limbum": "lmp", "English": "eng"})
    dic = dic.drop(columns=[c for c in dic.columns if "len" in c.lower()])
    nt["source"] = "nt"
    dic["source"] = "dict"
    merged = pd.concat([nt, dic], ignore_index=True).reindex(columns=["lmp", "eng", "source"])
    return merged.dropna(subset=["lmp", "eng"]).astype(str)


# ---------- 2. normalise and split ----------
def load_corpus(df):
    df = df.copy()
    df["lmp"] = df["lmp"].map(lambda s: clean_ws(nfc(s)))
    df["eng"] = df["eng"].map(lambda s: clean_ws(nfc(s)))
    df["source"] = df["source"].str.lower().str.strip().map(lambda s: "dict" if s.startswith("dic") else "nt")
    df = df[(df.lmp.str.len() > 0) & (df.eng.str.len() > 0)]
    return df.drop_duplicates(subset=["lmp", "eng"]).reset_index(drop=True)


def make_split(df):
    rng = random.Random(0)
    split = pd.Series("train", index=df.index)
    nt = df[df.source == "nt"]
    blocks = np.array_split(np.array(nt.index), 20)
    order = list(range(20))
    rng.shuffle(order)
    for j, bi in enumerate(order):
        if j < 2:
            split[blocks[bi]] = "test"
        elif j < 4:
            split[blocks[bi]] = "dev"
    di = list(df[df.source == "dict"].index)
    rng.shuffle(di)
    n = len(di)
    split[di[: int(0.1 * n)]] = "test"
    split[di[int(0.1 * n): int(0.2 * n)]] = "dev"
    return df.assign(split=split.values)


# ---------- 5. tone-mark repair ----------
def fix_marks(s):
    d = ud.normalize("NFD", s)
    d = re.sub(rf"([mnŋMNŊ]) ([{TONE_MARKS}])", r"\1\2", d)   # "M ̀" -> "M̀" (tone on syllabic nasal)
    d = re.sub(rf"([{TONE_MARKS}])\1+", r"\1", d)             # duplicated marks
    d = re.sub(rf"(^|\s)[{TONE_MARKS}]+", r"\1", d)           # any other stranded marks
    return ud.normalize("NFC", re.sub(r"\s+", " ", d).strip())


def build(nt_path, dict_path):
    legacy = make_split(load_corpus(merge(nt_path, dict_path)))

    # 3. convert the New Testament and normalise quotes everywhere
    uni = legacy.copy()
    is_nt = uni.source == "nt"
    uni.loc[is_nt, "lmp"] = uni.loc[is_nt, "lmp"].map(legacy_to_unicode)
    uni["lmp"] = uni["lmp"].map(lambda s: ud.normalize("NFC", norm_quotes(s)))
    uni["eng"] = uni["eng"].map(norm_quotes)

    # 4. exclude verses that mix encodings (detected on the legacy text)
    bad = (legacy.source == "nt") & legacy.lmp.map(lambda s: any(c in SUSPECT for c in s))
    excluded, kept = uni[bad].reset_index(drop=True), uni[~bad].reset_index(drop=True)

    # 5. repair stranded / duplicated tone marks
    kept["lmp"] = kept["lmp"].map(fix_marks)
    return kept, excluded, legacy


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nt", default=os.path.join(ROOT, "data/raw/nt_legacy_encoding.csv"))
    ap.add_argument("--dict", default=os.path.join(ROOT, "data/raw/dictionary.csv"))
    ap.add_argument("--out", default=os.path.join(ROOT, "data/rebuilt"))
    ap.add_argument("--check", action="store_true", help="compare with the released data/split.csv")
    a = ap.parse_args()

    kept, excluded, legacy = build(a.nt, a.dict)
    os.makedirs(a.out, exist_ok=True)
    kept.to_csv(os.path.join(a.out, "split.csv"), index=False)
    excluded.to_csv(os.path.join(a.out, "excluded_mixed_encoding.csv"), index=False)
    legacy.to_csv(os.path.join(a.out, "split_legacy_encoding.csv"), index=False)
    print(f"{len(kept)} pairs kept, {len(excluded)} mixed-encoding verses excluded -> {a.out}")
    print(kept.groupby(["split", "source"]).size().unstack(fill_value=0))

    if a.check:
        ref = pd.read_csv(os.path.join(ROOT, "data/split.csv"), dtype=str)
        same = ref.reset_index(drop=True).equals(kept.astype(str).reset_index(drop=True))
        print("Identical to data/split.csv:", same)
        sys.exit(0 if same else 1)


if __name__ == "__main__":
    main()
