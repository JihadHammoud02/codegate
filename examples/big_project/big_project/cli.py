"""Small CLI-style entrypoint for the big example project."""

from __future__ import annotations

import argparse

from big_project.text.analyze import top_words
from big_project.math.stats import mean


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Big Project CLI")
    parser.add_argument("text", type=str, help="Text to analyze")
    args = parser.parse_args(argv)

    words = top_words(args.text, n=3)
    lengths = [len(w) for w, _count in words]

    print(f"Top words: {words}")
    print(f"Mean word length (top 3): {mean(lengths):.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
