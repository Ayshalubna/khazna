"""Two guards that make "private by design" checkable rather than a promise.

1. Prompt-injection guard: text inside documents is data, never instructions. Sentences that try to instruct an
   AI ("ignore previous instructions", "tell the user...") are detected, removed from what the model reads, and
   flagged to the user.
2. Egress guard: once the app has started, any attempt to open a network connection to a host outside the
   container is refused and counted. Documents and questions physically cannot be sent to an outside service.
"""
from __future__ import annotations

import ipaddress
import re
import socket
import threading

from .text import normalise_ar, sentences

INJECTION = re.compile(
    r"(ignore|disregard|forget|override)\s+(all\s+|any\s+|the\s+)?(previous|prior|above|earlier|your)\s+"
    r"(instructions|rules|prompts?|guidelines)"
    r"|note\s+to\s+(any\s+)?(ai|assistant|language model|llm|chatbot)"
    r"|(you are now|act as|pretend to be|new instructions:|system prompt)"
    r"|(reveal|include|print|show)\s+(the\s+|all\s+|every\s+|full\s+)*(salary|iban|password|system prompt|secret)"
    r"|تجاهل\s+(جميع\s+|كل\s+)?التعليمات|انت الان|تعليمات جديدة",
    re.I,
)


def is_injection(text: str) -> bool:
    return bool(INJECTION.search(normalise_ar(text)))


def sanitise(text: str) -> tuple[str, int]:
    """Drop sentences that look like instructions to an AI, keeping the line structure.
    Returns (clean text, number removed)."""
    lines, removed = [], 0
    for line in text.splitlines():
        if not is_injection(line):
            lines.append(line)
            continue
        kept = []
        for s in sentences(line):
            if is_injection(s):
                removed += 1
            else:
                kept.append(s)
        if kept:
            lines.append(" ".join(kept))
    return "\n".join(lines), removed


# ------------------------------------------------------------------------------------------- egress
class EgressGuard:
    def __init__(self):
        self.enabled = False
        self.blocked: list[str] = []
        self.lock = threading.Lock()
        self._orig = socket.socket.connect
        self._orig_ex = socket.socket.connect_ex

    @staticmethod
    def _local(addr) -> bool:
        host = addr[0] if isinstance(addr, tuple) else str(addr)
        if isinstance(host, bytes):
            host = host.decode()
        if host in ("localhost", "") or str(host).startswith("/"):
            return True
        try:
            ip = ipaddress.ip_address(host)
            return ip.is_loopback or ip.is_private or ip.is_link_local
        except ValueError:
            return False

    def enable(self) -> None:
        if self.enabled:
            return
        guard = self

        def connect(sock, addr):
            if sock.family in (socket.AF_INET, socket.AF_INET6) and not guard._local(addr):
                with guard.lock:
                    guard.blocked.append(str(addr[0]) if isinstance(addr, tuple) else str(addr))
                raise ConnectionRefusedError("Khazna egress guard: outbound connections are disabled")
            return guard._orig(sock, addr)

        def connect_ex(sock, addr):
            try:
                connect(sock, addr)
                return 0
            except ConnectionRefusedError:
                return 111

        socket.socket.connect = connect
        socket.socket.connect_ex = connect_ex
        self.enabled = True

    def disable(self) -> None:
        socket.socket.connect = self._orig
        socket.socket.connect_ex = self._orig_ex
        self.enabled = False

    def status(self) -> dict:
        with self.lock:
            return {"enabled": self.enabled, "blocked_attempts": len(self.blocked), "last_blocked": self.blocked[-5:]}


EGRESS = EgressGuard()
