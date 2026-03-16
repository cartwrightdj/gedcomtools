"""validat7 — GEDCOM 7 file validator CLI.

Usage::

    validat7 <file.ged>

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


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: validat7 <file.ged>")
        sys.exit(0)

    filepath = Path(sys.argv[1])

    if not filepath.exists():
        print(f"error: file not found: {filepath}")
        sys.exit(3)

    try:
        g = Gedcom7(filepath)
    except Exception as exc:
        print(f"error: could not read file: {exc}")
        sys.exit(3)

    version = g.detect_gedcom_version()
    if not version:
        print("error: no GEDCOM version found in HEAD.GEDC.VERS")
        sys.exit(2)

    if not version.startswith("7"):
        print(f"error: not a GEDCOM 7 file (found version {version!r})")
        sys.exit(2)

    print(f"GEDCOM {version}  —  {filepath}  —  {len(g.records)} records")

    issues = g.validate()
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]

    for issue in warnings:
        loc = f"line {issue.line_num}" if issue.line_num else "—"
        tag = f" [{issue.tag}]" if issue.tag else ""
        print(f"  warning  {loc}{tag}  {issue.code}: {issue.message}")

    for issue in errors:
        loc = f"line {issue.line_num}" if issue.line_num else "—"
        tag = f" [{issue.tag}]" if issue.tag else ""
        print(f"  error    {loc}{tag}  {issue.code}: {issue.message}")

    total = len(errors) + len(warnings)
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
