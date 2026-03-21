from __future__ import annotations

"""
Validation result types and shared helpers for GedcomX model validation.

Used by GedcomXModel.validate() and the GedcomX.validate() container method.
"""

import re
from dataclasses import dataclass, field
from typing import Literal

# ── Shared regex patterns ──────────────────────────────────────────────────────

# BCP-47 language tag (simplified: 2–8 letter primary + optional subtags)
_LANG_RE = re.compile(r"^[a-zA-Z]{2,8}(-[a-zA-Z0-9]{1,8})*$")

# MIME type: type/subtype
_MIME_RE = re.compile(
    r"^[a-zA-Z0-9][a-zA-Z0-9!#$&\-^_]*/[a-zA-Z0-9][a-zA-Z0-9!#$&\-^_.+]*$"
)

# GedcomX formal date — loose prefix check
_GEDCOMX_DATE_RE = re.compile(r"^[+\-A\[/]|^\d{4}")


@dataclass
class ValidationIssue:
    """A single validation finding."""
    severity: Literal["error", "warning"]
    path: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] {self.path}: {self.message}"


@dataclass
class ValidationResult:
    """Aggregated findings from validate()."""
    issues: list[ValidationIssue] = field(default_factory=list)

    # ── helpers ────────────────────────────────────────────────────────────────

    def error(self, path: str, message: str) -> None:
        self.issues.append(ValidationIssue("error", path, message))

    def warn(self, path: str, message: str) -> None:
        self.issues.append(ValidationIssue("warning", path, message))

    def merge(self, other: "ValidationResult", prefix: str = "") -> None:
        for issue in other.issues:
            full = f"{prefix}.{issue.path}" if issue.path else prefix
            self.issues.append(ValidationIssue(issue.severity, full, issue.message))

    # ── introspection ──────────────────────────────────────────────────────────

    @property
    def is_valid(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    def __bool__(self) -> bool:
        return self.is_valid

    def __repr__(self) -> str:
        return (
            f"ValidationResult("
            f"{len(self.errors)} error(s), {len(self.warnings)} warning(s))"
        )

    def __str__(self) -> str:
        if not self.issues:
            return "ValidationResult: OK"
        lines = [repr(self)]
        for issue in self.issues:
            lines.append(f"  {issue}")
        return "\n".join(lines)


# ── Shared helper functions ───────────────────────────────────────────────────
# Import these in _validate_self overrides:
#   from .validation import check_lang, check_mime, check_instance


def check_lang(result: ValidationResult, path: str, value: str | None) -> None:
    """Warn if *value* is set but is not a valid BCP-47 language tag."""
    if value and not _LANG_RE.match(value):
        result.warn(path, f"{value!r} is not a valid BCP-47 language tag")


def check_mime(result: ValidationResult, path: str, value: str | None) -> None:
    """Warn if *value* is set but is not a valid MIME type (type/subtype)."""
    if value and not _MIME_RE.match(value):
        result.warn(path, f"{value!r} is not a valid MIME type (expected 'type/subtype')")


def check_gedcomx_date(result: ValidationResult, path: str, value: str | None) -> None:
    """Warn if *value* is set but does not look like a GedcomX formal date."""
    if value and not _GEDCOMX_DATE_RE.match(value):
        result.warn(path, f"{value!r} does not look like a valid GedcomX formal date")


def check_nonempty(result: ValidationResult, path: str, value: str | None,
                   severity: str = "warning") -> None:
    """Warn/error if *value* is an empty or all-whitespace string."""
    if isinstance(value, str) and not value.strip():
        getattr(result, "error" if severity == "error" else "warn")(
            path, "Value must not be empty"
        )


def check_instance(result: ValidationResult, path: str, value: object,
                   *expected: type, severity: str = "error") -> bool:
    """Error/warn if *value* is not None and not an instance of any *expected* type.

    Returns True if the check passed (value is None or correct type).
    """
    if value is not None and not isinstance(value, expected):
        names = " or ".join(t.__name__ for t in expected)
        msg = f"Expected {names}, got {type(value).__name__}"
        getattr(result, "error" if severity == "error" else "warn")(path, msg)
        return False
    return True
