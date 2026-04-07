"""
======================================================================
 Project: gedcomtools
 File:    gedcom5/validator5.py
 Purpose: GEDCOM 5.5.1 structural validator.

 Created: 2026-03-22
 Updated: 2026-04-07 — added phases 7-9; expanded payload checks for
                        AGE format, LDS STAT enumerations, GEDC.VERS
                        value, and HEAD.CHAR encoding.
======================================================================

Validates a parsed GEDCOM 5 element tree against the GEDCOM 5.5.1
specification rules defined in :mod:`gedcom5.specification5`.

Usage::

    from gedcomtools.gedcom5.gedcom5 import Gedcom5
    g = Gedcom5()
    g.loadfile("family.ged")
    issues = g.validate()        # list[ValidationIssue]
    for i in issues:
        print(i.severity, i.code, i.message)

The :class:`ValidationIssue` dataclass is shared with the GEDCOM 7
validator (imported from ``gedcom7.validator``).

Validation phases
-----------------
1. File-level structure (HEAD/TRLR presence, HEAD required children,
   GEDC.VERS value, HEAD.CHAR encoding).
2. Xref index construction and duplicate-xref detection.
3. Recursive structural validation (allowed children, cardinality,
   payload types including SEX, date, PEDI, QUAY, MEDI, RESN, AGE,
   and LDS ordinance STAT enumerations).
4. Pointer resolution (unresolved pointers, wrong target record type).
5. Bidirectional link consistency (FAMS/FAMC ↔ FAM.HUSB/WIFE/CHIL).
6. Orphaned citeable records (SOUR, REPO, OBJE, NOTE, SUBM never cited).
7. Xref format (max 20 inner characters, no embedded ``@`` or spaces).
8. Duplicate FAMC links (same family cited more than once per individual).
9. Self-referential ALIA (individual aliased to itself).
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from gedcomtools.gedcom7.validator import ValidationIssue
from gedcomtools.gedcom5 import specification5 as spec


# Regex to recognise a pointer payload (@...@)
_POINTER_RE = re.compile(r"^@[^@]+@$")

# Xref format: @<no-space, no-embedded-@>@, inner part max 20 chars
_XREF_ID_RE = re.compile(r"^@[^@ ]+@$")

# AGE format: optional < or >, then Ny[Nm[Nd]] | Nm[Nd] | Nw | Nd
_AGE_RE = re.compile(
    r"^[<>]?\s*(?:"
    r"\d+y(?:\s+\d+m(?:\s+\d+d)?)?"
    r"|\d+m(?:\s+\d+d)?"
    r"|\d+w"
    r"|\d+d"
    r")$",
    re.IGNORECASE,
)

# Recognised HEAD.CHAR encodings (core spec + common vendor values)
_KNOWN_CHAR_ENCODINGS: FrozenSet[str] = frozenset({
    "ANSEL", "ASCII", "UTF-8", "UNICODE", "ANSI", "IBMPC", "MACINTOSH",
})

# Valid HEAD.GEDC.VERS values
_KNOWN_GEDC_VERS: FrozenSet[str] = frozenset({"5.5", "5.5.1"})

# LDS ordinance parents that use LDS_STAT_ORD values
_LDS_ORD_PARENTS: FrozenSet[str] = frozenset({"BAPL", "CONL", "ENDL", "SLGC", "SLGS"})

# Tags whose value is always a pointer (to specific record types)
_ALWAYS_POINTER_TAGS: Dict[str, Set[str]] = {
    "FAMC": {"FAM"}, "FAMS": {"FAM"},
    "HUSB": {"INDI"}, "WIFE": {"INDI"}, "CHIL": {"INDI"},
    "ALIA": {"INDI"}, "ASSO": {"INDI"},
    "ANCI": {"SUBM"}, "DESI": {"SUBM"},
    "SUBM": {"SUBM"},
    "REPO": {"REPO"},
}

# Tags to silently skip in structure checks (CONC/CONT are parser artefacts)
_SKIP_TAGS: FrozenSet[str] = frozenset({"CONC", "CONT", "TRLR"})

# Record tags that should be cited from other records (orphan check)
_CITEABLE_RECORDS: FrozenSet[str] = frozenset({"SOUR", "REPO", "OBJE", "NOTE", "SUBM"})


def _norm(xref: str) -> str:
    return xref.strip().upper() if xref else ""


class Gedcom5Validator:
    """Validate a parsed GEDCOM 5.5.1 element tree.

    Args:
        parser: A Gedcom5 instance that has already parsed a ``.ged`` file.
    """

    def __init__(self, parser: Any) -> None:
        self._parser = parser
        self.issues: List[ValidationIssue] = []

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def validate(self) -> List[ValidationIssue]:
        """Run all validation phases and return the collected issues."""
        self.issues = []
        roots = self._parser.get_root_child_elements()
        xref_index = self._build_xref_index(roots)

        self._check_file_structure(roots)             # Phase 1
        # Phase 2 is _build_xref_index (called above)
        for el in roots:                               # Phase 3
            self._check_node(el, parent_tag=None, parent_is_record=False)
        self._check_pointers(roots, xref_index)       # Phase 4
        self._check_bidirectional(xref_index)         # Phase 5
        self._check_orphans(roots, xref_index)        # Phase 6
        self._check_xref_format(roots)                # Phase 7
        self._check_duplicate_famc(xref_index)        # Phase 8
        self._check_self_referential_alia(xref_index) # Phase 9
        return list(self.issues)

    # ------------------------------------------------------------------
    # Phase 1 — File structure
    # ------------------------------------------------------------------

    def _check_file_structure(self, roots: List[Any]) -> None:
        top_tags = [el.tag.upper() for el in roots]
        tag_counts: Counter = Counter(top_tags)

        if "HEAD" not in tag_counts:
            self._err("missing_head", "No HEAD record found.", tag="HEAD")
        elif tag_counts["HEAD"] > 1:
            self._err("duplicate_head", f"HEAD appears {tag_counts['HEAD']} times; expected 1.", tag="HEAD")

        if "TRLR" not in tag_counts:
            self._err("missing_trlr", "No TRLR record found.", tag="TRLR")
        elif top_tags[-1] != "TRLR":
            self._warn("trlr_not_last", "TRLR is not the last record.", tag="TRLR")

        # HEAD content checks
        head_els = [el for el in roots if el.tag.upper() == "HEAD"]
        if head_els:
            head = head_els[0]
            self._check_head_contents(head)

    def _check_head_contents(self, head: Any) -> None:
        child_tags = {c.tag.upper() for c in head.get_child_elements()}
        required = {"SOUR", "SUBM", "GEDC", "CHAR"}
        for req in required:
            if req not in child_tags:
                self._err(
                    "head_missing_required",
                    f"HEAD is missing required child {req}.",
                    tag=req, line=head._line_num,
                )
        # GEDC.VERS required and must be a known version
        gedc_els = [c for c in head.get_child_elements() if c.tag.upper() == "GEDC"]
        if gedc_els:
            gedc = gedc_els[0]
            vers_children = [c for c in gedc.get_child_elements() if c.tag.upper() == "VERS"]
            if not vers_children:
                self._err(
                    "head_gedc_no_vers",
                    "HEAD.GEDC is missing required VERS child.",
                    tag="VERS", line=gedc._line_num,
                )
            else:
                vers_val = (vers_children[0].get_value() or "").strip()
                if vers_val not in _KNOWN_GEDC_VERS:
                    self._warn(
                        "head_gedc_vers_value",
                        f"HEAD.GEDC.VERS value {vers_val!r} is not '5.5' or '5.5.1'.",
                        tag="VERS", line=vers_children[0]._line_num,
                    )

        # HEAD.CHAR must be a recognised encoding
        char_els = [c for c in head.get_child_elements() if c.tag.upper() == "CHAR"]
        if char_els:
            char_val = (char_els[0].get_value() or "").strip().upper()
            if char_val and char_val not in _KNOWN_CHAR_ENCODINGS:
                self._warn(
                    "head_char_unknown",
                    f"HEAD.CHAR value {char_val!r} is not a recognised GEDCOM 5 encoding.",
                    tag="CHAR", line=char_els[0]._line_num,
                )

    # ------------------------------------------------------------------
    # Phase 2 — Build xref index
    # ------------------------------------------------------------------

    def _build_xref_index(self, roots: List[Any]) -> Dict[str, Any]:
        index: Dict[str, Any] = {}
        seen_xrefs: Set[str] = set()
        for el in roots:
            if not el.xref:
                continue
            key = _norm(el.xref)
            if key in seen_xrefs:
                self._err(
                    "duplicate_xref",
                    f"Duplicate xref {el.xref!r}.",
                    tag=el.tag.upper(), line=el._line_num,
                )
            seen_xrefs.add(key)
            index[key] = el
        return index

    # ------------------------------------------------------------------
    # Phase 3 — Recursive structural validation
    # ------------------------------------------------------------------

    def _check_node(
        self,
        el: Any,
        parent_tag: Optional[str],
        parent_is_record: bool,
    ) -> None:
        tag = el.tag.upper() if el.tag else ""
        if tag in _SKIP_TAGS:
            return

        is_record = (el.level == 0 and bool(el.xref))
        line = el._line_num

        # Allowed-child check
        if parent_tag is not None:
            allowed = spec.allowed_children(parent_tag, is_record=parent_is_record)
            # Extension tags (starting with _) are always allowed
            if tag and not tag.startswith("_") and allowed and tag not in allowed:
                self._warn(
                    "unexpected_tag",
                    f"{tag} is not a recognised substructure of {parent_tag}.",
                    tag=tag, line=line,
                )

        # Cardinality — checked at parent level (see _check_cardinality)

        # Payload type check
        self._check_payload(el, tag, is_record, parent_tag=parent_tag)

        # Recurse: collect child tags, check cardinality for this node
        children = el.get_child_elements()
        child_tag_counts: Counter = Counter(
            c.tag.upper() for c in children if c.tag.upper() not in _SKIP_TAGS
        )
        rule = spec.rule_for(tag, is_record=is_record)
        if rule:
            self._check_cardinality(tag, is_record, child_tag_counts, line)

        for child in children:
            self._check_node(child, parent_tag=tag, parent_is_record=is_record)

    def _check_payload(
        self,
        el: Any,
        tag: str,
        is_record: bool,
        *,
        parent_tag: Optional[str] = None,
    ) -> None:
        value = (el.get_value() or "").strip()
        line = el._line_num

        rule = spec.rule_for(tag, is_record=is_record)
        if rule is None:
            return

        ptype = rule.get("payload_type", "text")

        if ptype == "none" and value:
            # Tolerate — many real files put notes on structural tags
            pass

        elif ptype == "sex" and value and value.upper() not in spec.SEX_VALUES:
            self._warn(
                "invalid_sex_value",
                f"SEX value {value!r} is not one of {sorted(spec.SEX_VALUES)}.",
                tag=tag, line=line,
            )

        elif ptype == "date" and value:
            if not spec.is_valid_date(value):
                self._warn(
                    "invalid_date_format",
                    f"Date value {value!r} does not match the GEDCOM 5.5.1 date grammar.",
                    tag=tag, line=line,
                )

        # Pointer-only tags
        if tag in _ALWAYS_POINTER_TAGS and value and not _POINTER_RE.match(value):
            self._warn(
                "expected_pointer",
                f"{tag} payload {value!r} should be a pointer (@XREF@).",
                tag=tag, line=line,
            )

        # Specific enum checks
        if tag == "PEDI" and value and value.upper() not in spec.PEDI_VALUES:
            self._warn(
                "invalid_pedi_value",
                f"PEDI value {value!r} is not one of {sorted(spec.PEDI_VALUES)}.",
                tag=tag, line=line,
            )
        if tag == "QUAY" and value and value not in spec.QUAY_VALUES:
            self._warn(
                "invalid_quay_value",
                f"QUAY value {value!r} is not one of {sorted(spec.QUAY_VALUES)}.",
                tag=tag, line=line,
            )
        if tag == "MEDI" and value and value.upper() not in spec.MEDI_VALUES:
            self._warn(
                "invalid_medi_value",
                f"MEDI value {value!r} is not a recognised media type.",
                tag=tag, line=line,
            )
        if tag == "RESN" and value and value.upper() not in spec.RESN_VALUES:
            self._warn(
                "invalid_resn_value",
                f"RESN value {value!r} is not one of {sorted(spec.RESN_VALUES)}.",
                tag=tag, line=line,
            )

        # A4: AGE payload format
        if tag == "AGE" and value and not _AGE_RE.match(value):
            self._warn(
                "invalid_age_format",
                f"AGE value {value!r} does not match the GEDCOM age format "
                "(e.g. '30y', '2m 10d', '< 1y 6m').",
                tag=tag, line=line,
            )

        # A3: LDS ordinance STAT enumeration
        if tag == "STAT" and value:
            val_upper = value.upper()
            if parent_tag in _LDS_ORD_PARENTS:
                if val_upper not in spec.LDS_STAT_ORD:
                    self._warn(
                        "invalid_lds_stat_ord",
                        f"LDS ordinance STAT value {value!r} is not a recognised "
                        f"ordinance status (parent: {parent_tag}).",
                        tag=tag, line=line,
                    )
            elif parent_tag == "FAMC":
                if val_upper not in spec.LDS_STAT_CHILD:
                    self._warn(
                        "invalid_lds_stat_child",
                        f"FAMC.STAT value {value!r} is not one of "
                        f"{sorted(spec.LDS_STAT_CHILD)}.",
                        tag=tag, line=line,
                    )

    def _check_cardinality(
        self,
        tag: str,
        is_record: bool,
        child_counts: Counter,
        line: Optional[int],
    ) -> None:
        rule = spec.rule_for(tag, is_record=is_record)
        if not rule:
            return
        card_rules: Dict = rule.get("cardinality", {})
        for child_tag, card in card_rules.items():
            lo, hi = card
            count = child_counts.get(child_tag, 0)
            if lo > 0 and count < lo:
                self._err(
                    "missing_required_child",
                    f"{tag} requires at least {lo} {child_tag} child(ren); found {count}.",
                    tag=child_tag, line=line,
                )
            if hi is not None and count > hi:
                self._err(
                    "too_many_children",
                    f"{tag} allows at most {hi} {child_tag} child(ren); found {count}.",
                    tag=child_tag, line=line,
                )

    # ------------------------------------------------------------------
    # Phase 4 — Pointer resolution
    # ------------------------------------------------------------------

    def _check_pointers(self, roots: List[Any], xref_index: Dict[str, Any]) -> None:
        def _walk(el: Any) -> None:
            tag = el.tag.upper() if el.tag else ""
            value = (el.get_value() or "").strip()
            if value and _POINTER_RE.match(value):
                key = _norm(value)
                if key not in xref_index:
                    self._err(
                        "unresolved_pointer",
                        f"{tag} points to {value!r} which does not exist.",
                        tag=tag, line=el._line_num,
                    )
                else:
                    # Check target record type
                    expected_types = _ALWAYS_POINTER_TAGS.get(tag)
                    if expected_types:
                        target = xref_index[key]
                        target_tag = target.tag.upper()
                        if target_tag not in expected_types:
                            self._err(
                                "wrong_pointer_target",
                                f"{tag} points to {value!r} ({target_tag}); "
                                f"expected {sorted(expected_types)}.",
                                tag=tag, line=el._line_num,
                            )
            for child in el.get_child_elements():
                _walk(child)

        for el in roots:
            _walk(el)

    # ------------------------------------------------------------------
    # Phase 5 — Bidirectional link consistency
    # ------------------------------------------------------------------

    def _check_bidirectional(self, xref_index: Dict[str, Any]) -> None:
        indi_elements = [el for el in xref_index.values() if el.tag.upper() == "INDI"]
        fam_elements  = [el for el in xref_index.values() if el.tag.upper() == "FAM"]

        # Build FAM membership maps from the FAM records themselves
        fam_husb: Dict[str, Set[str]] = defaultdict(set)   # fam_xref → indi_xref(s)
        fam_wife: Dict[str, Set[str]] = defaultdict(set)
        fam_chil: Dict[str, Set[str]] = defaultdict(set)

        for fam in fam_elements:
            fk = _norm(fam.xref)
            for child in fam.get_child_elements():
                ctag = child.tag.upper()
                val = _norm(child.get_value() or "")
                if not val:
                    continue
                if ctag == "HUSB":
                    fam_husb[fk].add(val)
                elif ctag == "WIFE":
                    fam_wife[fk].add(val)
                elif ctag == "CHIL":
                    fam_chil[fk].add(val)

        # Check each INDI's FAMS / FAMC links against FAM records
        for indi in indi_elements:
            ik = _norm(indi.xref)
            for child in indi.get_child_elements():
                ctag = child.tag.upper()
                fam_xref = _norm(child.get_value() or "")
                if not fam_xref:
                    continue

                if ctag == "FAMS":
                    husb_ok = ik in fam_husb.get(fam_xref, set())
                    wife_ok = ik in fam_wife.get(fam_xref, set())
                    if not husb_ok and not wife_ok:
                        self._warn(
                            "broken_fams_link",
                            f"INDI {indi.xref} has FAMS {child.get_value()!r} "
                            f"but FAM {child.get_value()!r} does not list this individual "
                            "as HUSB or WIFE.",
                            tag="FAMS", line=child._line_num,
                        )

                elif ctag == "FAMC":
                    if ik not in fam_chil.get(fam_xref, set()):
                        self._warn(
                            "broken_famc_link",
                            f"INDI {indi.xref} has FAMC {child.get_value()!r} "
                            f"but FAM {child.get_value()!r} does not list this individual "
                            "as CHIL.",
                            tag="FAMC", line=child._line_num,
                        )

        # Reverse: each FAM.HUSB/WIFE/CHIL must have a back-link
        for fam in fam_elements:
            fk = _norm(fam.xref)
            for child in fam.get_child_elements():
                ctag = child.tag.upper()
                val = child.get_value() or ""
                ik = _norm(val)
                if not ik or ctag not in ("HUSB", "WIFE", "CHIL"):
                    continue
                target = xref_index.get(ik)
                if target is None or target.tag.upper() != "INDI":
                    continue
                indi_fams = {_norm(c.get_value() or "") for c in target.get_child_elements()
                             if c.tag.upper() == "FAMS"}
                indi_famc = {_norm(c.get_value() or "") for c in target.get_child_elements()
                             if c.tag.upper() == "FAMC"}
                fam_xref_norm = _norm(fam.xref)

                if ctag in ("HUSB", "WIFE") and fam_xref_norm not in indi_fams:
                    self._warn(
                        "missing_fams_backlink",
                        f"FAM {fam.xref} lists {val!r} as {ctag} but "
                        f"INDI {val!r} has no FAMS {fam.xref!r}.",
                        tag=ctag, line=child._line_num,
                    )
                elif ctag == "CHIL" and fam_xref_norm not in indi_famc:
                    self._warn(
                        "missing_famc_backlink",
                        f"FAM {fam.xref} lists {val!r} as CHIL but "
                        f"INDI {val!r} has no FAMC {fam.xref!r}.",
                        tag="CHIL", line=child._line_num,
                    )

    # ------------------------------------------------------------------
    # Phase 6 — Orphaned records
    # ------------------------------------------------------------------

    def _check_orphans(self, roots: List[Any], xref_index: Dict[str, Any]) -> None:
        # Collect all pointer values mentioned anywhere in the file
        cited: Set[str] = set()

        def _collect(el: Any) -> None:
            val = (el.get_value() or "").strip()
            if val and _POINTER_RE.match(val):
                cited.add(_norm(val))
            for child in el.get_child_elements():
                _collect(child)

        for el in roots:
            _collect(el)

        # Any citeable record not mentioned is orphaned
        for el in roots:
            if not el.xref:
                continue
            tag = el.tag.upper()
            if tag in _CITEABLE_RECORDS:
                key = _norm(el.xref)
                if key not in cited:
                    self._warn(
                        "orphaned_record",
                        f"{tag} record {el.xref!r} is never referenced.",
                        tag=tag, line=el._line_num,
                    )

    # ------------------------------------------------------------------
    # Phase 7 — Xref format
    # ------------------------------------------------------------------

    def _check_xref_format(self, roots: List[Any]) -> None:
        for el in roots:
            if not el.xref:
                continue
            xref = el.xref
            line = el._line_num
            if not _XREF_ID_RE.match(xref):
                self._err(
                    "invalid_xref_format",
                    f"Xref {xref!r} contains invalid characters (spaces or embedded '@').",
                    tag=el.tag.upper(), line=line,
                )
                continue
            # Inner part (strip leading/trailing @) must be 1-20 characters
            inner = xref[1:-1]
            if len(inner) > 20:
                self._warn(
                    "xref_too_long",
                    f"Xref {xref!r} inner identifier is {len(inner)} characters; "
                    "the GEDCOM 5.5.1 maximum is 20.",
                    tag=el.tag.upper(), line=line,
                )

    # ------------------------------------------------------------------
    # Phase 8 — Duplicate FAMC links
    # ------------------------------------------------------------------

    def _check_duplicate_famc(self, xref_index: Dict[str, Any]) -> None:
        for el in xref_index.values():
            if el.tag.upper() != "INDI":
                continue
            seen: Set[str] = set()
            for child in el.get_child_elements():
                if child.tag.upper() != "FAMC":
                    continue
                target = _norm(child.get_value() or "")
                if not target:
                    continue
                if target in seen:
                    self._warn(
                        "duplicate_famc",
                        f"INDI {el.xref} has more than one FAMC link to {child.get_value()!r}.",
                        tag="FAMC", line=child._line_num,
                    )
                else:
                    seen.add(target)

    # ------------------------------------------------------------------
    # Phase 9 — Self-referential ALIA
    # ------------------------------------------------------------------

    def _check_self_referential_alia(self, xref_index: Dict[str, Any]) -> None:
        for el in xref_index.values():
            if el.tag.upper() != "INDI":
                continue
            ik = _norm(el.xref)
            for child in el.get_child_elements():
                if child.tag.upper() != "ALIA":
                    continue
                target = _norm(child.get_value() or "")
                if target and target == ik:
                    self._err(
                        "self_referential_alia",
                        f"INDI {el.xref} has an ALIA pointer that references itself.",
                        tag="ALIA", line=child._line_num,
                    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _err(
        self,
        code: str,
        message: str,
        *,
        tag: Optional[str] = None,
        line: Optional[int] = None,
    ) -> None:
        self.issues.append(ValidationIssue(
            code=code, message=message, line_num=line, tag=tag, severity="error",
        ))

    def _warn(
        self,
        code: str,
        message: str,
        *,
        tag: Optional[str] = None,
        line: Optional[int] = None,
    ) -> None:
        self.issues.append(ValidationIssue(
            code=code, message=message, line_num=line, tag=tag, severity="warning",
        ))
