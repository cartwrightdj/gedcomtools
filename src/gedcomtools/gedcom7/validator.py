"""GEDCOM 7 validator.

This module performs structural and semantic validation of parsed GEDCOM 7
trees.

Validation phases:

1. file-level validation
2. parent/child legality validation
3. child cardinality validation
4. basic payload validation
5. pointer validation
6. selected enumeration validation

The docstrings are written in Google style so they render well with
Sphinx Napoleon.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set

from .GedcomStructure import GedcomStructure
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
    rf"|FROM\s+{_DP}(?:\s+TO\s+{_DP})?|TO\s+{_DP}|BET\s+{_DP}\s+AND\s+{_DP})$",
    re.IGNORECASE,
)

# hh:mm or h:mm, optional seconds, optional fraction, optional timezone
_TIME_RE = re.compile(
    r"^\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{4})?$"
)

# [< | >] any combo of Ny Nm Nd  (at least one component required)
_AGE_RE = re.compile(
    r"^[<>]?\s*(?:(?:\d+y\s*)?(?:\d+m\s*)?(?:\d+d\s*)?)$",
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
    "AGE":  (_AGE_RE,  "invalid_age_format",   "AGE payload does not match [<>] Ny Nm Nd"),
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

    def index_xrefs(self) -> None:
        """Build an index of all defined xref ids."""
        self._xref_index.clear()

        for node in self.walk():
            if not node.xref_id:
                continue

            self.validate_xref_format(node)

            if node.xref_id in self._xref_index:
                self.add_issue(
                    "duplicate_xref",
                    f"Duplicate xref id {node.xref_id!r}.",
                    line_num=node.line_num,
                    tag=node.tag,
                )
            else:
                self._xref_index[node.xref_id] = node

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

        if node.tag == "TRLR" and node.children:
            self.add_issue(
                "trlr_has_children",
                "TRLR must not have child structures.",
                line_num=node.line_num,
                tag=node.tag,
            )

    def validate_enumeration(self, node: GedcomStructure) -> None:
        """Validate selected enumeration payloads.

        Args:
            node: Node to validate.
        """
        values = g7specs.get_enum_values(node.tag)
        if values is None:
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
            if target == "@VOID@":
                # @VOID@ is a valid sentinel meaning "intentionally no target"
                continue

            if target not in self._xref_index:
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
        # Build maps from xref → set of pointer values for relevant tags
        def _pointer_set(record: GedcomStructure, tag: str) -> set:
            return {
                child.payload.strip()
                for child in record.get_children(tag)
                if child.payload_is_pointer and child.payload.strip() != "@VOID@"
            }

        indi_records = {
            node.xref_id: node
            for node in self.records
            if node.tag == "INDI" and node.xref_id
        }
        fam_records = {
            node.xref_id: node
            for node in self.records
            if node.tag == "FAM" and node.xref_id
        }

        for indi_xref, indi in indi_records.items():
            # INDI.FAMC → FAM must have CHIL back
            for famc in indi.get_children("FAMC"):
                fam_xref = famc.payload.strip()
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
                fam_xref = fams.payload.strip()
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
                indi_xref = chil.payload.strip()
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
