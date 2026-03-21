"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/date.py
 Purpose: Gedcom-X Date class with GEDCOM date format parsing and ISO 8601 support.

 Created: 2025-08-25
 Updated:
   - 2025-11-13: added Gedcom-X Date Format API
   - 2026-03-19: migrated to pydantic GedcomXModel
======================================================================
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, ClassVar, Optional

from pydantic import model_validator

from .gx_base import GedcomXModel

try:
    import dateparser
except ImportError:
    dateparser = None

try:
    from dateutil import parser as dateutil_parser
except ImportError:
    dateutil_parser = None


class DateFormat:
    pass


class DateNormalization:
    pass


class Date(GedcomXModel):
    identifier: ClassVar[str] = "http://gedcomx.org/v1/Date"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    original: Optional[str] = None
    formal: Optional[str] = None
    normalized: Optional[Any] = None  # DateNormalization

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_gedcomx_date, check_nonempty
        if not self.original and not self.formal:
            result.warn("", "Date has neither original nor formal value")
        if self.original is not None:
            check_nonempty(result, "original", self.original)
        check_gedcomx_date(result, "formal", self.formal)

    @model_validator(mode="after")
    def _parse_formal(self) -> "Date":
        if self.formal is None and self.original:
            try:
                self.formal = parse_to_gedcomx_date(self.original)
            except Exception:
                pass  # parsing failures are non-fatal
        return self


# ---------------------------------------------------------------------------
# GedcomX Date Format parsing (unchanged from original)
# ---------------------------------------------------------------------------

def parse_to_gedcomx_date(s: str) -> str:
    from .exceptions import GedcomXDateParseError

    original = s
    s = s.strip()
    if not s:
        raise GedcomXDateParseError("Empty date string")

    lower = s.lower()

    # ---- detect approximate ----
    approx_prefixes = (
        "about ", "abt ", "abt. ", "circa ", "ca. ", "ca ", "c. ",
        "approximately ", "approx. ", "approx ",
    )
    is_approx = any(lower.startswith(p) for p in approx_prefixes)
    if is_approx:
        for p in approx_prefixes:
            if lower.startswith(p):
                s = s[len(p):].strip()
                lower = s.lower()
                break

    # ---- detect range: "between X and Y" ----
    range_match = re.match(
        r"^between\s+(.+?)\s+and\s+(.+)$", s, re.IGNORECASE
    )
    if range_match:
        start_str = range_match.group(1).strip()
        end_str = range_match.group(2).strip()
        start = _parse_simple_to_gx(start_str)
        end = _parse_simple_to_gx(end_str)
        if start and end:
            return f"[{start}/{end}]"

    # ---- detect "before X" / "after X" ----
    before_match = re.match(r"^(?:before|bef\.?)\s+(.+)$", s, re.IGNORECASE)
    if before_match:
        date_part = _parse_simple_to_gx(before_match.group(1).strip())
        return f"A/{date_part}" if date_part else original

    after_match = re.match(r"^(?:after|aft\.?)\s+(.+)$", s, re.IGNORECASE)
    if after_match:
        date_part = _parse_simple_to_gx(after_match.group(1).strip())
        return f"{date_part}/" if date_part else original

    # ---- simple date ----
    result = _parse_simple_to_gx(s)
    if result is None:
        return original

    return f"A{result}" if is_approx else result


def _parse_simple_to_gx(s: str) -> str | None:
    s = s.strip()
    if not s:
        return None

    # Already in GedcomX/ISO format
    if re.match(r"^[+-]?\d{4}(-\d{2}(-\d{2})?)?$", s):
        return s

    dt = _parse_to_datetime(s)
    if dt is None:
        return None

    precision = _infer_precision_from_text(s)
    if precision == "year":
        return f"+{dt.year:04d}"
    if precision == "month":
        return f"+{dt.year:04d}-{dt.month:02d}"
    return f"+{dt.year:04d}-{dt.month:02d}-{dt.day:02d}"


def _infer_precision_from_text(s: str) -> str:
    s_lower = s.lower().strip()
    if re.match(r"^\d{4}$", s):
        return "year"
    year_only_patterns = [
        r"^\w+\s+\d{4}$",          # "Jan 1900" — month+year only
        r"^\d{1,2}/\d{4}$",         # 1/1900
        r"^\d{4}s?$",               # 1900 or 1900s
    ]
    if any(re.match(p, s) for p in year_only_patterns):
        return "month"
    return "day"


def _parse_to_datetime(s: str) -> datetime | None:
    if dateutil_parser:
        try:
            return dateutil_parser.parse(s, default=datetime(1, 1, 1))
        except Exception:
            pass
    if dateparser:
        try:
            result = dateparser.parse(s)
            if result:
                return result
        except Exception:
            pass
    return None


def date_to_timestamp(date_obj: Date | None) -> datetime | None:
    if date_obj is None:
        return None
    for attr in ("formal", "original"):
        val = getattr(date_obj, attr, None)
        if val:
            dt = _parse_to_datetime(str(val))
            if dt:
                return dt
    return None
