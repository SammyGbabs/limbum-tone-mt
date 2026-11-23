"""Convert Limbum text from the legacy 8-bit font encoding to Unicode.

In the legacy text, special letters and tone marks were typed as French accented
characters, with each tone glyph typed after the vowel it belongs to:

    legacy        Unicode                         role
    á, Á          ɛ, Ɛ                            vowel letter
    ú, Ú          ʉ, Ʉ                            vowel letter
    ñ, Ñ          ŋ, Ŋ                            consonant letter
    ï, Ï          i, I                            base for a following tone glyph
    è, ì          combining grave (U+0300)        low tone (after a vowel)
    ê, â, î, û    combining circumflex (U+0302)   falling tone (after a vowel)

The mapping reproduces the Unicode text of Luke 11:2 published on Omniglot letter
for letter. Tone glyphs that do not follow a vowel are left unchanged and counted.

Usage as a script:
    python scripts/legacy_to_unicode.py input.txt > output.txt
"""
import sys
import unicodedata as ud
from collections import Counter

GRAVE, CIRC = "̀", "̂"
TONE_GLYPH = {"è": GRAVE, "È": GRAVE, "ì": GRAVE, "Ì": GRAVE,
              "ê": CIRC, "Ê": CIRC, "â": CIRC, "Â": CIRC, "î": CIRC, "Î": CIRC, "û": CIRC, "Û": CIRC}
LETTER = {"á": "ɛ", "Á": "Ɛ", "ú": "ʉ", "Ú": "Ʉ", "ñ": "ŋ", "Ñ": "Ŋ", "ï": "i", "Ï": "I"}
VOWELS = set("aeiouɛʉAEIOUƐɄ")
QUOTES = {"“": '"', "”": '"', "‘": '"', "’": '"', "ʼ": "'"}   # curly quotes are <unk> for NLLB-200

stats = Counter()


def legacy_to_unicode(s):
    out = []
    for ch in s:
        if ch in TONE_GLYPH:
            j = len(out) - 1
            while j >= 0 and ud.category(out[j]) == "Mn":     # skip marks already on the vowel
                j -= 1
            if j >= 0 and out[j] in VOWELS:
                out.append(TONE_GLYPH[ch])
                stats["tone_attached"] += 1
                continue
            stats["tone_unattached"] += 1
            out.append(ch)
        else:
            out.append(LETTER.get(ch, ch))
    return ud.normalize("NFC", "".join(out))


def norm_quotes(s):
    return "".join(QUOTES.get(c, c) for c in s)


if __name__ == "__main__":
    src = open(sys.argv[1], encoding="utf-8") if len(sys.argv) > 1 else sys.stdin
    for line in src:
        print(norm_quotes(legacy_to_unicode(line.rstrip("\n"))))
    print(dict(stats), file=sys.stderr)
