"""GEDCOM 7 parser and validator.

This module parses GEDCOM 7 files into an in-memory tree and exposes a simple
validation entry point.

Validation currently focuses on:

- line parsing
- hierarchy integrity
- top-level file structure
- legal child tags
- child cardinality
- pointer validation
- selected enumeration validation

The docstrings are written in Google style so they render well with
Sphinx Napoleon.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, DefaultDict, Dict, Iterable, List, Optional, Union
from collections import defaultdict

from .GedcomStructure import GedcomStructure
from . import specification as g7specs
from .validator import GedcomValidator


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
        """
        self.filepath = Path(filepath)
        self.records = []
        self.errors = []
        self._tag_index.clear()

        context: Dict[int, GedcomStructure] = {}

        with self.filepath.open("r", encoding="utf-8") as handle:
            for line_num, raw_line in enumerate(handle, start=1):
                # C0 control character check (U+0000–U+001F, excluding LF/CR)
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
                                    message=(
                                        f"Forbidden C0 control character U+{cp:04X} "
                                        f"on line {line_num}."
                                    ),
                                    line_num=line_num,
                                    severity="warning",
                                )
                            )
                        break  # one issue per line

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
                                f"Level {level} line has no active parent at "
                                f"level {level - 1}."
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
                                message=(
                                    "CONC was removed in GEDCOM 7.0; "
                                    "use longer lines or CONT instead."
                                ),
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
        """
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
