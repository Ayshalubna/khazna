"""Text normalisation and tokenisation for English and Arabic (no external models)."""
from __future__ import annotations

import re
import unicodedata

AR_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
AR_CHARS = re.compile(r"[؀-ۿ]")
TOKEN = re.compile(r"[A-Za-z]+\d+|[A-Za-z]+|[\u0621-\u064A]+|\d+(?:[.,]\d+)*%?")

EN_STOP = set("""a an and are as at be been by can could do does for from had has have how i if in is it its
me my of on or our shall should so than that the their them then there these they this to up was we were what when
where which who whom why will with would you your about any after all also am into more most no not only other out
over same some such very just get got per did done does someone anyone anybody far number tell show say says
give summarise summarize require requires required handle handles accept explain describe list please""".split())
AR_STOP = set("""في من على إلى الى عن مع هل ما ماذا متى متي كيف كم هو هي هذا هذه ذلك تلك التي الذي الذين أو او ثم قد كان بشأن بشان عدد
كانت يكون تكون لا لم لن إن ان أن عند كل بعد قبل بين أي اي هناك لدى لي له لها لهم نحن أنا انا يجب يمكن""".split())

PREFIXES = ("وال", "بال", "كال", "فال", "لل", "ال")
SUFFIXES = ("هما", "كما", "ات", "ون", "ين", "ها", "هم", "يه", "ه", "ي")


def normalise_ar(s: str) -> str:
    s = AR_DIACRITICS.sub("", s)
    s = re.sub("[إأآٱ]", "ا", s)
    s = s.replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي").replace("ة", "ه")
    return s


def is_arabic(s: str) -> bool:
    letters = [c for c in s if c.isalpha()]
    return bool(letters) and sum(1 for c in letters if AR_CHARS.match(c)) / len(letters) > 0.4


def stem_ar(w: str) -> str:
    """Very light Arabic stemmer: strip one common prefix and one suffix, keep >= 3 letters."""
    for p in PREFIXES:
        if w.startswith(p) and len(w) - len(p) >= 3:
            w = w[len(p):]
            break
    if w.startswith("و") and len(w) >= 5:
        w = w[1:]
    if w[:1] in ("ل", "ب", "ك", "ف") and len(w) >= 4 and not w.startswith(("لل",)):
        w = w[1:]
    for s in SUFFIXES:
        if w.endswith(s) and len(w) - len(s) >= 3:
            w = w[: -len(s)]
            break
    return w


def stem_en(w: str) -> str:
    for suf, rep in (("ies", "y"), ("ing", ""), ("ed", ""), ("es", ""), ("s", "")):
        if w.endswith(suf) and len(w) - len(suf) >= 3 and not w.endswith("ss"):
            return w[: -len(suf)] + rep
    return w


def tokens(s: str, stem: bool = True, stop: bool = True) -> list[str]:
    s = unicodedata.normalize("NFKC", s)
    s = normalise_ar(s).lower()
    out = []
    for t in TOKEN.findall(s):
        if t[0].isdigit():
            out.append(t.replace(",", ""))
            continue
        if AR_CHARS.match(t):
            if stop and t in AR_STOP:
                continue
            out.append(stem_ar(t) if stem else t)
        else:
            if stop and t in EN_STOP:
                continue
            out.append(stem_en(t) if stem else t)
    return out


SENT = re.compile(r"(?<=[.!?؟])\s+(?=[A-Z\u0600-\u06FF\d\"(])")
LIST_ITEM = re.compile(r"^\s*(?:[-•*]|\d+[.)])\s+")


def sentences(s: str) -> list[str]:
    """Sentences, keeping each list item whole (so "P1 Critical: ... Response within 15 minutes" stays together)."""
    out = []
    for line in s.splitlines():
        line = line.strip()
        if not line:
            continue
        if LIST_ITEM.match(line):
            out.append(LIST_ITEM.sub("", line))
        else:
            out.extend(x.strip() for x in SENT.split(line))
    return [x for x in out if len(x) > 2]
