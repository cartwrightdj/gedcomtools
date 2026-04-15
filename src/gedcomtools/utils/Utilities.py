"""
======================================================================
 Project: gedcomtools
 File:    utils/Utilities.py
 Author:  David J. Cartwright
 Purpose: Utility functions including dynamic enum combination helper

 Created: 2025-07-01
 Updated: 2026-04-03 — added _is_url / _check_ged_url shared helpers
 Updated: 2026-04-10 — added shared bounded URL download helper with
                       timeout and response-size limits for public loaders
 Updated: 2026-04-12 — fixed backwards ValueError re-raise in download_url_bytes();
                       non-numeric Content-Length headers are now silently ignored
                       instead of being swallowed by the wrong except branch
 Updated: 2026-04-15 — release refresh for v0.7.5b1 docs/build packaging

======================================================================
"""
from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from enum import Enum
from pathlib import Path

DEFAULT_DOWNLOAD_TIMEOUT = 20
DEFAULT_DOWNLOAD_MAX_BYTES = 64 * 1024 * 1024

def _is_url(s: str) -> bool:
    """Return True if *s* looks like an HTTP/HTTPS URL."""
    return s.startswith(("http://", "https://"))


def _check_ged_url(url: str) -> None:
    """Raise :class:`ValueError` if the URL path does not end in ``.ged``."""
    path = urllib.parse.urlparse(url).path
    if Path(path).suffix.lower() != ".ged":
        raise ValueError(f"URL does not point to a .ged file: {url!r}")


def download_url_bytes(
    url: str,
    *,
    timeout: int = DEFAULT_DOWNLOAD_TIMEOUT,
    max_bytes: int = DEFAULT_DOWNLOAD_MAX_BYTES,
    user_agent: str = "gedcomtools/0.7.5b1",
) -> bytes:
    """Download *url* with a timeout and a hard response-size cap.

    The body is streamed in chunks so very large responses do not need to be
    buffered by the HTTP client before the size check is enforced.
    """
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        content_length = resp.headers.get("Content-Length")
        if content_length is not None:
            try:
                cl_int = int(content_length)
            except ValueError:
                cl_int = None
            if cl_int is not None and cl_int > max_bytes:
                raise ValueError(
                    f"Response from {url} exceeds the {max_bytes} byte limit."
                )

        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = resp.read(64 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise ValueError(
                    f"Response from {url} exceeds the {max_bytes} byte limit."
                )
            chunks.append(chunk)
    return b"".join(chunks)


def combine_enums(name: str, *enums, allow_aliases=False, prefix_on_conflict=False) -> Enum:
    """Combine enum-like classes into a single iterable mapping."""
    items: dict[str, object] = {}
    seen_values: set[object] = set()

    for E in enums:
        for m in E:
            key = m.name
            val = m.value

            name_conflict = key in items
            value_conflict = (val in seen_values) and not allow_aliases

            if name_conflict or value_conflict:
                if prefix_on_conflict:
                    key = f"{E.__name__}_{key}"
                    if key in items:
                        raise ValueError(f"duplicate even after prefix: {key}")
                else:
                    raise ValueError(f"conflict on name={m.name!r} or value={m.value!r}")

            items[key] = val
            seen_values.add(val)

    return Enum(name, items)
