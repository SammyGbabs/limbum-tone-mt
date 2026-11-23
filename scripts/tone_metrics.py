"""Tone-aware evaluation used in the paper (identical to the notebook's metric code).

* chrF++ on toned text (chrfT) and on tone-stripped text (chrfS); Delta = chrfS - chrfT.
* Word-level tone accuracy: hypothesis and reference words are aligned by their
  tone-stripped forms (longest matching blocks); TAcc is the share of aligned words whose
  toned forms match. TAccM restricts to reference words carrying a tone mark,
  TAccAmb to contested words, TAccUnamb to fixed-pattern words. Coverage is the share of
  reference words that could be aligned (tone can only be scored on those words).
* "Contested" (called "amb" in code): a word type whose second most frequent toned
  spelling in the training targets has >= 10% of its occurrences and >= 3 occurrences.
"""
import difflib
import re
import unicodedata as ud
from collections import Counter, defaultdict

from sacrebleu.metrics import BLEU, CHRF

TONE = {"̀", "̂", "̌"}        # low (grave), falling (circumflex), rising (caron)
PUNCT = '.,;:!?"“”‘«»()[]{}…—–-'          # apostrophes ' and ’ are letters in Limbum orthography
SENT_END = set(".!?;:")
AFFIX_RE = re.compile(rf"^([{re.escape(PUNCT)}]*)(.*?)([{re.escape(PUNCT)}]*)$", re.S)

CHRF_M = CHRF(word_order=2)
BLEU_M = BLEU()


def nfc(s):
    return ud.normalize("NFC", s)


def nfd(s):
    return ud.normalize("NFD", s)


def strip_tones(s):
    """Remove tone marks only; keep base letters and non-tone diacritics."""
    return nfc("".join(ch for ch in nfd(s) if ch not in TONE))


def count_marks(s):
    return sum(1 for ch in nfd(s) if ch in TONE)


def split_affix(token):
    m = AFFIX_RE.match(token)
    return m.group(1), m.group(2), m.group(3)


def word_items(s):
    """[(core_word, is_phrase_final)]; punctuation stripped from word edges only."""
    out = []
    for t in s.split():
        pre, core, post = split_affix(t)
        if core:
            out.append([core, any(c in SENT_END for c in post)])
        elif out and any(c in SENT_END for c in t):
            out[-1][1] = True
    if out:
        out[-1][1] = True
    return [(w, f) for w, f in out]


def key(w):
    return strip_tones(w).lower()


def load_lines(path):
    with open(path, encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


def chrf(h, r):
    return CHRF_M.corpus_score(h, [r]).score


class Lexicon:
    """Toned spellings of each word type in the training targets (no test leakage)."""

    def __init__(self, train_targets, min_share=0.10, min_count=3):
        self.lex = defaultdict(Counter)
        for s in train_targets:
            for w, _ in word_items(s):
                self.lex[key(w)][nfc(w).lower()] += 1
        self.seen = set(self.lex)

        def contested(c):
            if len(c) < 2:
                return False
            second = c.most_common(2)[1][1]
            return second >= min_count and second / sum(c.values()) >= min_share

        self.contested = {k for k, c in self.lex.items() if contested(c)}

    def restore(self, text):
        """Lexical restorer: most frequent toned spelling of each word."""
        out = []
        for t in strip_tones(text).split():
            pre, core, post = split_affix(t)
            k = key(core)
            if core and k in self.lex:
                toned = self.lex[k].most_common(1)[0][0]
                core = toned[:1].upper() + toned[1:] if core[:1].isupper() else toned
            out.append(pre + core + post)
        return " ".join(out)


def tone_eval(hyps, refs, lexicon, per_sentence=False):
    C = Counter()
    sent = []
    for h, r in zip(hyps, refs):
        hi, ri = word_items(nfc(h)), word_items(nfc(r))
        hk, rk = [key(w) for w, _ in hi], [key(w) for w, _ in ri]
        sm = difflib.SequenceMatcher(None, hk, rk, autojunk=False)
        s = Counter(ref=len(ri))
        for a, b, n in sm.get_matching_blocks():
            for k in range(n):
                hw, (rw, fin) = hi[a + k][0], ri[b + k]
                ok = nfc(hw).lower() == nfc(rw).lower()
                kk = rk[b + k]
                cats = ["all", "final" if fin else "nonfinal",
                        "oov" if kk not in lexicon.seen else ("amb" if kk in lexicon.contested else "unamb")]
                if count_marks(rw) > 0:
                    cats.append("marked")
                for c in cats:
                    s[f"m_{c}"] += 1
                    s[f"c_{c}"] += ok
        s["hyp_marks"] = sum(count_marks(w) for w, _ in hi)
        s["ref_marks"] = sum(count_marks(w) for w, _ in ri)
        C.update(s)
        sent.append(s)

    def pct(a, b):
        return 100 * a / b if b else float("nan")

    out = dict(TAcc=pct(C["c_all"], C["m_all"]), TAccM=pct(C["c_marked"], C["m_marked"]),
               TAccAmb=pct(C["c_amb"], C["m_amb"]), TAccUnamb=pct(C["c_unamb"], C["m_unamb"]),
               TAccOOV=pct(C["c_oov"], C["m_oov"]), TAccFinal=pct(C["c_final"], C["m_final"]),
               TAccNonfinal=pct(C["c_nonfinal"], C["m_nonfinal"]), Coverage=pct(C["m_all"], C["ref"]),
               MarkRatio=C["hyp_marks"] / C["ref_marks"] if C["ref_marks"] else float("nan"),
               N_all=C["m_all"], N_marked=C["m_marked"], N_amb=C["m_amb"], N_unamb=C["m_unamb"],
               N_oov=C["m_oov"], N_final=C["m_final"], N_nonfinal=C["m_nonfinal"])
    return (out, sent) if per_sentence else out


def full_eval(hyps, refs, lexicon):
    hs, rs = [strip_tones(h) for h in hyps], [strip_tones(r) for r in refs]
    m = dict(chrfT=chrf(hyps, refs), chrfS=chrf(hs, rs), bleuT=BLEU_M.corpus_score(hyps, [refs]).score)
    m["Delta"] = m["chrfS"] - m["chrfT"]
    m.update(tone_eval(hyps, refs, lexicon))
    return m
