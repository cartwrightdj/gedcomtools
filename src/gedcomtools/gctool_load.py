# -*- coding: utf-8 -*-
"""
======================================================================
 Project: gedcomtools
 File:    gctool_load.py
 Purpose: Format detection, URL loading, file loading
 Created: 2026-04-01 — split from gctool.py
======================================================================
"""

from __future__ import annotations

import os
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Tuple

from gedcomtools.glog import get_logger

log = get_logger(__name__)

from .gctool_output import _bold


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

def _sniff(path: Path) -> str:
    """Return 'g5', 'g7', or 'gx'.  Raises ValueError if unknown."""
    suffix = path.suffix.lower()

    if suffix in (".json", ".gedcomx"):
        try:
            with open(path, "rb") as fh:
                if fh.read(1) == b"{":
                    return "gx"
        except OSError:
            pass

    if suffix in (".ged", ".gedcom", ".gdz", ""):
        if suffix == ".gdz":
            return "g7"  # .gdz is always a zipped GEDCOM 7 archive
        try:
            with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if line.startswith("2 VERS"):
                        parts = line.split(None, 2)
                        vers = parts[2] if len(parts) > 2 else ""
                        return "g7" if vers.startswith("7") else "g5"
                    if line.startswith("0 ") and "HEAD" not in line:
                        break
        except OSError:
            pass
        return "g5"  # no VERS found — assume GEDCOM 5

    raise ValueError(
        f"Cannot determine format for {path.name!r}. "
        "Expected .ged/.gedcom/.gdz (GEDCOM) or .json/.gedcomx (GedcomX)."
    )


# ---------------------------------------------------------------------------
# Unified loader
# ---------------------------------------------------------------------------

def _is_url(s: str) -> bool:
    """Return True if *s* looks like an HTTP/HTTPS URL."""
    return s.startswith("http://") or s.startswith("https://")


def _load_url(url: str) -> Tuple[str, Any]:
    """Download a GEDCOM file from *url* to a temp file and call :func:`_load`."""
    print(f"Fetching {url} …")
    try:
        with urllib.request.urlopen(url) as resp:
            data = resp.read()
    except urllib.error.HTTPError as exc:
        print(f"error: HTTP {exc.code} fetching {url}: {exc.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"error: cannot fetch {url}: {exc.reason}", file=sys.stderr)
        sys.exit(1)

    # Preserve the filename/extension so _sniff() works correctly.
    suffix = Path(url.split("?")[0]).suffix or ".ged"
    fd, tmp = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        return _load(Path(tmp))
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _load(path: Path) -> Tuple[str, Any]:
    """Return ``(fmt, obj)`` where *obj* is a ``Gedcom5`` or ``Gedcom7`` instance."""
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        fmt = _sniff(path)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    if fmt == "gx":
        print("error: gctool operates on GEDCOM 5/7 files. Use gxcli for GedcomX.", file=sys.stderr)
        sys.exit(1)

    if fmt == "g5":
        from gedcomtools.gedcom5.gedcom5 import Gedcom5
        obj = Gedcom5()
        try:
            obj.loadfile(path)
        except Exception as exc:
            print(f"error loading {path}: {exc}", file=sys.stderr)
            sys.exit(1)
        return "g5", obj

    # g7
    from gedcomtools.gedcom7.gedcom7 import Gedcom7
    obj = Gedcom7()
    try:
        if path.suffix.lower() == ".gdz":
            with zipfile.ZipFile(path) as zf:
                ged_names = [n for n in zf.namelist() if n.endswith(".ged")]
                if not ged_names:
                    print(f"error: no .ged file inside {path.name}", file=sys.stderr)
                    sys.exit(1)
                obj.parse_string(zf.read(ged_names[0]).decode("utf-8-sig"))
        else:
            obj.loadfile(path)
    except Exception as exc:
        print(f"error loading {path}: {exc}", file=sys.stderr)
        sys.exit(1)
    return "g7", obj
