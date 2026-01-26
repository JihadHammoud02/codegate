"""Tiny HTTP wrapper to exercise 'requests' dependency for security_deps."""

from __future__ import annotations

from typing import Any, Dict, Optional

import requests


def fetch_json(url: str, timeout: float = 2.0, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Fetch JSON from a URL.

    In the CodeGate contract, network access is typically disabled, so this is mostly here
    as an example of code that *would* need network in production.
    """
    resp = requests.get(url, timeout=timeout, headers=headers)
    resp.raise_for_status()
    return resp.json()
