"""
======================================================================
 Project: gedcomtools
 File:    gedcom5/g5tog7.py
 Purpose: GEDCOM 5.x → GEDCOM 7.0 structure converter.

 Created: 2026-03-24
 Updated: 2026-03-24 — added unknown_tags='drop'|'convert' option;
                        _handle_vendor_child; _ALWAYS_DROP/_VENDOR_TAGS
                        split; OBJE handler uses vendor-tag split
 Updated: 2026-03-31 — added get_logger; replaced bare except Exception blocks
                        with specific exception types and log.debug() messages
======================================================================

Walks the raw G5 element tree and builds a ``List[GedcomStructure]``
suitable for passing directly to ``Gedcom7Writer``.

Key transformations
-------------------
* ``HEAD`` is rebuilt with mandatory ``GEDC.VERS 7.0``.
* ``HEAD.CHAR`` / ``HEAD.FILE`` / ``HEAD.GEDC`` are handled explicitly.
* ``SUBN`` records are dropped (no equivalent in GEDCOM 7).
* Level-0 ``NOTE @xref@`` records are promoted to ``SNOTE``.
* ``CONC`` children are merged into the parent payload.
* ``CONT`` children are merged with a newline separator; the G7 writer
  re-serialises them as ``CONT`` lines automatically.
* Vendor-specific G5 tags (``RIN``, ``FSID``, ``WWW``, ``AFN``,
  ``ADR4``–``ADR6``) are either dropped or renamed to ``_TAG`` extension
  tags depending on the ``unknown_tags`` constructor argument.
* Structurally illegal G5 sub-tags are dropped per context (e.g.
  ``PUBL.DATE``, ``SOUR.FILE``, ``FORM.TYPE``, ``OBJE.DATE``).
* Extension tags (``_TAG``) are collected and declared in
  ``HEAD.SCHMA.TAG`` so the G7 validator accepts them.

Usage::

    from gedcomtools.gedcom5.gedcom5 import Gedcom5
    from gedcomtools.gedcom5.g5tog7 import Gedcom5to7
    from gedcomtools.gedcom7.writer import Gedcom7Writer

    g5 = Gedcom5("family.ged")
    records = Gedcom5to7().convert(g5)
    Gedcom7Writer().write(records, "family_g7.ged")
"""

from __future__ import annotations

import re
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from gedcomtools.gedcom7.structure import GedcomStructure
from gedcomtools.glog import get_logger

log = get_logger(__name__)


_POINTER_RE = re.compile(r"^@[^@\s]+@$")

# Matches ISO-style year ranges that FTM and similar apps write:
#   YYYY-YYYY  →  BET YYYY AND YYYY
#   YYYY-      →  FROM YYYY
#   -YYYY      →  TO YYYY
_ISO_RANGE_RE = re.compile(r"^(\d{3,4})?-(\d{3,4})?$")

# Full English month name / variant abbreviation / German name → GEDCOM 3-letter abbreviation
_MONTH_MAP: Dict[str, str] = {
    # Full English names
    "january": "JAN", "february": "FEB", "march":    "MAR",
    "april":   "APR", "may":      "MAY", "june":     "JUN",
    "july":    "JUL", "august":   "AUG", "september":"SEP",
    "october": "OCT", "november": "NOV", "december": "DEC",
    # Common English variant abbreviations (incl. period-stripped forms)
    "jan": "JAN", "feb": "FEB", "mar": "MAR", "apr": "APR",
    "jun": "JUN", "jul": "JUL", "aug": "AUG",
    "sept": "SEP", "sep": "SEP",
    "oct": "OCT", "nov": "NOV", "dec": "DEC",
    # German month names (common in German genealogy software exports)
    "januar": "JAN", "februar": "FEB", "märz": "MAR", "marz": "MAR",
    "mai":    "MAY", "juni":    "JUN", "juli": "JUL",
    "oktober":"OCT", "dezember":"DEC", "dez":  "DEC",
}

# ISO full date  YYYY-MM-DD
_ISO_DATE_RE = re.compile(r"^(\d{3,4})-(\d{2})-(\d{2})$")

# US slash date  MM/DD/YYYY  or  M/D/YYYY
_US_SLASH_RE = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{3,4})$")

# Dual year appended as range:  14 Feb 1744-1745  → 14 FEB 1744/45
_DUAL_YEAR_RE = re.compile(r"^(.+\s)(\d{3,4})-(\d{2,4})$")

# Parenthetical alternative year:  "16 March 1720 (1721)"  → strip it
_PAREN_YEAR_RE = re.compile(r"\s*\(\d{3,4}\)\s*$")

# Numeric month → abbreviation
_MONTH_NUM: Dict[str, str] = {
    "01":"JAN","02":"FEB","03":"MAR","04":"APR","05":"MAY","06":"JUN",
    "07":"JUL","08":"AUG","09":"SEP","10":"OCT","11":"NOV","12":"DEC",
    "1":"JAN","2":"FEB","3":"MAR","4":"APR","5":"MAY","6":"JUN",
    "7":"JUL","8":"AUG","9":"SEP",
}

# US-style "Mon DD YYYY"  e.g. "Mar 13 1816"
_US_ABBR_MDY_RE = re.compile(r"^([^\W\d_]+)\s+(\d{1,2})\s+(\d{3,4})$", re.UNICODE)

# Dash-separated US date  M-D-YYYY  e.g. "8-20-1732"
_US_DASH_RE = re.compile(r"^(\d{1,2})-(\d{1,2})-(\d{3,4})$")

# Dual year with spaces around slash  "15 Jan 1717 / 18" → "15 JAN 1717/18"
_SPACED_DUAL_RE = re.compile(r"^(.+)\s+(\d{3,4})\s*/\s*(\d{2,4})$")

# Parenthetical suffix of any short number  e.g. "(51)"  — strip it
_PAREN_NUM_RE = re.compile(r"\s*\(\d{1,4}\)\s*$")

# English date qualifiers → GEDCOM equivalents
_QUALIFIER_MAP: Dict[str, str] = {
    "before": "BEF", "after": "AFT", "about": "ABT",
    "circa":  "ABT", "ca":    "ABT", "c.":    "ABT",
    "abt":    "ABT", "bef":   "BEF", "aft":   "AFT",
}

# Strip leading day-of-week:  "Wednesday, January 19, 1921" → "January 19, 1921"
_DOW_RE = re.compile(
    r"^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s*",
    re.IGNORECASE,
)

# Full-month date patterns after DOW stripping.
# Use \w to match Unicode month names (e.g. German "März").
_FULL_MONTH_DMY_RE = re.compile(
    r"^(\d{1,2})\s+([^\W\d_]+)\s+(\d{3,4})$", re.UNICODE
)
_FULL_MONTH_MDY_RE = re.compile(
    r"^([^\W\d_]+)\s+(\d{1,2}),?\s+(\d{3,4})$", re.UNICODE
)
_FULL_MONTH_MY_RE = re.compile(
    r"^([^\W\d_]+)\s+(\d{3,4})$", re.UNICODE
)


def _normalize_date(value: str) -> str:
    """Convert non-standard date strings to GEDCOM date grammar where possible.

    Handles:
    * ISO year ranges:           ``1999-2017``        →  ``BET 1999 AND 2017``
    * ISO full date:             ``1891-05-18``        →  ``18 MAY 1891``
    * US slash date:             ``04/15/1966``        →  ``15 APR 1966``
    * Full English month names:  ``1 June 1915``       →  ``1 JUN 1915``
    * Month-day-year US format:  ``June 1, 1915``      →  ``1 JUN 1915``
    * US abbrev month-day-year:  ``Mar 13 1816``       →  ``13 MAR 1816``
    * Month-year:                ``November 1726``     →  ``NOV 1726``
    * Dual year suffix:          ``14 Feb 1744-1745``  →  ``14 FEB 1744/45``
    * Parenthetical year:        ``16 March 1720 (1721)`` →  ``16 MAR 1720``
    * English qualifiers:        ``Before 1951``       →  ``BEF 1951``
    * Day-of-week prefix:        ``Wednesday, January 19, 1921``  →  ``19 JAN 1921``

    All other values are returned unchanged.
    """
    v = value.strip()

    # 1. ISO year range  YYYY-YYYY / YYYY- / -YYYY
    m = _ISO_RANGE_RE.match(v)
    if m:
        start, end = m.group(1), m.group(2)
        if start and end:
            return f"BET {start} AND {end}"
        if start:
            return f"FROM {start}"
        if end:
            return f"TO {end}"

    # 2. ISO full date  YYYY-MM-DD
    m = _ISO_DATE_RE.match(v)
    if m:
        abbr = _MONTH_NUM.get(m.group(2))
        if abbr:
            return f"{int(m.group(3))} {abbr} {m.group(1)}"

    # 3. US slash date  MM/DD/YYYY
    m = _US_SLASH_RE.match(v)
    if m:
        abbr = _MONTH_NUM.get(m.group(1))
        if abbr:
            return f"{int(m.group(2))} {abbr} {m.group(3)}"

    # 4. US dash date  M-D-YYYY  (must be checked before ISO range)
    m = _US_DASH_RE.match(v)
    if m:
        abbr = _MONTH_NUM.get(m.group(1))
        if abbr:
            return f"{int(m.group(2))} {abbr} {m.group(3)}"

    # 5. Strip leading day-of-week
    v = _DOW_RE.sub("", v)

    # 6. Strip period from month abbreviations  "Oct. 25, 1782" → "Oct 25, 1782"
    v = re.sub(r"\b([A-Za-z]{3,4})\.", r"\1", v)

    # 7. Strip parenthetical suffix (alternative year or age)  "(1721)" / "(51)"
    v = _PAREN_NUM_RE.sub("", v)

    # 8. Spaced dual year  "15 Jan 1717 / 18"  →  "15 JAN 1717/18"
    m = _SPACED_DUAL_RE.match(v)
    if m:
        rest = _normalize_date(f"{m.group(1)} {m.group(2)}")
        short = m.group(3)[-2:]
        return f"{rest}/{short}"

    # 9. English qualifier prefix (Before/After/About …)
    words = v.split(None, 1)
    if len(words) == 2 and words[0].rstrip(".").lower() in _QUALIFIER_MAP:
        qual = _QUALIFIER_MAP[words[0].rstrip(".").lower()]
        rest = _normalize_date(words[1])  # recurse to normalise the date part
        return f"{qual} {rest}"

    # 10. Dual year appended as range  "14 Feb 1744-1745" → "14 FEB 1744/45"
    m = _DUAL_YEAR_RE.match(v)
    if m:
        prefix, y1, y2 = m.group(1), m.group(2), m.group(3)
        short = y2[-2:]
        rest = _normalize_date(f"{prefix}{y1}")
        return f"{rest}/{short}"

    # 11. Full/abbrev month name — D MONTH YYYY
    m2 = _FULL_MONTH_DMY_RE.match(v)
    if m2:
        abbr = _MONTH_MAP.get(m2.group(2).lower())
        if abbr:
            return f"{m2.group(1)} {abbr} {m2.group(3)}"

    # 12. Full month name — MONTH D, YYYY  (US format)
    m3 = _FULL_MONTH_MDY_RE.match(v)
    if m3:
        abbr = _MONTH_MAP.get(m3.group(1).lower())
        if abbr:
            return f"{m3.group(2)} {abbr} {m3.group(3)}"

    # 13. US abbrev month-day-year  "Mar 13 1816"
    m5 = _US_ABBR_MDY_RE.match(v)
    if m5:
        abbr = _MONTH_MAP.get(m5.group(1).lower())
        if abbr:
            return f"{m5.group(2)} {abbr} {m5.group(3)}"

    # 14. Full/abbrev month name — MONTH YYYY
    m4 = _FULL_MONTH_MY_RE.match(v)
    if m4:
        abbr = _MONTH_MAP.get(m4.group(1).lower())
        if abbr:
            return f"{abbr} {m4.group(2)}"

    return value


# Tags whose payload is folded into the parent; they are never emitted as children.
_FOLD: FrozenSet[str] = frozenset({"CONC", "CONT"})

# Tags always dropped regardless of mode — these have no G7 structural equivalent.
_ALWAYS_DROP: FrozenSet[str] = frozenset({
    "CHAR",   # charset — G7 is always UTF-8; no declaration needed
    "SUBN",   # submission record — not in G7
})

# Vendor / non-standard tags that have no G7 equivalent but carry real data.
# In "drop" mode these are discarded; in "convert" mode they become _TAG extensions.
_VENDOR_TAGS: FrozenSet[str] = frozenset({
    "RIN",    # G5 vendor record-ID
    "FSID",   # FamilySearch ID
    "AFN",    # Ancestral File Number
    "WWW",    # website URL tag used by some G5 apps
    "ADR4",   # non-standard extended address lines
    "ADR5",
    "ADR6",
})

# Combined set for callers that don't need the distinction.
_DROP: FrozenSet[str] = _ALWAYS_DROP | _VENDOR_TAGS

# (parent_tag, child_tag) pairs that are structurally illegal in G7 and dropped.
_CONTEXT_DROP: FrozenSet[Tuple[str, str]] = frozenset({
    ("HEAD",  "FILE"),   # HEAD.FILE — path information, not in G7 HEAD
    ("PUBL",  "DATE"),   # SOUR.PUBL.DATE — not in G7 PUBL
    ("SOUR",  "DATE"),   # direct DATE child of top-level SOUR not in G7
    ("SOUR",  "FILE"),   # SOUR.FILE — not in G7 SOUR structure
    ("FORM",  "TYPE"),   # FORM.TYPE — not in G7 (G5 used TYPE for media sub-type)
    ("OBJE",  "DATE"),   # OBJE.DATE — not in G7 OBJE
    ("OBJE",  "PLAC"),   # OBJE.PLAC — not in G7 OBJE
    ("DATA",  "WWW"),    # DATA.WWW — not a standard G7 tag
    ("CENS",  "HUSB"),   # CENS.HUSB — not in G7 CENS event
    ("CENS",  "WIFE"),   # CENS.WIFE — not in G7 CENS event
    ("SUBM",  "COMM"),   # SUBM.COMM (G5 commercial info) — not in G7 SUBM
})

# Tags whose payload must be uppercased (G5 files sometimes use lowercase).
_UPPERCASE_PAYLOAD: FrozenSet[str] = frozenset({"PEDI", "QUAY", "RESN"})

# HEAD children handled explicitly (rebuilt, remapped, or dropped) in _build_head.
_HEAD_EXPLICIT: FrozenSet[str] = frozenset({"CHAR", "GEDC", "FILE", "SUBN"})

# Placeholder URI base for undeclared extension tags.
_EXT_URI_BASE = "https://gedcom.io/terms/v7#"


class Gedcom5to7:
    """Convert a GEDCOM 5.x file to a list of GEDCOM 7 ``GedcomStructure`` records.

    Args:
        unknown_tags: How to handle vendor / non-standard G5 tags that have no
            direct G7 equivalent (``RIN``, ``FSID``, ``AFN``, ``WWW``,
            ``ADR4``–``ADR6``).

            * ``"drop"`` *(default)* — silently discard with a warning.
            * ``"convert"`` — rename to ``_TAG`` extension tags (prepend ``_``)
              and declare them in ``HEAD.SCHMA.TAG`` so the G7 validator accepts
              them.  Use this when data preservation matters more than a clean
              validation report.

    Attributes:
        warnings: Human-readable notes about lossy or notable transformations,
            populated after each :meth:`convert` call.
    """

    def __init__(self, *, unknown_tags: str = "drop") -> None:
        if unknown_tags not in ("drop", "convert"):
            raise ValueError(
                f"unknown_tags must be 'drop' or 'convert', got {unknown_tags!r}"
            )
        self._unknown_tags = unknown_tags
        self.warnings: List[str] = []
        self._snote_promoted: int = 0
        self._dropped_tags: Dict[str, int] = {}
        self._ext_tags: Set[str] = set()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def convert(self, g5_or_parser: Any) -> List[GedcomStructure]:
        """Convert a loaded GEDCOM 5 file to a list of top-level G7 records.

        Args:
            g5_or_parser: Either a :class:`~gedcomtools.gedcom5.gedcom5.Gedcom5`
                facade or a raw ``Gedcom5x`` parser instance.

        Returns:
            Records ready for ``Gedcom7Writer.write()``.  The list starts with
            ``HEAD`` and ends with ``TRLR``.
        """
        self.warnings = []
        self._snote_promoted = 0
        self._dropped_tags = {}
        self._ext_tags = set()

        parser = getattr(g5_or_parser, "_parser", g5_or_parser)
        try:
            roots = list(parser.get_root_child_elements())
        except (AttributeError, TypeError) as exc:
            log.debug("get_root_child_elements failed: {}", exc)
            roots = []

        g5_head = next(
            (el for el in roots if (el.tag or "").upper() == "HEAD"), None
        )

        # HEAD goes first — we'll patch SCHMA into it after the full scan.
        head_record = self._build_head(g5_head)
        records: List[GedcomStructure] = [head_record]

        for el in roots:
            tag = (el.tag or "").upper()
            if tag in ("HEAD", "TRLR"):
                continue
            if tag in _DROP:
                self._note_drop(tag)
                continue

            xref = (getattr(el, "xref_id", None) or getattr(el, "xref", None) or "").strip()

            # Level-0 NOTE with an xref → SNOTE in GEDCOM 7
            force = "SNOTE" if (tag == "NOTE" and xref) else None
            rec = self._convert_element(el, level=0, parent=None,
                                        force_tag=force, parent_tag="")
            if rec is not None:
                if force:
                    self._snote_promoted += 1
                records.append(rec)

        records.append(GedcomStructure(level=0, tag="TRLR"))

        # Patch HEAD.SCHMA with any extension tags found during conversion.
        self._declare_extensions(head_record)

        # Post-process: convert extra MARR events in FAM records to EVEN TYPE MARR.
        self._fix_marr_cardinality(records)

        # Build human-readable warnings.
        if self._snote_promoted:
            self.warnings.append(
                f"{self._snote_promoted} level-0 NOTE record(s) promoted to SNOTE"
            )
        for tag, n in sorted(self._dropped_tags.items()):
            self.warnings.append(f"tag {tag!r} dropped ({n} occurrence(s))")

        return records

    # ------------------------------------------------------------------
    # HEAD builder
    # ------------------------------------------------------------------

    def _build_head(self, g5_head: Optional[Any]) -> GedcomStructure:
        """Construct a GEDCOM 7-conformant HEAD record."""
        head = GedcomStructure(level=0, tag="HEAD")

        # Mandatory in GEDCOM 7: GEDC / VERS 7.0
        gedc = GedcomStructure(level=1, tag="GEDC", parent=head)
        GedcomStructure(level=2, tag="VERS", payload="7.0", parent=gedc)

        if g5_head is None:
            return head

        char_val: Optional[str] = None
        try:
            for child in g5_head.get_child_elements():
                ctag = (child.tag or "").upper()
                if ctag in _HEAD_EXPLICIT:
                    if ctag == "CHAR":
                        try:
                            char_val = child.get_value() or ""
                        except (AttributeError, TypeError) as exc:
                            log.debug("HEAD.CHAR get_value failed: {}", exc)
                    continue  # GEDC replaced; CHAR, FILE, SUBN dropped
                self._convert_element(child, level=1, parent=head, parent_tag="HEAD")
        except (AttributeError, TypeError) as exc:
            log.debug("_build_head iteration failed: {}", exc)

        if char_val and char_val.upper() not in ("UTF-8", "UTF8", "UNICODE"):
            self.warnings.append(
                f"HEAD.CHAR was {char_val!r}; output is UTF-8 (GEDCOM 7 requirement)"
            )
        return head

    # ------------------------------------------------------------------
    # Post-processing
    # ------------------------------------------------------------------

    def _fix_marr_cardinality(self, records: List[GedcomStructure]) -> None:
        """Convert duplicate MARR events in FAM records to ``EVEN TYPE MARR``.

        GEDCOM 7 allows at most one ``MARR`` per ``FAM``.  When G5 files have
        multiple marriage events for the same family (e.g. remarriage after
        annulment), the additional ones are converted to generic ``EVEN``
        records with a ``TYPE MARR`` child so no data is lost.
        """
        for rec in records:
            if rec.tag != "FAM":
                continue
            marr_nodes = [c for c in rec.children if c.tag == "MARR"]
            if len(marr_nodes) <= 1:
                continue
            for extra in marr_nodes[1:]:
                extra.tag = "EVEN"
                # Prepend TYPE MARR child if not already present.
                if not any(c.tag == "TYPE" for c in extra.children):
                    type_node = GedcomStructure(
                        level=extra.level + 1,
                        tag="TYPE",
                        payload="MARR",
                        parent=None,
                    )
                    type_node.parent = extra
                    extra.children.insert(0, type_node)
                self.warnings.append(
                    f"{rec.xref_id}: extra MARR converted to EVEN TYPE MARR"
                )

    # ------------------------------------------------------------------
    # Extension tag SCHMA declaration
    # ------------------------------------------------------------------

    def _declare_extensions(self, head: GedcomStructure) -> None:
        """Walk *head* and all records to collect extension tags, add HEAD.SCHMA."""
        if not self._ext_tags:
            return
        schma = GedcomStructure(level=1, tag="SCHMA", parent=head)
        for ext in sorted(self._ext_tags):
            GedcomStructure(
                level=2, tag="TAG",
                payload=f"{ext} {_EXT_URI_BASE}{ext}",
                parent=schma,
            )

    # ------------------------------------------------------------------
    # Generic recursive element converter
    # ------------------------------------------------------------------

    def _merged_payload(self, el: Any) -> str:
        """Return element value with CONC/CONT children folded in."""
        try:
            base = el.get_value() or ""
        except (AttributeError, TypeError) as exc:
            log.debug("get_value failed in _merged_payload: {}", exc)
            base = ""
        try:
            for child in el.get_child_elements():
                ctag = (child.tag or "").upper()
                try:
                    cval = child.get_value() or ""
                except (AttributeError, TypeError) as exc:
                    log.debug("child.get_value failed: {}", exc)
                    cval = ""
                if ctag == "CONC":
                    base += cval
                elif ctag == "CONT":
                    base += "\n" + cval
        except (AttributeError, TypeError) as exc:
            log.debug("get_child_elements failed in _merged_payload: {}", exc)
        return base

    def _note_drop(self, tag: str) -> None:
        self._dropped_tags[tag] = self._dropped_tags.get(tag, 0) + 1

    def _handle_vendor_child(
        self,
        el: Any,
        tag: str,
        level: int,
        parent: Optional[GedcomStructure],
    ) -> None:
        """Handle a vendor/non-standard G5 tag according to ``unknown_tags`` mode."""
        if self._unknown_tags == "convert":
            ext_tag = tag if tag.startswith("_") else f"_{tag}"
            self._convert_element(el, level, parent=parent, force_tag=ext_tag)
        else:
            self._note_drop(tag)

    def _convert_obje(
        self,
        el: Any,
        level: int,
        parent: Optional[GedcomStructure],
    ) -> Optional[GedcomStructure]:
        """Convert a G5 OBJE element, moving top-level FORM under FILE children.

        In GEDCOM 5, ``FORM`` is a direct child of ``OBJE``.
        In GEDCOM 7, ``FORM`` must be a child of ``FILE``.
        """
        xref_raw = ""
        if level == 0:
            xref_raw = (
                getattr(el, "xref_id", None) or getattr(el, "xref", None) or ""
            ).strip()

        node = GedcomStructure(
            level=level,
            tag="OBJE",
            xref_id=xref_raw or None,
            payload=self._merged_payload(el),
            parent=parent,
        )

        # Collect FORM value from direct OBJE children (G5 pattern).
        g5_form = ""
        try:
            for child in el.get_child_elements():
                if (child.tag or "").upper() == "FORM":
                    try:
                        g5_form = child.get_value() or ""
                    except (AttributeError, TypeError) as exc:
                        log.debug("OBJE FORM get_value failed: {}", exc)
                    break
        except (AttributeError, TypeError) as exc:
            log.debug("get_child_elements failed scanning OBJE FORM: {}", exc)

        try:
            children = el.get_child_elements()
        except (AttributeError, TypeError) as exc:
            log.debug("get_child_elements failed in _convert_obje: {}", exc)
            children = []

        for child in children:
            ctag = (child.tag or "").upper()
            if ctag in _FOLD or ctag in _ALWAYS_DROP:
                continue
            if ctag in _VENDOR_TAGS:
                self._handle_vendor_child(child, ctag, level + 1, node)
                continue
            if ctag == "FORM":
                continue  # will be injected under FILE below
            if ("OBJE", ctag) in _CONTEXT_DROP:
                self._note_drop(f"OBJE.{ctag}")
                continue
            child_node = self._convert_element(
                child, level + 1, parent=node, parent_tag="OBJE"
            )
            # Inject FORM under FILE if the G5 file had a top-level OBJE.FORM.
            if ctag == "FILE" and child_node is not None and g5_form:
                has_form = any(c.tag == "FORM" for c in child_node.children)
                if not has_form:
                    GedcomStructure(
                        level=child_node.level + 1,
                        tag="FORM",
                        payload=g5_form,
                        parent=child_node,
                    )

        return node

    def _convert_element(
        self,
        el: Any,
        level: int,
        parent: Optional[GedcomStructure],
        force_tag: Optional[str] = None,
        parent_tag: str = "",
    ) -> Optional[GedcomStructure]:
        """Recursively convert one G5 element and all its descendants."""
        tag = force_tag or (el.tag or "").upper()
        if not tag:
            return None

        # Delegate OBJE to the specialised handler.
        if tag == "OBJE" and not force_tag:
            return self._convert_obje(el, level, parent)

        # xref only on level-0 records
        xref_raw = ""
        if level == 0:
            xref_raw = (
                getattr(el, "xref_id", None) or getattr(el, "xref", None) or ""
            ).strip()

        payload = self._merged_payload(el)

        # Normalise enumeration payloads that G5 sometimes stores in lowercase.
        if tag in _UPPERCASE_PAYLOAD and payload:
            payload = payload.upper()

        # Normalise non-standard date formats (e.g. ISO year ranges) to GEDCOM grammar.
        if tag == "DATE" and payload:
            payload = _normalize_date(payload)

        is_ptr = bool(payload and _POINTER_RE.match(payload.strip()))

        # Track extension tags for later SCHMA declaration.
        if tag.startswith("_"):
            self._ext_tags.add(tag)

        node = GedcomStructure(
            level=level,
            tag=tag,
            xref_id=xref_raw or None,
            payload=payload,
            payload_is_pointer=is_ptr,
            parent=parent,
        )

        try:
            children = el.get_child_elements()
        except (AttributeError, TypeError) as exc:
            log.debug("get_child_elements failed in _convert_element: {}", exc)
            children = []

        for child in children:
            ctag = (child.tag or "").upper()
            if ctag in _FOLD:
                continue  # content already folded into payload
            if ctag in _ALWAYS_DROP:
                self._note_drop(ctag)
                continue
            if ctag in _VENDOR_TAGS:
                self._handle_vendor_child(child, ctag, level + 1, node)
                continue
            if (tag, ctag) in _CONTEXT_DROP:
                self._note_drop(f"{tag}.{ctag}")
                continue
            self._convert_element(child, level + 1, parent=node, parent_tag=tag)

        return node
