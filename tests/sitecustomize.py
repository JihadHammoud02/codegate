"""Test-time sitecustomize.

Python automatically imports `sitecustomize` on startup if it is importable.

We use this to enable coverage collection in subprocesses spawned by tests
(e.g., the CLI end-to-end test).

This is safe because it's only picked up when `tests/` is on PYTHONPATH.
"""

from __future__ import annotations

import os


def _maybe_enable_coverage() -> None:
    # If coverage isn't installed or the env isn't configured, do nothing.
    try:
        import coverage  # noqa: F401
    except Exception:
        return

    # Don't double-start.
    if os.environ.get("COVERAGE_PROCESS_START"):
        try:
            import coverage

            coverage.process_startup()
        except Exception:
            return


_maybe_enable_coverage()
