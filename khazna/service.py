"""Process-wide Khazna instance."""
from __future__ import annotations

import threading

from .engine import Khazna

_INSTANCE: Khazna | None = None
_LOCK = threading.Lock()


def get() -> Khazna:
    global _INSTANCE
    if _INSTANCE is None:
        with _LOCK:
            if _INSTANCE is None:
                _INSTANCE = Khazna()
    return _INSTANCE
