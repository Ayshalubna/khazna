"""Detect and mask personal data (UAE formats) before anything is shown to a user.

Masking is applied at two points (defence in depth): to every passage shown as a source, and to every
generated answer. Identifiers that no chat user needs (Emirates ID, IBAN, card, passport numbers) are always
masked; phone numbers and personal e-mail addresses are visible only to roles that need them for their work.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

PATTERNS = {
    "emirates_id": re.compile(r"\b784[-\s]?\d{4}[-\s]?\d{7}[-\s]?\d\b"),
    "iban": re.compile(r"\bAE\s?\d{2}(?:\s?\d){19}\b", re.I),
    "card": re.compile(r"\b(?:\d[ -]?){13,19}\b"),
    "passport": re.compile(r"\b(?:passport(?: no\.?| number)?:?\s*)([A-Z]\d{7,8})\b", re.I),
    "phone": re.compile(r"(?:\+971|00971|\b0)\s?5\d[\s-]?\d{3}[\s-]?\d{4}\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
}
LABEL = {"emirates_id": "EMIRATES ID", "iban": "IBAN", "card": "CARD NUMBER", "passport": "PASSPORT",
         "phone": "PHONE", "email": "EMAIL"}
ALWAYS = {"emirates_id", "iban", "card", "passport"}
CONTACT_ROLES = {"it", "executive"}          # may see personal phone numbers / e-mails
SHARED_MAILBOX = re.compile(r"^(hr|hr\.desk|security|dpo|ethics|info|support|procurement|careers|finance|legal|it)@", re.I)


def _luhn_ok(digits: str) -> bool:
    d = [int(c) for c in digits if c.isdigit()]
    if not 13 <= len(d) <= 19:
        return False
    s = 0
    for i, v in enumerate(reversed(d)):
        if i % 2:
            v *= 2
            if v > 9:
                v -= 9
        s += v
    return s % 10 == 0


@dataclass
class Finding:
    kind: str
    start: int
    end: int


def find(text: str) -> list[Finding]:
    out: list[Finding] = []
    taken: list[tuple[int, int]] = []

    def free(a, b):
        return all(b <= x or a >= y for x, y in taken)

    for kind in ("emirates_id", "iban", "passport", "phone", "email", "card"):
        for m in PATTERNS[kind].finditer(text):
            a, b = (m.start(1), m.end(1)) if kind == "passport" else (m.start(), m.end())
            if kind == "card" and not _luhn_ok(m.group()):
                continue
            if kind == "email" and SHARED_MAILBOX.match(m.group()):
                continue          # shared team mailboxes are business contacts, not personal data
            if free(a, b):
                out.append(Finding(kind, a, b))
                taken.append((a, b))
    return sorted(out, key=lambda f: f.start)


CONTACT_DOCS = {"runbook"}                   # operational documents where on-call contacts are needed


def redact(text: str, role: str = "employee", contacts_ok: bool = False) -> tuple[str, dict]:
    """Return the masked text and a count of what was masked. Personal phone numbers and e-mails are shown only
    to roles that need them, and only from operational documents (never from HR records)."""
    counts: dict[str, int] = {}
    pieces, last = [], 0
    for f in find(text):
        if f.kind not in ALWAYS and role in CONTACT_ROLES and contacts_ok:
            continue
        pieces.append(text[last:f.start])
        pieces.append(f"[{LABEL[f.kind]} HIDDEN]")
        last = f.end
        counts[f.kind] = counts.get(f.kind, 0) + 1
    pieces.append(text[last:])
    return "".join(pieces), counts


def summary(text: str) -> dict:
    counts: dict[str, int] = {}
    for f in find(text):
        counts[f.kind] = counts.get(f.kind, 0) + 1
    return counts
