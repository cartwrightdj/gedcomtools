"""
======================================================================
 Project: gedcomtools
 File:    gedcom7/gedcom7.py
 Author:  David J. Cartwright
 Purpose: GEDCOM 7 file parser, tree builder, and validation entry point.

 Created: 2026-03-01
 Updated:
   - 2026-03-15: added parse_string() and parse_lines() helpers;
                 line-length warning on load; write() convenience method
   - 2026-03-16: version gate in validate(); GedcomParseError in loadfile();
                 reject negative GEDCOM levels in parse_gedcom_line();
                 strip payload before pointer detection; _rebuild_tag_index();
                 individuals(), families(), sources() etc. convenience methods;
                 imported models layer; get_parents/get_children_of/get_spouses
                 relationship traversal helpers
   - 2026-03-16: import updated GedcomStructure.py → structure.py
======================================================================

This module parses GEDCOM 7 files into an in-memory tree and exposes
validation and serialization entry points.

Validation currently focuses on:

- line parsing
- hierarchy integrity
- top-level file structure
- legal child tags
- child cardinality
- pointer validation
- selected enumeration validation
- payload format validation
- orphaned record detection

The docstrings are written in Google style so they render well with
Sphinx Napoleon.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, DefaultDict, Dict, Iterable, List, Optional, Union, overload
from collections import defaultdict

from .structure import GedcomStructure
from . import specification as g7specs
from .validator import GedcomValidator
from .writer import Gedcom7Writer
from .exceptions import GedcomParseError
from .models import (
    IndividualDetail, FamilyDetail, SourceDetail, RepositoryDetail,
    MediaDetail, SharedNoteDetail, SubmitterDetail,
    individual_detail, family_detail, source_detail, repository_detail,
    media_detail, shared_note_detail, submitter_detail,
)


@dataclass(slots=True)
class GedcomValidationError:
    """Represents a validation problem.

    Attributes:
        code: Stable machine-readable code.
        message: Human-readable description.
        line_num: Source line number if available.
        tag: GEDCOM tag associated with the problem.
        severity: ``"error"`` or ``"warning"``.
    """

    code: str
    message: str
    line_num: Optional[int] = None
    tag: Optional[str] = None
    severity: str = "error"


class Gedcom7:
    """Parse and validate GEDCOM 7 files."""

    def __init__(self, filepath: Optional[Union[str, Path]] = None) -> None:
        """Initialize the parser.

        Args:
            filepath: Optional GEDCOM file path to load immediately.
        """
        self.filepath: Optional[Path] = Path(filepath) if filepath else None
        self.records: List[GedcomStructure] = []
        self.errors: List[GedcomValidationError] = []
        self._tag_index: DefaultDict[str, List[int]] = defaultdict(list)

        if self.filepath:
            self.loadfile(self.filepath)

    @staticmethod
    def _norm_tag(tag: str) -> str:
        """Normalize a GEDCOM tag.

        Args:
            tag: GEDCOM tag.

        Returns:
            Uppercase GEDCOM tag.
        """
        return tag.upper()

    def _append_record(self, record: GedcomStructure) -> None:
        """Append a top-level record.

        Args:
            record: Top-level record to append.
        """
        self.records.append(record)
        self._tag_index[self._norm_tag(record.tag)].append(len(self.records) - 1)

    def _rebuild_tag_index(self) -> None:
        """Rebuild the tag index from the current records list.

        Call this after any direct mutation of ``self.records`` (e.g. pop or
        insert) to keep ``g["TAG"]`` lookups consistent.
        """
        self._tag_index.clear()
        for i, record in enumerate(self.records):
            self._tag_index[self._norm_tag(record.tag)].append(i)

    def __len__(self) -> int:
        """Return the number of top-level records."""
        return len(self.records)

    def __iter__(self) -> Iterable[GedcomStructure]:
        """Iterate over top-level records."""
        return iter(self.records)

    def __contains__(self, key: Union[str, GedcomStructure]) -> bool:
        """Return whether a tag or record exists.

        Args:
            key: Tag name or structure.
        """
        if isinstance(key, str):
            return self._norm_tag(key) in self._tag_index
        return key in self.records

    @overload
    def __getitem__(self, key: int) -> GedcomStructure: ...
    @overload
    def __getitem__(self, key: slice) -> List[GedcomStructure]: ...
    @overload
    def __getitem__(self, key: str) -> List[GedcomStructure]: ...
    @overload
    def __getitem__(self, key: tuple) -> Union[GedcomStructure, List[GedcomStructure]]: ...

    def __getitem__(
        self,
        key: Union[int, slice, str, tuple],
    ) -> Union[GedcomStructure, List[GedcomStructure]]:
        """Return records by position or tag.

        Args:
            key: Index, slice, tag, or ``(tag, subindex)``.

        Returns:
            Matching record or records.

        Raises:
            TypeError: If the key type is unsupported.
        """
        if isinstance(key, (int, slice)):
            return self.records[key]

        if isinstance(key, str):
            indexes = self._tag_index.get(self._norm_tag(key), [])
            return [self.records[index] for index in indexes]

        if isinstance(key, tuple) and len(key) == 2 and isinstance(key[0], str):
            tag, subkey = key
            items = self[tag]
            if isinstance(subkey, (int, slice)):
                return items[subkey]
            raise TypeError(f"Unsupported sub-key type: {type(subkey)!r}")

        raise TypeError(f"Unsupported key type: {type(key)!r}")

    @staticmethod
    def parse_gedcom_line(line: str) -> Optional[Dict[str, Any]]:
        """Parse one GEDCOM line into normalized fields.

        Args:
            line: Raw GEDCOM line.

        Returns:
            Parsed line dictionary or ``None`` for blank lines.

        Raises:
            ValueError: If the line is malformed.
        """
        line = line.lstrip("\ufeff").rstrip("\r\n")
        if not line.strip():
            return None

        parts = line.split(maxsplit=3)
        if len(parts) < 2:
            raise ValueError(f"Malformed GEDCOM line: {line!r}")

        try:
            level = int(parts[0])
        except ValueError as exc:
            raise ValueError(f"Invalid GEDCOM level: {parts[0]!r}") from exc

        if level < 0:
            raise ValueError(f"GEDCOM level must be non-negative, got {level}.")

        xref_id: Optional[str] = None
        payload = ""

        if parts[1].startswith("@") and parts[1].endswith("@"):
            if len(parts) < 3:
                raise ValueError(f"Missing tag after xref id: {line!r}")
            xref_id = parts[1]
            tag = parts[2].upper()
            payload = parts[3] if len(parts) > 3 else ""
        else:
            tag = parts[1].upper()
            payload = " ".join(parts[2:]) if len(parts) > 2 else ""

        payload = payload.strip()
        payload_is_pointer = (
            bool(payload)
            and payload.startswith("@")
            and payload.endswith("@")
            and " " not in payload
        )

        return {
            "level": level,
            "xref_id": xref_id,
            "tag": tag,
            "payload": payload,
            "payload_is_pointer": payload_is_pointer,
        }

    def _handle_schema_registration(self, node: GedcomStructure) -> None:
        """Register extension tags defined under ``HEAD.SCHMA.TAG``.

        Args:
            node: Newly created node.
        """
        if node.tag != "TAG":
            return
        if not node.parent or node.parent.tag != "SCHMA":
            return
        if not node.payload:
            return

        parts = node.payload.split(maxsplit=1)
        if len(parts) != 2:
            return

        ext_tag, uri = parts
        g7specs.register_extension_tag(ext_tag, uri)

    def loadfile(self, filepath: Union[str, Path]) -> None:
        """Load and parse a GEDCOM file.

        Args:
            filepath: Path to the GEDCOM file.

        Raises:
            GedcomParseError: If the file cannot be opened or read.
        """
        path = Path(filepath)
        try:
            handle = path.open("r", encoding="utf-8")
        except OSError as exc:
            raise GedcomParseError(f"Cannot open file {path}: {exc}") from exc
        self.filepath = path
        try:
            with handle:
                self.parse_lines(handle)
        except UnicodeDecodeError as exc:
            raise GedcomParseError(
                f"File {path} is not valid UTF-8. "
                f"GEDCOM 7 requires UTF-8 encoding. ({exc})"
            ) from exc

    def parse_string(self, text: str) -> None:
        """Parse GEDCOM 7 content from a string.

        This resets any previously loaded data.  Useful for testing or
        when GEDCOM content is available in memory rather than on disk.

        Args:
            text: Complete GEDCOM 7 file content as a string.
        """
        self.filepath = None
        self.records = []
        self.errors = []
        self._tag_index.clear()
        self.parse_lines(text.splitlines(keepends=True))

    def parse_lines(self, lines: Iterable[str]) -> None:
        """Parse GEDCOM 7 content from an iterable of raw lines.

        This resets any previously loaded data.

        Args:
            lines: Iterable of raw GEDCOM lines (with or without newlines).
        """
        self.records = []
        self.errors = []
        self._tag_index.clear()

        context: Dict[int, GedcomStructure] = {}

        for line_num, raw_line in enumerate(lines, start=1):
            # C0 control character check
            for ch in raw_line:
                cp = ord(ch)
                if cp <= 0x1F and ch not in "\n\r":
                    if cp == 0x00:
                        self.errors.append(
                            GedcomValidationError(
                                code="nul_character",
                                message="NUL byte (U+0000) is forbidden in GEDCOM 7.",
                                line_num=line_num,
                                severity="error",
                            )
                        )
                    else:
                        self.errors.append(
                            GedcomValidationError(
                                code="control_character",
                                message=f"Forbidden C0 control character U+{cp:04X} on line {line_num}.",
                                line_num=line_num,
                                severity="warning",
                            )
                        )
                    break

            try:
                parsed = self.parse_gedcom_line(raw_line)
            except ValueError as exc:
                self.errors.append(
                    GedcomValidationError(
                        code="parse_error",
                        message=str(exc),
                        line_num=line_num,
                    )
                )
                continue

            if parsed is None:
                continue

            level = parsed["level"]
            tag = parsed["tag"]

            if level > 0 and (level - 1) not in context:
                self.errors.append(
                    GedcomValidationError(
                        code="missing_parent_level",
                        message=(
                            f"Level {level} line has no active parent at level {level - 1}."
                        ),
                        line_num=line_num,
                        tag=tag,
                    )
                )
                continue

            if level > 0:
                previous_parent = context[level - 1]

                if tag == g7specs.CONC:
                    self.errors.append(
                        GedcomValidationError(
                            code="conc_deprecated",
                            message="CONC was removed in GEDCOM 7.0; use longer lines or CONT instead.",
                            line_num=line_num,
                            tag="CONC",
                            severity="warning",
                        )
                    )
                    previous_parent.value += parsed["payload"]
                    continue

                if tag == g7specs.CONT:
                    previous_parent.value += "\n" + parsed["payload"]
                    continue

            parent = context[level - 1] if level > 0 else None
            node = GedcomStructure(
                level=level,
                tag=tag,
                xref_id=parsed["xref_id"],
                payload=parsed["payload"],
                payload_is_pointer=parsed["payload_is_pointer"],
                parent=parent,
                line_num=line_num,
            )

            if level == 0:
                self._append_record(node)

            context[level] = node
            stale_levels = [k for k in context if k > level]
            for stale in stale_levels:
                del context[stale]

            self._handle_schema_registration(node)

    def validate(self) -> List[GedcomValidationError]:
        """Validate the loaded GEDCOM tree.

        Returns:
            All parse errors plus structural errors and warnings from the
            validator. Check ``issue.severity`` (``"error"`` or
            ``"warning"``) to distinguish them.

        If the file is not a GEDCOM 7 file a single error is returned
        instead of running the full validator (which would produce
        thousands of false positives on GEDCOM 5.x files).
        """
        import re as _re
        version = self.detect_gedcom_version()
        if not version or not _re.match(r"^7\.", version):
            label = f"GEDCOM {version}" if version else "unknown version"
            return list(self.errors) + [
                GedcomValidationError(
                    code="not_gedcom7",
                    message=(
                        f"This file is {label}; the GEDCOM 7 validator only "
                        "validates GEDCOM 7.x files."
                    ),
                    severity="error",
                )
            ]

        validator = GedcomValidator(self.records)
        issues = validator.validate()

        result = list(self.errors)  # parse-time errors (always severity="error")
        result.extend(
            GedcomValidationError(
                code=issue.code,
                message=issue.message,
                line_num=issue.line_num,
                tag=issue.tag,
                severity=issue.severity,
            )
            for issue in issues
        )

        return result

    def detect_gedcom_version(self) -> Optional[str]:
        """Return the GEDCOM version declared in ``HEAD.GEDC.VERS``.

        Returns:
            Version string if present, otherwise ``None``.
        """
        head_records = self["HEAD"]
        if not head_records:
            return None

        head = head_records[0]
        gedc = head.first_child("GEDC")
        if gedc is None:
            return None

        vers = gedc.first_child("VERS")
        if vers is None:
            return None

        value = vers.payload.strip()
        return value or None

    def write(
        self,
        filepath: Union[str, Path],
        *,
        line_ending: str = "\n",
        bom: bool = False,
    ) -> None:
        """Write the loaded records to a GEDCOM 7 file.

        Args:
            filepath: Destination path.
            line_ending: Line terminator (default LF per GEDCOM 7 spec).
            bom: Whether to write a UTF-8 BOM (discouraged by the spec).
        """
        writer = Gedcom7Writer(line_ending=line_ending, bom=bom)
        writer.write(self.records, filepath)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _records_by_tag(self, tag: str) -> List[GedcomStructure]:
        return [r for r in self.records if r.tag == tag]

    def _record_by_xref(self, tag: str, xref: str) -> Optional[GedcomStructure]:
        key = xref.upper()
        return next(
            (r for r in self.records if r.tag == tag
             and r.xref_id and r.xref_id.upper() == key),
            None,
        )

    # ------------------------------------------------------------------
    # Raw record accessors
    # ------------------------------------------------------------------

    def individuals(self) -> List[GedcomStructure]:
        """Return every INDI record as a raw :class:`GedcomStructure`."""
        return self._records_by_tag("INDI")

    def get_individual(self, xref: str) -> Optional[GedcomStructure]:
        """Return the raw :class:`GedcomStructure` for a single INDI by xref."""
        return self._record_by_xref("INDI", xref)

    def families(self) -> List[GedcomStructure]:
        """Return every FAM record as a raw :class:`GedcomStructure`."""
        return self._records_by_tag("FAM")

    def get_family(self, xref: str) -> Optional[GedcomStructure]:
        """Return the raw :class:`GedcomStructure` for a single FAM by xref."""
        return self._record_by_xref("FAM", xref)

    def sources(self) -> List[GedcomStructure]:
        """Return every SOUR record as a raw :class:`GedcomStructure`."""
        return self._records_by_tag("SOUR")

    def get_source(self, xref: str) -> Optional[GedcomStructure]:
        """Return the raw :class:`GedcomStructure` for a single SOUR by xref."""
        return self._record_by_xref("SOUR", xref)

    def repositories(self) -> List[GedcomStructure]:
        """Return every REPO record as a raw :class:`GedcomStructure`."""
        return self._records_by_tag("REPO")

    def get_repository(self, xref: str) -> Optional[GedcomStructure]:
        """Return the raw :class:`GedcomStructure` for a single REPO by xref."""
        return self._record_by_xref("REPO", xref)

    def media_objects(self) -> List[GedcomStructure]:
        """Return every OBJE record as a raw :class:`GedcomStructure`."""
        return self._records_by_tag("OBJE")

    def get_media(self, xref: str) -> Optional[GedcomStructure]:
        """Return the raw :class:`GedcomStructure` for a single OBJE by xref."""
        return self._record_by_xref("OBJE", xref)

    def shared_notes(self) -> List[GedcomStructure]:
        """Return every SNOTE record as a raw :class:`GedcomStructure`."""
        return self._records_by_tag("SNOTE")

    def get_shared_note(self, xref: str) -> Optional[GedcomStructure]:
        """Return the raw :class:`GedcomStructure` for a single SNOTE by xref."""
        return self._record_by_xref("SNOTE", xref)

    def submitters(self) -> List[GedcomStructure]:
        """Return every SUBM record as a raw :class:`GedcomStructure`."""
        return self._records_by_tag("SUBM")

    def get_submitter(self, xref: str) -> Optional[GedcomStructure]:
        """Return the raw :class:`GedcomStructure` for a single SUBM by xref."""
        return self._record_by_xref("SUBM", xref)

    # ------------------------------------------------------------------
    # Detail model accessors  (explicit snapshot; not editable)
    # ------------------------------------------------------------------

    def individual_details(self) -> List[IndividualDetail]:
        """Return :class:`IndividualDetail` for every INDI record."""
        return [individual_detail(r) for r in self._records_by_tag("INDI")]

    def get_individual_detail(self, xref: str) -> Optional[IndividualDetail]:
        """Return :class:`IndividualDetail` for a single INDI by xref."""
        node = self._record_by_xref("INDI", xref)
        return individual_detail(node) if node else None

    def family_details(self) -> List[FamilyDetail]:
        """Return :class:`FamilyDetail` for every FAM record."""
        return [family_detail(r) for r in self._records_by_tag("FAM")]

    def get_family_detail(self, xref: str) -> Optional[FamilyDetail]:
        """Return :class:`FamilyDetail` for a single FAM by xref."""
        node = self._record_by_xref("FAM", xref)
        return family_detail(node) if node else None

    def source_details(self) -> List[SourceDetail]:
        """Return :class:`SourceDetail` for every SOUR record."""
        return [source_detail(r) for r in self._records_by_tag("SOUR")]

    def get_source_detail(self, xref: str) -> Optional[SourceDetail]:
        """Return :class:`SourceDetail` for a single SOUR by xref."""
        node = self._record_by_xref("SOUR", xref)
        return source_detail(node) if node else None

    def repository_details(self) -> List[RepositoryDetail]:
        """Return :class:`RepositoryDetail` for every REPO record."""
        return [repository_detail(r) for r in self._records_by_tag("REPO")]

    def get_repository_detail(self, xref: str) -> Optional[RepositoryDetail]:
        """Return :class:`RepositoryDetail` for a single REPO by xref."""
        node = self._record_by_xref("REPO", xref)
        return repository_detail(node) if node else None

    def media_details(self) -> List[MediaDetail]:
        """Return :class:`MediaDetail` for every OBJE record."""
        return [media_detail(r) for r in self._records_by_tag("OBJE")]

    def get_media_detail(self, xref: str) -> Optional[MediaDetail]:
        """Return :class:`MediaDetail` for a single OBJE by xref."""
        node = self._record_by_xref("OBJE", xref)
        return media_detail(node) if node else None

    def shared_note_details(self) -> List[SharedNoteDetail]:
        """Return :class:`SharedNoteDetail` for every SNOTE record."""
        return [shared_note_detail(r) for r in self._records_by_tag("SNOTE")]

    def get_shared_note_detail(self, xref: str) -> Optional[SharedNoteDetail]:
        """Return :class:`SharedNoteDetail` for a single SNOTE by xref."""
        node = self._record_by_xref("SNOTE", xref)
        return shared_note_detail(node) if node else None

    def submitter_details(self) -> List[SubmitterDetail]:
        """Return :class:`SubmitterDetail` for every SUBM record."""
        return [submitter_detail(r) for r in self._records_by_tag("SUBM")]

    def get_submitter_detail(self, xref: str) -> Optional[SubmitterDetail]:
        """Return :class:`SubmitterDetail` for a single SUBM by xref."""
        node = self._record_by_xref("SUBM", xref)
        return submitter_detail(node) if node else None

    def resolve_subm(self, xref: str) -> str:
        """Resolve a SUBM xref pointer to a human-readable name.

        Returns the submitter's NAME value, or the raw *xref* string if the
        record cannot be found or has no name.

        Args:
            xref: Xref id, e.g. ``"@S1@"`` or ``"S1"``.
        """
        xref = xref.strip()
        if not xref.startswith("@"):
            xref = f"@{xref}@"
        detail = self.get_submitter_detail(xref)
        if detail and detail.name:
            return detail.name
        return xref

    # ------------------------------------------------------------------
    # Relationship traversal — raw records
    # ------------------------------------------------------------------

    def get_parents(self, indi_xref: str) -> List[GedcomStructure]:
        """Return the parents of an individual as raw records.

        Walks FAMC → FAM → HUSB/WIFE.

        Args:
            indi_xref: Xref id of the individual (e.g. ``"@I1@"``).

        Returns:
            Raw :class:`GedcomStructure` for each parent found.
        """
        indi_node = self._record_by_xref("INDI", indi_xref)
        if indi_node is None:
            return []
        result: List[GedcomStructure] = []
        for famc in indi_node.get_children("FAMC"):
            if not famc.payload_is_pointer or not famc.payload:
                continue
            fam_node = self._record_by_xref("FAM", famc.payload)
            if fam_node is None:
                continue
            for tag in ("HUSB", "WIFE"):
                ptr_node = fam_node.first_child(tag)
                if ptr_node and ptr_node.payload_is_pointer and ptr_node.payload:
                    parent = self._record_by_xref("INDI", ptr_node.payload)
                    if parent:
                        result.append(parent)
        return result

    def get_children_of(self, indi_xref: str) -> List[GedcomStructure]:
        """Return the children of an individual as raw records.

        Walks FAMS → FAM → CHIL.

        Args:
            indi_xref: Xref id of the individual.

        Returns:
            Raw :class:`GedcomStructure` for each child found.
        """
        indi_node = self._record_by_xref("INDI", indi_xref)
        if indi_node is None:
            return []
        result: List[GedcomStructure] = []
        for fams in indi_node.get_children("FAMS"):
            if not fams.payload_is_pointer or not fams.payload:
                continue
            fam_node = self._record_by_xref("FAM", fams.payload)
            if fam_node is None:
                continue
            for chil in fam_node.get_children("CHIL"):
                if chil.payload_is_pointer and chil.payload:
                    child_node = self._record_by_xref("INDI", chil.payload)
                    if child_node:
                        result.append(child_node)
        return result

    def get_spouses(self, indi_xref: str) -> List[GedcomStructure]:
        """Return the spouses of an individual as raw records.

        For each FAMS family, returns the other HUSB or WIFE record.

        Args:
            indi_xref: Xref id of the individual.

        Returns:
            Raw :class:`GedcomStructure` for each spouse found.
        """
        indi_node = self._record_by_xref("INDI", indi_xref)
        if indi_node is None:
            return []
        norm_xref = indi_xref.upper()
        result: List[GedcomStructure] = []
        for fams in indi_node.get_children("FAMS"):
            if not fams.payload_is_pointer or not fams.payload:
                continue
            fam_node = self._record_by_xref("FAM", fams.payload)
            if fam_node is None:
                continue
            for tag in ("HUSB", "WIFE"):
                ptr_node = fam_node.first_child(tag)
                if (ptr_node and ptr_node.payload_is_pointer and ptr_node.payload
                        and ptr_node.payload.upper() != norm_xref):
                    spouse_node = self._record_by_xref("INDI", ptr_node.payload)
                    if spouse_node:
                        result.append(spouse_node)
        return result

    # ------------------------------------------------------------------
    # Relationship traversal — Detail models (explicit)
    # ------------------------------------------------------------------

    def get_parents_detail(self, indi_xref: str) -> List[IndividualDetail]:
        """Return parents as :class:`IndividualDetail` snapshots."""
        return [individual_detail(r) for r in self.get_parents(indi_xref)]

    def get_children_detail(self, indi_xref: str) -> List[IndividualDetail]:
        """Return children as :class:`IndividualDetail` snapshots."""
        return [individual_detail(r) for r in self.get_children_of(indi_xref)]

    def get_spouses_detail(self, indi_xref: str) -> List[IndividualDetail]:
        """Return spouses as :class:`IndividualDetail` snapshots."""
        return [individual_detail(r) for r in self.get_spouses(indi_xref)]

    def to_dict(self) -> Dict[str, Any]:
        """Convert the full GEDCOM file into a serializable dictionary.

        Returns:
            Serializable representation of the parsed GEDCOM file.
        """
        return {
            "filepath": str(self.filepath) if self.filepath else None,
            "records": [record.to_dict() for record in self.records],
            "errors": [
                {
                    "code": err.code,
                    "message": err.message,
                    "line_num": err.line_num,
                    "tag": err.tag,
                }
                for err in self.errors
            ],
        }
