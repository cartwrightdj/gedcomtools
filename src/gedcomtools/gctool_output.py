# -*- coding: utf-8 -*-
"""
======================================================================
 Project: gedcomtools
 File:    gctool_output.py
 Purpose: Color helpers, table/kv output, _norm_xref
 Created: 2026-04-01 — split from gctool.py
======================================================================
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, List, Tuple


# ---------------------------------------------------------------------------
# ANSI colour helpers
# ---------------------------------------------------------------------------

def _colour_ok() -> bool:
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _c(code: str, text: str) -> str:
    return f"\x1b[{code}m{text}\x1b[0m" if _colour_ok() else text


def _green(t: str) -> str: return _c("32", t)
def _yellow(t: str) -> str: return _c("33", t)
def _red(t: str) -> str: return _c("31", t)
def _cyan(t: str) -> str: return _c("36", t)
def _bold(t: str) -> str: return _c("1", t)
def _dim(t: str) -> str: return _c("2", t)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _table(
    headers: List[str],
    rows: List[List[str]],
    *,
    json_out: bool = False,
    json_key: str = "records",
) -> None:
    if json_out:
        data = [
            {h: (row[i] if i < len(row) else "") for i, h in enumerate(headers)}
            for row in rows
        ]
        print(json.dumps({json_key: data}, ensure_ascii=False, indent=2))
        return
    if not rows:
        print("  (no records)")
        return
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(_bold(fmt.format(*headers)))
    print(_dim("  ".join("-" * w for w in widths)))
    for row in rows:
        padded = [str(row[i]) if i < len(row) else "" for i in range(len(headers))]
        print(fmt.format(*padded))


def _kv(pairs: List[Tuple[str, Any]], *, json_out: bool = False) -> None:
    if json_out:
        print(json.dumps(
            {k: v for k, v in pairs if v is not None},
            ensure_ascii=False, indent=2, default=str,
        ))
        return
    width = max((len(k) for k, _ in pairs), default=10)
    for k, v in pairs:
        if v is not None and v != [] and v != "":
            print(f"  {_cyan(k.ljust(width))}  {v}")


def _norm_xref(xref: str) -> str:
    xref = xref.strip()
    if not xref.startswith("@"):
        xref = f"@{xref}@"
    return xref.upper()
