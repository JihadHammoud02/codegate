"""Text analysis helpers."""

from __future__ import annotations

from collections import Counter
from typing import List, Tuple

from big_project.text.tokenize import tokenize


def top_words(text: str, n: int = 5) -> List[Tuple[str, int]]:
    """Return the n most common words in the given text."""
    if n <= 0:
        return []

    counts = Counter(tokenize(text))
    return counts.most_common(n)
