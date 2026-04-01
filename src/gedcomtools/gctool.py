#!/usr/bin/env python3
"""
======================================================================
 Project: gedcomtools
 File:    gctool.py
 Purpose: GEDCOM 5/7 command-line utility — thin entry point.

 Created: 2026-03-22
 Updated: 2026-03-24 — dispatch table refactor (examine + interactive REPLs);
                        merge, diff, export, repair subcommands
 Updated: 2026-03-31 — added get_logger; replaced bare except Exception blocks
                        with specific exception types; added importlib.metadata import
 Updated: 2026-04-01 — split into focused modules; this file is now a thin
                        entry point containing only main() and argparse setup
======================================================================

gctool — inspect and manipulate GEDCOM 5 and GEDCOM 7 files.

Auto-detects format from file content.  All commands accept --json
for machine-readable output.

Usage::

    gctool info     <file>
    gctool validate <file>
    gctool list     <file> [indi|fam|sour|repo|obje|subm|snote]
    gctool show     <file> <xref>
    gctool find     <file> <tag> [--payload TEXT]
    gctool tree     <file> <xref> [--depth N]
    gctool stats    <file>
    gctool convert      <file> --to <fmt> [--out <path>]
    gctool interactive  <file>

Commands
--------
info      File summary: format, version, record counts.
validate  Run the validator and print issues.  Exits 1 if errors found.
          (Full validation for GEDCOM 7; parse-error check only for GEDCOM 5.)
list      Tabular listing of records by type.
show      All detail fields for a single record (any type).
find      Search the whole tree for nodes matching a tag (and optional payload).
tree      ASCII ancestry + descendant tree for one individual.
stats     Individual/family completeness and coverage summary.
convert       Convert between formats.  Currently supports: g5 → gx.
interactive   Drop into an interactive REPL for the loaded file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from .gctool_commands import (
    _LIST_TYPES,
    cmd_convert,
    cmd_find,
    cmd_info,
    cmd_list,
    cmd_show,
    cmd_spec,
    cmd_stats,
    cmd_tree,
    cmd_validate,
    cmd_version,
)
from .gctool_dataops import cmd_diff, cmd_export, cmd_merge, cmd_repair
from .gctool_interactive import cmd_interactive


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

_LIST_TYPES_STR = "|".join(_LIST_TYPES)


def main(argv: Optional[List[str]] = None) -> int:
    """Run the command-line entry point."""
    parser = argparse.ArgumentParser(
        prog="gctool",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    def _file(p):
        p.add_argument("file", metavar="FILE", help="GEDCOM 5 or 7 file (.ged / .gdz)")

    # info
    p = sub.add_parser("info", help="File summary (format, version, record counts)")
    _file(p); p.set_defaults(func=cmd_info)

    # validate
    p = sub.add_parser("validate", help="Validate; exit 1 if errors found")
    _file(p); p.set_defaults(func=cmd_validate)

    # list
    p = sub.add_parser("list", help=f"Tabular record listing [{_LIST_TYPES_STR}]")
    _file(p)
    p.add_argument("type", metavar="TYPE", nargs="?",
                   choices=_LIST_TYPES, default="indi",
                   help=f"Record type (default: indi)")
    p.set_defaults(func=cmd_list)

    # show
    p = sub.add_parser("show", help="Show all fields for a single record")
    _file(p)
    p.add_argument("xref", metavar="XREF", help="Xref id, e.g. @I1@ or I1")
    p.set_defaults(func=cmd_show)

    # find
    p = sub.add_parser("find", help="Search the tree for nodes matching a tag")
    _file(p)
    p.add_argument("tag", metavar="TAG")
    p.add_argument("--payload", "-p", metavar="TEXT",
                   help="Filter: payload must contain TEXT (case-insensitive)")
    p.set_defaults(func=cmd_find)

    # tree
    p = sub.add_parser("tree", help="ASCII ancestry + descendant tree")
    _file(p)
    p.add_argument("xref", metavar="XREF")
    p.add_argument("--depth", "-d", type=int, default=3, metavar="N",
                   help="Max generations in each direction (default: 3)")
    p.set_defaults(func=cmd_tree)

    # stats
    p = sub.add_parser("stats", help="Individual/family completeness summary")
    _file(p); p.set_defaults(func=cmd_stats)

    # convert
    p = sub.add_parser("convert", help="Convert between formats (g5→g7, g5→gx)")
    _file(p)
    p.add_argument("--to", required=True, metavar="FORMAT",
                   choices=["g5", "g7", "gx"], help="Target format")
    p.add_argument("--out", "-o", metavar="PATH",
                   help="Output path (default: auto-named next to source)")
    p.set_defaults(func=cmd_convert)

    # repair
    p = sub.add_parser("repair", help="Auto-fix common validation issues")
    _file(p)
    p.add_argument("--out", "-o", metavar="FILE",
                   help="Output path (default: FILE_repaired.ged)")
    p.add_argument("--dry-run", action="store_true",
                   help="Show what would be fixed without writing")
    p.set_defaults(func=cmd_repair)

    # export
    p = sub.add_parser("export", help="Dump individuals/families to CSV")
    _file(p)
    p.add_argument("--to", required=True, metavar="FORMAT", choices=["csv"],
                   help="Output format (csv)")
    p.add_argument("--out", "-o", metavar="FILE",
                   help="Output base path (auto-named if omitted)")
    p.set_defaults(func=cmd_export)

    # diff
    p = sub.add_parser("diff", help="Structural diff between two GEDCOM files")
    p.add_argument("file1", metavar="FILE1")
    p.add_argument("file2", metavar="FILE2")
    p.set_defaults(func=cmd_diff)

    # merge
    p = sub.add_parser("merge", help="Merge two GEDCOM files")
    p.add_argument("file1", metavar="FILE1")
    p.add_argument("file2", metavar="FILE2")
    p.add_argument("--out", "-o", metavar="FILE",
                   help="Output path (default: FILE1_merged.ged)")
    p.add_argument("--no-interactive", action="store_true",
                   help="Do not prompt for duplicates; keep both by default")
    p.set_defaults(func=cmd_merge)

    # interactive
    p = sub.add_parser("interactive", aliases=["repl"],
                       help="Drop into an interactive REPL for the loaded file")
    p.add_argument("file", metavar="FILE", nargs="?", default=None,
                   help="GEDCOM file to load on startup (optional)")
    p.set_defaults(func=cmd_interactive)

    # version
    p = sub.add_parser("version", help="Print package version and exit")
    p.set_defaults(func=cmd_version)

    # spec — thin passthrough to g7spec CLI (info/check/update/export/load/reset)
    p = sub.add_parser("spec", help="GEDCOM 7 spec management (g7spec passthrough)")
    p.add_argument("spec_args", nargs=argparse.REMAINDER,
                   help="Arguments forwarded to g7spec (e.g. check --verbose)")
    p.set_defaults(func=cmd_spec)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
