"""Text tokenization utilities."""

from __future__ import annotations

import re
from typing import List

_WORD_RE = re.compile(r"[A-Za-z0-9']+")


def tokenize(text: str) -> List[str]:
    """Lowercase tokenize into simple word tokens."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    return [m.group(0).lower() for m in _WORD_RE.finditer(text)]
