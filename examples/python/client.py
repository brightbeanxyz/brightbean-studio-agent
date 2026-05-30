"""Tiny Brightbean Studio Agent API client used by the example scripts.

Pulls the two pieces of config every example needs from environment vars:

* ``BRIGHTBEAN_BASE_URL`` — e.g. ``https://studio.example.com`` (no trailing
  slash, no ``/api/v1``)
* ``BRIGHTBEAN_TOKEN`` — the ``bb_studio_...`` bearer

The class is intentionally minimal — a single ``Session`` with the
``Authorization`` header set, plus a couple of shortcuts. Real apps
should add retry/backoff (the ``05_idempotent_retry.py`` example shows
the pattern).
"""

from __future__ import annotations

import os
import sys
from typing import Any

import requests


class BrightbeanClient:
    def __init__(self, base_url: str | None = None, token: str | None = None):
        self.base_url = (base_url or os.environ.get("BRIGHTBEAN_BASE_URL", "")).rstrip("/")
        self.token = token or os.environ.get("BRIGHTBEAN_TOKEN", "")
        if not self.base_url or not self.token:
            sys.exit(
                "Set BRIGHTBEAN_BASE_URL and BRIGHTBEAN_TOKEN before running the "
                "examples. See ../../README.md."
            )
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        })

    def _url(self, path: str) -> str:
        return f"{self.base_url}/api/v1{path}"

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.session.get(self._url(path), timeout=10, **kwargs)

    def post(self, path: str, json_body: dict[str, Any], **kwargs) -> requests.Response:
        return self.session.post(self._url(path), json=json_body, timeout=10, **kwargs)

    def patch(self, path: str, json_body: dict[str, Any], **kwargs) -> requests.Response:
        return self.session.patch(self._url(path), json=json_body, timeout=10, **kwargs)
