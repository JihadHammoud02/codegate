"""Simple math/statistics helpers."""

from __future__ import annotations

from typing import Iterable


def mean(values: Iterable[float]) -> float:
    values = list(values)
    if not values:
        raise ValueError("mean of empty sequence")
    return sum(values) / len(values)


def variance(values: Iterable[float]) -> float:
    values = list(values)
    m = mean(values)
    return sum((x - m) ** 2 for x in values) / len(values)
