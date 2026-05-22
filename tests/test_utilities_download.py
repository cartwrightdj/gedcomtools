"""Tests for shared bounded URL download helpers.

Updated: 2026-04-15 — release refresh for v0.8.0b4 docs/build packaging.
"""

from __future__ import annotations

import urllib.error

import pytest

from gedcomtools.gedcom7.gedcom7 import Gedcom7
from gedcomtools.utils.Utilities import download_url_bytes


class _FakeResponse:
    def __init__(self, chunks: list[bytes], headers: dict[str, str] | None = None) -> None:
        self._chunks = list(chunks)
        self.headers = headers or {}

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self, _size: int = -1) -> bytes:
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


def test_download_url_bytes_rejects_large_content_length(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(req, timeout=0):  # type: ignore[no-untyped-def]
        return _FakeResponse([b""], headers={"Content-Length": "11"})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    with pytest.raises(ValueError, match="exceeds the 10 byte limit"):
        download_url_bytes("https://example.com/test.ged", max_bytes=10)


def test_download_url_bytes_rejects_stream_larger_than_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(req, timeout=0):  # type: ignore[no-untyped-def]
        return _FakeResponse([b"12345", b"67890", b"X"], headers={})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    with pytest.raises(ValueError, match="exceeds the 10 byte limit"):
        download_url_bytes("https://example.com/test.ged", max_bytes=10)


def test_download_url_bytes_ignores_non_numeric_content_length(monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-numeric Content-Length header must not raise — fall through to streaming check."""
    def fake_urlopen(req, timeout=0):  # type: ignore[no-untyped-def]
        return _FakeResponse([b"hi"], headers={"Content-Length": "not-a-number"})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = download_url_bytes("https://example.com/test.ged", max_bytes=100)
    assert result == b"hi"


def test_gedcom7_load_url_surfaces_bounded_download_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_download(_url: str) -> bytes:
        raise ValueError("Response from test exceeds the 16 byte limit.")

    monkeypatch.setattr("gedcomtools.gedcom7.gedcom7.download_url_bytes", fake_download)

    g = Gedcom7()
    with pytest.raises(ValueError, match="Cannot fetch GEDCOM from https://example.com/tree.ged"):
        g.load_url("https://example.com/tree.ged")


def test_gedcom7_load_url_preserves_urlerror(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_download(_url: str) -> bytes:
        raise urllib.error.URLError("network down")

    monkeypatch.setattr("gedcomtools.gedcom7.gedcom7.download_url_bytes", fake_download)

    g = Gedcom7()
    with pytest.raises(urllib.error.URLError, match="network down"):
        g.load_url("https://example.com/tree.ged")
