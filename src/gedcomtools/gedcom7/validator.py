"""
======================================================================
 Project: gedcomtools
 File:    gedcom7/validator.py
 Author:  David J. Cartwright
 Purpose: Multi-phase GEDCOM 7 structural and semantic validator.

 Created: 2026-03-01
 Updated:
   - 2026-03-15: added INT date format; MEDI/PEDI/ROLE enum validation;
                 orphaned record detection; line-length warning;
                 TRAN context validation; @VOID@ restriction check
   - 2026-03-16: extended TRAN context for NAME.TRAN and PLAC.TRAN
   - 2026-03-16: fix pointer case-sensitivity (normalize xrefs to uppercase);
                 wire FAMC.STAT context enum; catch malformed @@ pointer;
                 validate required xref ids on top-level records; VERS format check;
                 FILE.TRAN now checks for MIME in addition to FORM;
                 TRAN invalid-parent check; DATE INT regex tightened;
                 orphaned check uses broader pointer detection to catch HEAD.SOUR refs;
                 SDATE added to _TRAN_LEGAL_PARENTS
   - 2026-03-16: import updated GedcomStructure.py → structure.py
   - 2026-03-22: AGE regex adds week (Nw) support; SNOTE.LANG cardinality fix;
                 self-referential ALIA/SOUR-OBJE cycle detection; NO-context
                 validation; duplicate FAMC/CHIL detection; EXID-without-TYPE
                 and ADR1/ADR2/ADR3 deprecation warnings (changelog 7.0.6–7.0.17)
======================================================================

This module performs structural and semantic validation of parsed GEDCOM 7
trees.

Validation phases:

1. file-level validation
2. parent/child legality validation
3. child cardinality validation
4. basic payload validation
5. pointer validation
6. selected enumeration validation
7. payload format validation (DATE, TIME, AGE, LATI, LONG, LANG, RESN)
8. orphaned record detection
9. bidirectional pointer consistency
10. TRAN context validation
11. deprecated tag warnings (ADR1/ADR2/ADR3, EXID without TYPE)
12. NO-tag context validation
13. self-referential ALIA detection
14. SOUR-OBJE cycle detection
15. duplicate FAMC/CHIL link detection

The docstrings are written in Google style so they render well with
Sphinx Napoleon.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set

from .structure import GedcomStructure
from . import specification as g7specs
from .g7interop import is_known_tag

# ---------------------------------------------------------------------------
# Pre-compiled payload format patterns
# ---------------------------------------------------------------------------

_MONTH = r"(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)"
_YEAR  = r"\d{1,4}(?:/\d{2})?"   # year, optional dual year e.g. 1700/01
_CAL   = r"(?:@#D[A-Z ]+@\s*)?"  # optional calendar escape @#DGREGORIAN@ etc.

# One date part: optional calendar escape + (day month year | month year | year)
_DP = (
    rf"(?:{_CAL}"
    rf"(?:\d{{1,2}}\s+{_MONTH}\s+{_YEAR}"
    rf"|{_MONTH}\s+{_YEAR}"
    rf"|{_YEAR}))"
)

_DATE_RE = re.compile(
    rf"^(?:{_DP}|(?:ABT|CAL|EST)\s+{_DP}|BEF\s+{_DP}|AFT\s+{_DP}"
    rf"|FROM\s+{_DP}(?:\s+TO\s+{_DP})?|TO\s+{_DP}|BET\s+{_DP}\s+AND\s+{_DP}"
    rf"|INT\s+\S[^(]*\([^)]+\))$",
    re.IGNORECASE,
)

# hh:mm or h:mm, optional seconds, optional fraction, optional timezone
_TIME_RE = re.compile(
    r"^\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{4})?$"
)

# [< | >] then exactly one of: Ny[Nm[Nd]] | Nm[Nd] | Nw | Nd
# Weeks (Nw) are standalone per the GEDCOM 7 ABNF (7.0.0+).
_AGE_RE = re.compile(
    r"^[<>]?\s*(?:"
    r"\d+y(?:\s+\d+m(?:\s+\d+d)?)?"   # years [months [days]]
    r"|\d+m(?:\s+\d+d)?"               # months [days]
    r"|\d+w"                            # weeks (standalone)
    r"|\d+d"                            # days
    r")$",
    re.IGNORECASE,
)

_LATI_RE = re.compile(r"^[NS]\d+(?:\.\d+)?$", re.IGNORECASE)
_LONG_RE = re.compile(r"^[EW]\d+(?:\.\d+)?$", re.IGNORECASE)

# BCP 47: primary (2-8 letters) + optional subtags
_LANG_RE = re.compile(r"^[a-zA-Z]{2,8}(?:-[a-zA-Z0-9]{2,8})*$")

# Xref must be @<non-empty, no embedded @, no spaces>@
_XREF_RE = re.compile(r"^@[^@ ]+@$")

_RESN_VALID = frozenset({"CONFIDENTIAL", "LOCKED", "PRIVACY"})

# Maps tag name → (compiled regex, error code, human-readable description)
_FORMAT_CHECKS: dict = {
    "DATE": (_DATE_RE, "invalid_date_format",  "DATE payload does not match GEDCOM date grammar"),
    "TIME": (_TIME_RE, "invalid_time_format",  "TIME payload does not match hh:mm[:ss[.frac]][Z|±hhmm]"),
    "AGE":  (_AGE_RE,  "invalid_age_format",   "AGE payload does not match [<>] Ny[Nm[Nd]] | Nm[Nd] | Nw | Nd"),
    "LATI": (_LATI_RE, "invalid_lati_format",  "LATI must be N or S followed by decimal degrees"),
    "LONG": (_LONG_RE, "invalid_long_format",  "LONG must be E or W followed by decimal degrees"),
    "LANG": (_LANG_RE, "invalid_lang_format",  "LANG must be a valid BCP 47 language tag"),
}


@dataclass(slots=True)
class ValidationIssue:
    """Represents a GEDCOM validation issue.

    Attributes:
        code: Stable machine-readable issue code.
        message: Human-readable issue description.
        line_num: Source line number if available.
        tag: GEDCOM tag associated with the issue.
        severity: Issue severity. Usually ``"error"`` or ``"warning"``.
    """

    code: str
    message: str
    line_num: Optional[int] = None
    tag: Optional[str] = None
    severity: str = "error"


class GedcomValidator:
    """Validate a parsed GEDCOM 7 dataset.

    Args:
        records: Parsed top-level GEDCOM records.
        strict_extensions: Whether undeclared extension tags should be errors.
    """

    def __init__(
        self,
        records: List[GedcomStructure],
        *,
        strict_extensions: bool = True,
    ) -> None:
        """Initialize the validator.

        Args:
            records: Parsed top-level records.
            strict_extensions: Whether extension tags require declaration.
        """
        self.records = records
        self.strict_extensions = strict_extensions
        self.issues: List[ValidationIssue] = []
        self._xref_index: Dict[str, GedcomStructure] = {}
        self._declared_extension_tags: Set[str] = set()

    def add_issue(
        self,
        code: str,
        message: str,
        *,
        line_num: Optional[int] = None,
        tag: Optional[str] = None,
        severity: str = "error",
    ) -> None:
        """Add a validation issue.

        Args:
            code: Stable machine-readable issue code.
            message: Human-readable issue text.
            line_num: Source line number if available.
            tag: GEDCOM tag associated with the issue.
            severity: Issue severity.
        """
        self.issues.append(
            ValidationIssue(
                code=code,
                message=message,
                line_num=line_num,
                tag=tag,
                severity=severity,
            )
        )

    def validate(self) -> List[ValidationIssue]:
        """Run all validation phases.

        Returns:
            Collected validation issues.
        """
        self.validate_file_structure()
        self.index_xrefs()
        self.collect_declared_extension_tags()

        for record in self.records:
            self.validate_node(record)

        self.validate_pointers()
        self.validate_bidirectional_links()
        self.validate_orphaned_records()
        self.validate_self_referential_links()
        self.validate_pointer_cycles()
        self.validate_duplicate_family_links()
        return self.issues

    def walk(self) -> Iterable[GedcomStructure]:
        """Yield all nodes in the dataset depth-first."""
        for record in self.records:
            yield from self.walk_node(record)

    def walk_node(self, node: GedcomStructure) -> Iterable[GedcomStructure]:
        """Yield a node and all descendants.

        Args:
            node: Root node to walk.
        """
        yield node
        for child in node.children:
            yield from self.walk_node(child)

    def validate_file_structure(self) -> None:
        """Validate required GEDCOM file-level rules."""
        if not self.records:
            self.add_issue(
                "empty_file",
                "GEDCOM file contains no top-level records.",
            )
            return

        if self.records[0].tag != g7specs.HEAD:
            self.add_issue(
                "missing_head_first",
                "First top-level record must be HEAD.",
                line_num=self.records[0].line_num,
                tag=self.records[0].tag,
            )

        if self.records[-1].tag != g7specs.TRLR:
            self.add_issue(
                "missing_trlr_last",
                "Last top-level record must be TRLR.",
                line_num=self.records[-1].line_num,
                tag=self.records[-1].tag,
            )

        counts = Counter(record.tag for record in self.records)

        if counts[g7specs.HEAD] != 1:
            self.add_issue(
                "invalid_head_count",
                f"Expected exactly one HEAD record, found {counts[g7specs.HEAD]}.",
                tag=g7specs.HEAD,
            )

        if counts[g7specs.TRLR] != 1:
            self.add_issue(
                "invalid_trlr_count",
                f"Expected exactly one TRLR record, found {counts[g7specs.TRLR]}.",
                tag=g7specs.TRLR,
            )

        head = next((record for record in self.records if record.tag == g7specs.HEAD), None)
        if head is None:
            return

        gedc = head.first_child(g7specs.GEDC)
        if gedc is None:
            self.add_issue(
                "missing_gedc",
                "HEAD must contain GEDC.",
                line_num=head.line_num,
                tag=head.tag,
            )
        else:
            vers = gedc.first_child("VERS")
            if vers is None or not vers.payload.strip():
                self.add_issue(
                    "missing_gedc_vers",
                    "HEAD.GEDC should contain VERS with a GEDCOM version.",
                    line_num=gedc.line_num,
                    tag="VERS",
                )
            elif not re.match(r"^\d+\.\d+", vers.payload.strip()):
                self.add_issue(
                    "invalid_gedc_vers_format",
                    f"HEAD.GEDC.VERS value {vers.payload.strip()!r} does not look like "
                    "a valid version number (expected e.g. '7.0').",
                    line_num=vers.line_num,
                    tag="VERS",
                    severity="warning",
                )

        # INDI, FAM, OBJE, REPO, SNOTE, SOUR, SUBM must have xref ids.
        # HEAD and TRLR must not.
        _REQUIRES_XREF = {"INDI", "FAM", "OBJE", "REPO", "SNOTE", "SOUR", "SUBM"}
        _FORBIDS_XREF  = {"HEAD", "TRLR"}
        for record in self.records:
            if record.tag in _REQUIRES_XREF and not record.xref_id:
                self.add_issue(
                    "missing_xref_id",
                    f"{record.tag} record at line {record.line_num} must have an xref id.",
                    line_num=record.line_num,
                    tag=record.tag,
                )
            elif record.tag in _FORBIDS_XREF and record.xref_id:
                self.add_issue(
                    "unexpected_xref_id",
                    f"{record.tag} record must not have an xref id "
                    f"(found {record.xref_id!r}).",
                    line_num=record.line_num,
                    tag=record.tag,
                )

    def index_xrefs(self) -> None:
        """Build an index of all defined xref ids."""
        self._xref_index.clear()

        for node in self.walk():
            if not node.xref_id:
                continue

            self.validate_xref_format(node)

            key = node.xref_id.upper()
            if key in self._xref_index:
                self.add_issue(
                    "duplicate_xref",
                    f"Duplicate xref id {node.xref_id!r}.",
                    line_num=node.line_num,
                    tag=node.tag,
                )
            else:
                self._xref_index[key] = node

    def collect_declared_extension_tags(self) -> None:
        """Collect extension tags declared in ``HEAD.SCHMA.TAG``."""
        self._declared_extension_tags.clear()

        head = next((record for record in self.records if record.tag == g7specs.HEAD), None)
        if head is None:
            return

        for schema in head.get_children(g7specs.SCHMA):
            for tag_node in schema.get_children("TAG"):
                if not tag_node.payload:
                    continue
                parts = tag_node.payload.split(maxsplit=1)
                if parts:
                    self._declared_extension_tags.add(parts[0].upper())

    def validate_node(self, node: GedcomStructure) -> None:
        """Validate a node and its descendants.

        Args:
            node: Node to validate.
        """
        self.validate_known_tag(node)
        self.validate_extension_usage(node)
        self.validate_level(node)
        self.validate_child_legality(node)
        self.validate_cardinality(node)
        self.validate_payload(node)
        self.validate_payload_format(node)
        self.validate_enumeration(node)
        self.validate_tran_context(node)
        self.validate_void_pointer(node)
        self.validate_deprecated_tag(node)
        self.validate_exid_type(node)
        self.validate_no_context(node)

        for child in node.children:
            self.validate_node(child)

    def validate_known_tag(self, node: GedcomStructure) -> None:
        """Validate that a tag is known or an extension.

        Args:
            node: Node to validate.
        """
        if node.tag.startswith("_"):
            return

        if not is_known_tag(node.tag):
            self.add_issue(
                "unknown_tag",
                f"Unknown GEDCOM tag {node.tag!r}.",
                line_num=node.line_num,
                tag=node.tag,
            )

    def validate_extension_usage(self, node: GedcomStructure) -> None:
        """Validate extension tag declaration.

        Args:
            node: Node to validate.
        """
        if not node.tag.startswith("_"):
            return

        if not self.strict_extensions:
            return

        if node.tag not in self._declared_extension_tags:
            self.add_issue(
                "undeclared_extension_tag",
                f"Extension tag {node.tag!r} is not declared in HEAD.SCHMA.TAG.",
                line_num=node.line_num,
                tag=node.tag,
            )

    def validate_level(self, node: GedcomStructure) -> None:
        """Validate level stepping.

        Args:
            node: Node to validate.
        """
        if node.parent is None:
            if node.level != 0:
                self.add_issue(
                    "invalid_top_level",
                    "Top-level records must have level 0.",
                    line_num=node.line_num,
                    tag=node.tag,
                )
            return

        if node.level != node.parent.level + 1:
            self.add_issue(
                "invalid_level_step",
                "Child level must be exactly parent level + 1.",
                line_num=node.line_num,
                tag=node.tag,
            )

    def validate_child_legality(self, node: GedcomStructure) -> None:
        """Validate parent/child legality.

        Args:
            node: Node to validate.
        """
        if node.parent is None:
            if not g7specs.is_allowed_child(None, node.tag):
                self.add_issue(
                    "illegal_top_level_record",
                    f"Illegal top-level record tag {node.tag!r}.",
                    line_num=node.line_num,
                    tag=node.tag,
                )
            return

        if not g7specs.is_allowed_child(node.parent.tag, node.tag):
            self.add_issue(
                "illegal_substructure",
                f"Tag {node.tag!r} is not allowed under {node.parent.tag!r}.",
                line_num=node.line_num,
                tag=node.tag,
            )

    def validate_cardinality(self, node: GedcomStructure) -> None:
        """Validate child cardinality for a parent node.

        Args:
            node: Parent node whose children should be checked.
        """
        counts = Counter(child.tag for child in node.children)

        for child_tag in g7specs.allowed_child_tags(node.tag):
            rule = g7specs.get_cardinality(node.tag, child_tag)
            if rule is None:
                continue

            min_count, max_count = rule
            actual = counts.get(child_tag, 0)

            if actual < min_count:
                self.add_issue(
                    "missing_required_child",
                    (
                        f"Tag {child_tag!r} appears {actual} times under "
                        f"{node.tag!r}, minimum is {min_count}."
                    ),
                    line_num=node.line_num,
                    tag=child_tag,
                )

            if max_count is not None and actual > max_count:
                self.add_issue(
                    "cardinality_exceeded",
                    (
                        f"Tag {child_tag!r} appears {actual} times under "
                        f"{node.tag!r}, maximum is {max_count}."
                    ),
                    line_num=node.line_num,
                    tag=child_tag,
                )

    def validate_payload(self, node: GedcomStructure) -> None:
        """Validate basic payload typing.

        Args:
            node: Node to validate.
        """
        payload_type = g7specs.get_payload_type(node.tag)

        if payload_type == g7specs.PAYLOAD_NONE:
            if node.payload.strip():
                self.add_issue(
                    "unexpected_payload",
                    f"{node.tag} must not have a payload.",
                    line_num=node.line_num,
                    tag=node.tag,
                )

        elif payload_type == g7specs.PAYLOAD_POINTER:
            if not node.payload_is_pointer:
                self.add_issue(
                    "pointer_required",
                    f"{node.tag} must use a pointer payload.",
                    line_num=node.line_num,
                    tag=node.tag,
                )

        # GEDCOM 7 recommends lines ≤ 255 chars.
        # Estimate assembled line length: level + space + [xref + space] + tag + space + payload
        if node.payload:
            xref_part = len(node.xref_id) + 1 if node.xref_id else 0
            # level digits + space + xref_part + tag + space + first line of payload
            first_payload_line = node.payload.split("\n")[0]
            estimated = len(str(node.level)) + 1 + xref_part + len(node.tag) + 1 + len(first_payload_line)
            if estimated > 255:
                self.add_issue(
                    "line_too_long",
                    f"{node.tag} line is approximately {estimated} chars; GEDCOM 7 recommends ≤ 255.",
                    line_num=node.line_num,
                    tag=node.tag,
                    severity="warning",
                )

        if node.tag == "TRLR" and node.children:
            self.add_issue(
                "trlr_has_children",
                "TRLR must not have child structures.",
                line_num=node.line_num,
                tag=node.tag,
            )

    def validate_enumeration(self, node: GedcomStructure) -> None:
        """Validate selected enumeration payloads.

        Checks the general enum for the tag first; if none is registered,
        falls back to context-specific enums keyed on (tag, parent_tag).

        Args:
            node: Node to validate.
        """
        parent_tag = node.parent.tag if node.parent else None
        values = g7specs.get_enum_values(node.tag)

        if values is None:
            # Fall back to context-specific enum (e.g. FAMC.STAT)
            ctx = g7specs.get_context_enum_values(node.tag, parent_tag)
            if ctx is None:
                return
            value = node.payload.strip()
            if value and value not in ctx:
                self.add_issue(
                    "invalid_enumeration_value",
                    f"{node.tag} under {parent_tag} has invalid value {value!r}. "
                    f"Allowed: {sorted(ctx)}.",
                    line_num=node.line_num,
                    tag=node.tag,
                )
            return

        value = node.payload.strip()
        if value and value not in values:
            self.add_issue(
                "invalid_enumeration_value",
                f"{node.tag} has invalid value {value!r}.",
                line_num=node.line_num,
                tag=node.tag,
            )

    def validate_pointers(self) -> None:
        """Validate pointer targets."""
        for node in self.walk():
            if not node.payload_is_pointer:
                continue

            target = node.payload.strip()
            if target.upper() == "@VOID@":
                # @VOID@ is a valid sentinel meaning "intentionally no target"
                continue

            # Fix 8: catch malformed pointer like @@
            if not _XREF_RE.match(target):
                self.add_issue(
                    "malformed_pointer",
                    f"Pointer value {target!r} is not a valid xref id.",
                    line_num=node.line_num,
                    tag=node.tag,
                )
                continue

            if target.upper() not in self._xref_index:
                self.add_issue(
                    "dangling_pointer",
                    f"Pointer target {target!r} does not exist.",
                    line_num=node.line_num,
                    tag=node.tag,
                )

    def validate_bidirectional_links(self) -> None:
        """Validate bidirectional pointer consistency between INDI and FAM records.

        Checks:
        - INDI.FAMC @FAM@ → that FAM must have CHIL @INDI@ pointing back
        - INDI.FAMS @FAM@ → that FAM must have HUSB or WIFE @INDI@ pointing back
        - FAM.CHIL @INDI@ → that INDI must have FAMC @FAM@ pointing back
        """
        # Build maps from xref (uppercased) → set of pointer values (uppercased)
        def _pointer_set(record: GedcomStructure, tag: str) -> set:
            return {
                child.payload.strip().upper()
                for child in record.get_children(tag)
                if child.payload_is_pointer
                and child.payload.strip().upper() != "@VOID@"
            }

        indi_records = {
            node.xref_id.upper(): node
            for node in self.records
            if node.tag == "INDI" and node.xref_id
        }
        fam_records = {
            node.xref_id.upper(): node
            for node in self.records
            if node.tag == "FAM" and node.xref_id
        }

        for indi_xref, indi in indi_records.items():
            # INDI.FAMC → FAM must have CHIL back
            for famc in indi.get_children("FAMC"):
                fam_xref = famc.payload.strip().upper()
                if fam_xref == "@VOID@" or fam_xref not in fam_records:
                    continue
                fam = fam_records[fam_xref]
                if indi_xref not in _pointer_set(fam, "CHIL"):
                    self.add_issue(
                        "missing_back_pointer",
                        (
                            f"INDI {indi_xref!r} has FAMC pointing to {fam_xref!r}, "
                            f"but that FAM has no CHIL pointing back."
                        ),
                        line_num=famc.line_num,
                        tag="FAMC",
                        severity="warning",
                    )

            # INDI.FAMS → FAM must have HUSB or WIFE back
            for fams in indi.get_children("FAMS"):
                fam_xref = fams.payload.strip().upper()
                if fam_xref == "@VOID@" or fam_xref not in fam_records:
                    continue
                fam = fam_records[fam_xref]
                spouses = _pointer_set(fam, "HUSB") | _pointer_set(fam, "WIFE")
                if indi_xref not in spouses:
                    self.add_issue(
                        "missing_back_pointer",
                        (
                            f"INDI {indi_xref!r} has FAMS pointing to {fam_xref!r}, "
                            f"but that FAM has no HUSB/WIFE pointing back."
                        ),
                        line_num=fams.line_num,
                        tag="FAMS",
                        severity="warning",
                    )

        for fam_xref, fam in fam_records.items():
            # FAM.CHIL → INDI must have FAMC back
            for chil in fam.get_children("CHIL"):
                indi_xref = chil.payload.strip().upper()
                if indi_xref == "@VOID@" or indi_xref not in indi_records:
                    continue
                indi = indi_records[indi_xref]
                if fam_xref not in _pointer_set(indi, "FAMC"):
                    self.add_issue(
                        "missing_back_pointer",
                        (
                            f"FAM {fam_xref!r} has CHIL pointing to {indi_xref!r}, "
                            f"but that INDI has no FAMC pointing back."
                        ),
                        line_num=chil.line_num,
                        tag="CHIL",
                        severity="warning",
                    )

    def validate_tran_context(self, node: GedcomStructure) -> None:
        """Validate TRAN substructures match their parent context.

        TRAN under NOTE/SNOTE must have LANG, may have MIME.
        TRAN under NAME must have LANG, may have NAME-part subs (GIVN, SURN…).
        TRAN under PLAC must have LANG, may have PLAC subs (MAP, FORM…).
        TRAN under FILE must have LANG plus FORM and MIME.

        Args:
            node: Node to validate (any node; only acts on TRAN nodes).
        """
        if node.tag != "TRAN":
            return
        if node.parent is None:
            return

        _TRAN_LEGAL_PARENTS = {"NOTE", "SNOTE", "FILE", "NAME", "PLAC", "SDATE"}
        parent_tag = node.parent.tag
        if parent_tag not in _TRAN_LEGAL_PARENTS:
            self.add_issue(
                "tran_invalid_parent",
                f"TRAN is not permitted under {parent_tag}. "
                f"Allowed parents: {', '.join(sorted(_TRAN_LEGAL_PARENTS))}.",
                line_num=node.line_num,
                tag="TRAN",
            )
            return

        # LANG is required in all TRAN contexts
        if not node.get_children("LANG"):
            self.add_issue(
                "tran_missing_lang",
                "TRAN must have a LANG substructure.",
                line_num=node.line_num,
                tag="TRAN",
                severity="warning",
            )

        child_tags = {child.tag for child in node.children}

        # FILE.TRAN must have FORM and MIME (and LANG already checked above)
        if parent_tag == "FILE":
            if "FORM" not in child_tags:
                self.add_issue(
                    "tran_file_missing_form",
                    "FILE.TRAN must have a FORM substructure specifying the media type.",
                    line_num=node.line_num,
                    tag="TRAN",
                    severity="warning",
                )
            if "MIME" not in child_tags:
                self.add_issue(
                    "tran_file_missing_mime",
                    "FILE.TRAN must have a MIME substructure specifying the media type.",
                    line_num=node.line_num,
                    tag="TRAN",
                    severity="warning",
                )

        # NAME.TRAN may only have name-part subs and LANG
        if parent_tag == "NAME":
            _NAME_TRAN_OK = {"LANG", "GIVN", "SURN", "NPFX", "NSFX", "NICK", "SPFX"}
            bad = child_tags - _NAME_TRAN_OK
            if bad:
                self.add_issue(
                    "tran_name_invalid_child",
                    f"NAME.TRAN contains unexpected substructure(s): {', '.join(sorted(bad))}.",
                    line_num=node.line_num,
                    tag="TRAN",
                    severity="warning",
                )

        # PLAC.TRAN may only have LANG
        if parent_tag == "PLAC":
            bad = child_tags - {"LANG"}
            if bad:
                self.add_issue(
                    "tran_plac_invalid_child",
                    f"PLAC.TRAN contains unexpected substructure(s): {', '.join(sorted(bad))}. "
                    "Only LANG is permitted.",
                    line_num=node.line_num,
                    tag="TRAN",
                    severity="warning",
                )

    def validate_orphaned_records(self) -> None:
        """Warn about top-level records that are defined but never cited.

        Checks SOUR, REPO, OBJE, SNOTE records to see whether any
        pointer in the entire tree references their xref id.

        Note: SUBM records referenced by HEAD.SUBM are treated as cited.
        """
        # Collect all pointer values used anywhere in the tree (uppercased).
        # Use both the payload_is_pointer flag and a regex fallback so that
        # nodes like HEAD.SOUR whose payload looks like a pointer but was not
        # flagged as one (e.g. because the spec marks it as text) are still
        # treated as citations.
        all_pointers: set = set()
        for node in self.walk():
            p = node.payload.strip() if node.payload else ""
            if not p or p.upper() == "@VOID@":
                continue
            if node.payload_is_pointer or _XREF_RE.match(p):
                all_pointers.add(p.upper())

        # Check records of types that should be cited
        # SUBM is included: HEAD.SUBM will be in all_pointers if present,
        # so truly orphaned SUBM records (no HEAD.SUBM reference) will warn.
        CITABLE = {"SOUR", "REPO", "OBJE", "SNOTE", "SUBM"}
        for record in self.records:
            if record.tag not in CITABLE:
                continue
            if not record.xref_id:
                continue
            if record.xref_id.upper() not in all_pointers:
                self.add_issue(
                    "orphaned_record",
                    f"{record.tag} record {record.xref_id!r} is defined but never cited.",
                    line_num=record.line_num,
                    tag=record.tag,
                    severity="warning",
                )

    def validate_void_pointer(self, node: GedcomStructure) -> None:
        """Warn if @VOID@ is used in a context where it is not meaningful.

        @VOID@ is only appropriate for pointer-type payloads on tags that
        the GEDCOM 7 spec explicitly allows to point to @VOID@:
        FAMC, FAMS, CHIL, HUSB, WIFE, ASSO, SOUR (citation), OBJE (citation),
        REPO (citation), SUBM.

        Args:
            node: Node to validate.
        """
        VOID_OK_TAGS = frozenset({
            # Family / individual links
            "FAMC", "FAMS", "CHIL", "HUSB", "WIFE",
            # Record citations
            "ASSO", "SOUR", "OBJE", "REPO", "SUBM", "SNOTE",
            # Interest pointers
            "ALIA", "ANCI", "DESI",
        })
        if not node.payload_is_pointer:
            return
        if node.payload.strip() != "@VOID@":
            return
        if node.tag not in VOID_OK_TAGS:
            self.add_issue(
                "void_in_wrong_context",
                f"@VOID@ pointer on {node.tag!r} is not a spec-defined use of @VOID@.",
                line_num=node.line_num,
                tag=node.tag,
                severity="warning",
            )

    def validate_xref_format(self, node: GedcomStructure) -> None:
        """Validate that a node's xref id matches the required format.

        Args:
            node: Node whose xref id should be validated.
        """
        if not node.xref_id:
            return
        if not _XREF_RE.match(node.xref_id):
            self.add_issue(
                "invalid_xref_format",
                f"Xref id {node.xref_id!r} is not a valid GEDCOM xref "
                f"(must be @<non-empty, no spaces, no embedded @>@).",
                line_num=node.line_num,
                tag=node.tag,
            )

    def validate_payload_format(self, node: GedcomStructure) -> None:
        """Validate format-specific payload constraints for a node.

        Checks DATE, TIME, AGE, LATI, LONG, LANG, and RESN payloads.

        Args:
            node: Node to validate.
        """
        tag = node.tag
        payload = node.payload.strip()

        if not payload or node.payload_is_pointer:
            return

        # Generic regex-checked tags
        check = _FORMAT_CHECKS.get(tag)
        if check is not None:
            pattern, code, description = check
            if not pattern.match(payload):
                self.add_issue(
                    code,
                    f"{description}: {payload!r}",
                    line_num=node.line_num,
                    tag=tag,
                    severity="warning",
                )
            return

        # RESN: comma-separated enumeration set
        if tag == "RESN":
            parts = [p.strip() for p in payload.split(",")]
            invalid = [p for p in parts if p.upper() not in _RESN_VALID]
            if invalid:
                self.add_issue(
                    "invalid_resn_value",
                    f"RESN contains unknown value(s): {invalid}. "
                    f"Allowed: {sorted(_RESN_VALID)}.",
                    line_num=node.line_num,
                    tag=tag,
                    severity="warning",
                )

    # -------------------------------------------------------------------------
    # Deprecation warnings (changelog 7.0.6, 7.0.13)
    # -------------------------------------------------------------------------

    _DEPRECATED_TAGS: frozenset = frozenset({"ADR1", "ADR2", "ADR3"})

    def validate_deprecated_tag(self, node: GedcomStructure) -> None:
        """Warn on deprecated GEDCOM 7 tags.

        ADR1, ADR2, and ADR3 were deprecated in 7.0.13 because they convey
        no information not already present in ADDR.

        Args:
            node: Node to validate.
        """
        if node.tag in self._DEPRECATED_TAGS:
            self.add_issue(
                "deprecated_tag",
                f"{node.tag} is deprecated since GEDCOM 7.0.13; use ADDR instead.",
                line_num=node.line_num,
                tag=node.tag,
                severity="warning",
            )

    def validate_exid_type(self, node: GedcomStructure) -> None:
        """Warn when EXID has no TYPE substructure.

        EXID without TYPE was deprecated in 7.0.6; TYPE will become {1:1}
        in the next major release.

        Args:
            node: Node to validate.
        """
        if node.tag != "EXID":
            return
        has_type = any(child.tag == "TYPE" for child in node.children)
        if not has_type:
            self.add_issue(
                "exid_missing_type",
                "EXID without a TYPE substructure is deprecated since GEDCOM 7.0.6.",
                line_num=node.line_num,
                tag="EXID",
                severity="warning",
            )

    # -------------------------------------------------------------------------
    # NO-tag context validation (changelog 7.0.14)
    # -------------------------------------------------------------------------

    def validate_no_context(self, node: GedcomStructure) -> None:
        """Warn when NO XYZ is used where XYZ is not permitted.

        Per 7.0.14, NO XYZ should only appear where XYZ itself is a legal
        sibling structure.

        Args:
            node: Node to validate.
        """
        if node.tag != "NO":
            return
        payload = node.payload.strip() if node.payload else ""
        if not payload:
            return
        parent = node.parent
        if parent is None:
            return
        allowed = set(g7specs.allowed_child_tags(parent.tag))
        if payload.upper() not in {t.upper() for t in allowed}:
            self.add_issue(
                "no_tag_invalid_context",
                f"NO {payload!r} is not meaningful here; {payload!r} is not "
                f"a permitted substructure of {parent.tag!r}.",
                line_num=node.line_num,
                tag="NO",
                severity="warning",
            )

    # -------------------------------------------------------------------------
    # Self-referential pointer checks (changelog 7.0.17)
    # -------------------------------------------------------------------------

    def validate_self_referential_links(self) -> None:
        """Error on self-referential ALIA pointers.

        Per 7.0.17, an INDI.ALIA pointing to the same INDI is meaningless
        and prohibited.
        """
        for record in self.records:
            if record.tag != "INDI" or not record.xref_id:
                continue
            own_xref = record.xref_id.upper()
            for alia in record.get_children("ALIA"):
                if not alia.payload_is_pointer:
                    continue
                target = alia.payload.strip().upper()
                if target == own_xref:
                    self.add_issue(
                        "self_referential_alia",
                        f"INDI {own_xref!r} has ALIA pointing to itself, which is prohibited.",
                        line_num=alia.line_num,
                        tag="ALIA",
                    )

    def validate_pointer_cycles(self) -> None:
        """Error on SOUR-OBJE pointer cycles.

        Per 7.0.17, a SOUR-OBJE cycle (a source whose multimedia object
        lists that source as its own source) is meaningless and prohibited.
        """
        sour_records = {
            node.xref_id.upper(): node
            for node in self.records
            if node.tag == "SOUR" and node.xref_id
        }
        obje_records = {
            node.xref_id.upper(): node
            for node in self.records
            if node.tag == "OBJE" and node.xref_id
        }

        for sour_xref, sour in sour_records.items():
            for obje_child in sour.get_children("OBJE"):
                if not obje_child.payload_is_pointer:
                    continue
                obje_xref = obje_child.payload.strip().upper()
                if obje_xref == "@VOID@" or obje_xref not in obje_records:
                    continue
                obje = obje_records[obje_xref]
                for sour_child in obje.get_children("SOUR"):
                    if not sour_child.payload_is_pointer:
                        continue
                    if sour_child.payload.strip().upper() == sour_xref:
                        self.add_issue(
                            "sour_obje_cycle",
                            f"SOUR {sour_xref!r} cites OBJE {obje_xref!r}, which "
                            f"lists {sour_xref!r} as its source — meaningless cycle "
                            f"prohibited by GEDCOM 7.0.17.",
                            line_num=obje_child.line_num,
                            tag="OBJE",
                            severity="warning",
                        )

    # -------------------------------------------------------------------------
    # Duplicate FAMC / CHIL detection (changelog 7.0.14)
    # -------------------------------------------------------------------------

    def validate_duplicate_family_links(self) -> None:
        """Warn when an INDI has duplicate FAMC pointers or a FAM has duplicate CHIL pointers.

        Per 7.0.14:
        - A given INDI should have at most one FAMC pointing to a given FAM.
        - A given FAM should have at most one CHIL pointing to a given INDI.
        """
        for record in self.records:
            if record.tag == "INDI":
                seen: set = set()
                for famc in record.get_children("FAMC"):
                    if not famc.payload_is_pointer:
                        continue
                    target = famc.payload.strip().upper()
                    if target == "@VOID@":
                        continue
                    if target in seen:
                        self.add_issue(
                            "duplicate_famc",
                            f"INDI {record.xref_id!r} has more than one FAMC pointing "
                            f"to {target!r}; this has unclear meaning per GEDCOM 7.0.14.",
                            line_num=famc.line_num,
                            tag="FAMC",
                            severity="warning",
                        )
                    seen.add(target)

            elif record.tag == "FAM":
                seen = set()
                for chil in record.get_children("CHIL"):
                    if not chil.payload_is_pointer:
                        continue
                    target = chil.payload.strip().upper()
                    if target == "@VOID@":
                        continue
                    if target in seen:
                        self.add_issue(
                            "duplicate_chil",
                            f"FAM {record.xref_id!r} has more than one CHIL pointing "
                            f"to {target!r}; this indicates nonsensical birth order per GEDCOM 7.0.14.",
                            line_num=chil.line_num,
                            tag="CHIL",
                            severity="warning",
                        )
                    seen.add(target)
