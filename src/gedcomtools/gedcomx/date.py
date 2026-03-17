"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/date.py
 Author:  David J. Cartwright
 Purpose: Gedcom-X Date class with GEDCOM date format parsing and ISO 8601 support

 Created: 2025-08-25
 Updated:
   - 2025-09-03: _from_json refactored
   - 2025-09-09: added schema_class
   - 2025-11-13: added Gedcom-X Date Format API

======================================================================
"""
import re

from typing import Any, Optional, Dict
from datetime import datetime, timezone
from dateutil import parser

from typing import Optional

try:
    import dateparser
except ImportError:
    dateparser = None

try:
    from dateutil import parser as dateutil_parser
except ImportError:
    dateutil_parser = None

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
from .schemas import extensible
"""
======================================================================
Logging
======================================================================
"""
#=====================================================================


class DateFormat:
    def __init__(self) -> None:
        pass

class DateNormalization():
    pass        

@extensible()
class Date:
    identifier = 'http://gedcomx.org/v1/Date'
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self, original: Optional[str],normalized: Optional[DateNormalization] = None ,formal: Optional[str | DateFormat] = None) -> None:
        self.original = original
        self.formal = formal if formal else parse_to_gedcomx_date(original) if original else None

        self.normalized: DateNormalization | None = normalized if normalized else None
    
        

# ----------------------------------------------------------------------
# API for Gedcom-X Date Format
# ----------------------------------------------------------------------
def parse_to_gedcomx_date(s: str) -> str:
    original = s
    s = s.strip()
    if not s:
        raise GedcomXDateParseError("Empty date string")

    lower = s.lower()

    # ---- detect approximate ----
    approx_prefixes = (
        "about ", "abt ", "abt. ", "around ", "circa ", "c. ",
        "ca. ", "approx ", "approximately "
    )

    approx = False
    for pref in approx_prefixes:
        if lower.startswith(pref):
            approx = True
            s = s[len(pref):].strip()
            lower = s.lower()
            break

    # ------------------------------------------------------------------
    # CLOSED RANGES
    #   - "day month YYYY-YYYY"   e.g. "14 Feb 1744-1745"
    #   - "day month YYYY/YY"     e.g. "22 Feb 1662/63"
    #   - "between X and Y"
    #   - "from X to Y"
    #   - "X - Y" (with spaces)
    #   - "YYYY-YYYY" or "YYYY/YY"
    # ------------------------------------------------------------------

    # Double-year notation with prefix:
    #   "14 Feb 1744-1745" → "14 Feb 1744" / "14 Feb 1745"
    #   "22 Feb 1662/63"   → "22 Feb 1662" / "22 Feb 1663"
    m_double_year = re.match(r"^(.*\D)(\d{3,4})\s*[-/]\s*(\d{2,4})\s*$", s)
    if m_double_year:
        prefix = m_double_year.group(1)        # e.g. "22 Feb "
        y1_str = m_double_year.group(2)        # "1662"
        y2_str = m_double_year.group(3)        # "63"

        # Expand shortened year, e.g. 1662 + "63" -> "1663"
        if len(y2_str) < len(y1_str):
            y2_full = y1_str[: len(y1_str) - len(y2_str)] + y2_str
        else:
            y2_full = y2_str

        left_raw = f"{prefix}{y1_str}".strip()
        right_raw = f"{prefix}{y2_full}".strip()

        left = _parse_simple_to_gx(left_raw)
        right = _parse_simple_to_gx(right_raw)
        gx = f"{left}/{right}"
        return "A" + gx if approx else gx

    # pure year range "1999-2017", "1662/63" (spaces optional)
    m_year_range = re.match(r"^\s*(\d{3,4})\s*[-/]\s*(\d{2,4})\s*$", s)
    if m_year_range:
        y1_str = m_year_range.group(1)     # "1662"
        y2_str = m_year_range.group(2)     # "63" or "2017"

        if len(y2_str) < len(y1_str):
            y2_full = y1_str[: len(y1_str) - len(y2_str)] + y2_str
        else:
            y2_full = y2_str

        y1 = int(y1_str)
        y2 = int(y2_full)

        left = f"+{y1:04d}"
        right = f"+{y2:04d}"
        gx = f"{left}/{right}"
        return "A" + gx if approx else gx

    # between X and Y
    m_between = re.match(r"^(?:between)\s+(.+?)\s+and\s+(.+)$", lower, re.IGNORECASE)
    if m_between:
        left_raw = s[m_between.start(1):m_between.end(1)]
        right_raw = s[m_between.start(2):m_between.end(2)]
        left = _parse_simple_to_gx(left_raw)
        right = _parse_simple_to_gx(right_raw)
        gx = f"{left}/{right}"
        return "A" + gx if approx else gx

    # from X to Y
    m_from = re.match(r"^(?:from)\s+(.+?)\s+to\s+(.+)$", lower, re.IGNORECASE)
    if m_from:
        left_raw = s[m_from.start(1):m_from.end(1)]
        right_raw = s[m_from.start(2):m_from.end(2)]
        left = _parse_simple_to_gx(left_raw)
        right = _parse_simple_to_gx(right_raw)
        gx = f"{left}/{right}"
        return "A" + gx if approx else gx

    # X - Y  (dash ranges with spaces so we don't collide with 1880-03-14)
    m_dash = re.match(r"^(.+?)\s+[-–]\s+(.+)$", s)
    if m_dash:
        left_raw = m_dash.group(1).strip()
        right_raw = m_dash.group(2).strip()
        left = _parse_simple_to_gx(left_raw)
        right = _parse_simple_to_gx(right_raw)
        gx = f"{left}/{right}"
        return "A" + gx if approx else gx

    # ------------------------------------------------------------------
    # OPEN-ENDED RANGES ("before X", "after X")
    # ------------------------------------------------------------------

    m_before = re.match(r"^(?:before|bef\.?)\s+(.+)$", lower, re.IGNORECASE)
    if m_before:
        tgt_raw = s[m_before.start(1):m_before.end(1)]
        tgt = _parse_simple_to_gx(tgt_raw)
        gx = f"/{tgt}"
        return "A" + gx if approx else gx

    m_after = re.match(r"^(?:after|aft\.?)\s+(.+)$", lower, re.IGNORECASE)
    if m_after:
        tgt_raw = s[m_after.start(1):m_after.end(1)]
        tgt = _parse_simple_to_gx(tgt_raw)
        gx = f"{tgt}/"
        return "A" + gx if approx else gx

    # ------------------------------------------------------------------
    # Plain simple date
    # ------------------------------------------------------------------
    gx = _parse_simple_to_gx(s)
    return "A" + gx if approx else gx


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
_YEAR_ONLY_RE = re.compile(r"^\s*(\d{4})\s*$")
_YEAR_MONTH_NUM_RE = re.compile(r"^\s*(\d{4})[-/](\d{1,2})\s*$")
# e.g. "March 1880", "Mar 1880"
_MONTH_YEAR_RE = re.compile(
    r"^\s*([A-Za-z]{3,9})[\s,]+(\d{4})\s*$"
)


def _parse_simple_to_gx(s: str) -> str:
    """
    Parse a single non-range, non-approx string into a GEDCOM X simple date:
      +YYYY
      +YYYY-MM
      +YYYY-MM-DD

    Uses heuristics to guess precision from the text.
    """
    raw = s
    s = s.strip()
    if not s:
        raise GedcomXDateParseError("Empty date part in range")

    # Determine intended precision from the *text* first
    precision = _infer_precision_from_text(s)

    dt = _parse_to_datetime(s)
    if dt is None:
        raise GedcomXDateParseError(f"Could not parse date: {raw!r}")

    year = dt.year
    if year <= 0:
        # For now we punt on BCE; GEDCOM X supports it, but typical
        # libs don't parse negative/0 years well.
        raise GedcomXDateParseError(f"BCE or year <= 0 not supported yet: {year}")

    sign = "+"
    # GEDCOM X wants 4-digit year, left padded
    if precision == "year":
        return f"{sign}{year:04d}"
    elif precision == "month":
        return f"{sign}{year:04d}-{dt.month:02d}"
    else:  # "day"
        return f"{sign}{year:04d}-{dt.month:02d}-{dt.day:02d}"


def _infer_precision_from_text(s: str) -> str:
    """
    Best-effort guess of precision: 'year', 'month', or 'day'
    based on the raw text.
    """
    s_clean = s.strip()

    # just 4 digits
    if _YEAR_ONLY_RE.match(s_clean):
        return "year"

    # pure numeric year-month:  YYYY-MM or YYYY/MM
    if _YEAR_MONTH_NUM_RE.match(s_clean):
        return "month"

    # "March 1880", "Mar 1880" etc.
    if _MONTH_YEAR_RE.match(s_clean):
        return "month"

    # Default: assume day precision if there's enough info
    return "day"


def _parse_to_datetime(s: str):
    """
    Try dateparser first (if installed), then dateutil, otherwise fail.
    Returns a datetime or None.
    """
    # dateparser
    if dateparser is not None:
        dt = dateparser.parse(
            s,
            settings={
                "PREFER_DAY_OF_MONTH": "first",
                "PREFER_DATES_FROM": "past",
            },
        )
        if dt is not None:
            return dt

    # dateutil
    if dateutil_parser is not None:
        try:
            return dateutil_parser.parse(s, fuzzy=True)
        except Exception:
            pass

    return None



def date_to_timestamp(date_str: str, assume_utc_if_naive: bool = True, print_definition: bool = True):
    """
    Convert a date string of various formats into a Unix timestamp.

    A "timestamp" refers to an instance of time, including values for year, 
    month, date, hour, minute, second, and timezone.
    """
    # Handle year ranges like "1894-1912" → pick first year
    if "-" in date_str and date_str.count("-") == 1 and all(part.isdigit() for part in date_str.split("-")):
        date_str = date_str.split("-")[0].strip()

    # Parse date
    dt = parser.parse(date_str)

    # Ensure timezone awareness
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc if assume_utc_if_naive else datetime.now().astimezone().tzinfo)

    # Normalize to UTC and compute timestamp
    dt_utc = dt.astimezone(timezone.utc)
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    ts = (dt_utc - epoch).total_seconds()

    # Create ISO 8601 string with full date/time/timezone
    full_timestamp_str = dt_utc.replace(microsecond=0).isoformat()

    
    return ts, full_timestamp_str