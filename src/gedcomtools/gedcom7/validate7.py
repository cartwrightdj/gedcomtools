"""
======================================================================
 Project: gedcomtools
 File:    gedcom7/validate7.py
 Author:  David J. Cartwright
 Purpose: CLI entry point for validating GEDCOM 7 files.

 Created: 2026-03-15
 Updated:
   - 2026-03-15: initial implementation
   - 2026-03-15: added --lenient flag to suppress strict extension errors
   - 2026-03-16: fixed version check to use regex (prevents '71.0' false-positive);
                 added directory-vs-file check; narrowed exception to GedcomParseError
======================================================================

validate7 — GEDCOM 7 file validator CLI.

Usage::

    validate7 [--lenient] <file.ged>

Options:
    --lenient   Accept undeclared extension tags without error.

Exit codes:
    0  No errors (warnings may still be present)
    1  Validation errors found
    2  Not a GEDCOM 7 file
    3  File not found or cannot be read
"""

from __future__ import annotations

import sys
from pathlib import Path

from .gedcom7 import Gedcom7
from .exceptions import GedcomParseError


def main() -> None:
    """Run the command-line entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="validate7",
        description="Validate a GEDCOM 7 file.",
    )
    parser.add_argument("file", metavar="FILE", help="GEDCOM 7 file to validate")
    parser.add_argument(
        "--lenient",
        action="store_true",
        help="Accept undeclared extension tags without raising an error.",
    )
    args = parser.parse_args()

    filepath = Path(args.file)

    if not filepath.exists():
        print(f"error: file not found: {filepath}")
        sys.exit(3)

    if filepath.is_dir():
        print(f"error: {filepath} is a directory, not a file")
        sys.exit(3)

    try:
        g = Gedcom7(filepath)
    except GedcomParseError as exc:
        print(f"error: could not read file: {exc}")
        sys.exit(3)

    version = g.detect_gedcom_version()
    if not version:
        print("error: no GEDCOM version found in HEAD.GEDC.VERS")
        sys.exit(2)

    import re as _re
    if not _re.match(r"^7\.", version):
        print(f"error: not a GEDCOM 7 file (found version {version!r})")
        sys.exit(2)

    print(f"GEDCOM {version}  —  {filepath}  —  {len(g.records)} records")

    from .validator import GedcomValidator
    validator = GedcomValidator(g.records, strict_extensions=not args.lenient)
    raw_issues = validator.validate()

    # Merge parse errors (always errors) with validator issues
    issues = list(g.errors)
    from .gedcom7 import GedcomValidationError
    issues.extend(
        GedcomValidationError(
            code=i.code,
            message=i.message,
            line_num=i.line_num,
            tag=i.tag,
            severity=i.severity,
        )
        for i in raw_issues
    )

    errors   = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]

    for issue in warnings:
        loc = f"line {issue.line_num}" if issue.line_num else "—"
        tag = f" [{issue.tag}]" if issue.tag else ""
        print(f"  warning  {loc}{tag}  {issue.code}: {issue.message}")

    for issue in errors:
        loc = f"line {issue.line_num}" if issue.line_num else "—"
        tag = f" [{issue.tag}]" if issue.tag else ""
        print(f"  error    {loc}{tag}  {issue.code}: {issue.message}")

    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
