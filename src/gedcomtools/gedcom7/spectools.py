#!/usr/bin/env python3
"""
======================================================================
 Project: gedcomtools
 File:    gedcom7/spectools.py
 Purpose: CLI for inspecting and updating the GEDCOM 7 spec rules.

 Created: 2026-03-22
======================================================================

g7spec — manage the GEDCOM 7 structural specification rules.

The spec rules live in ``spec_rules.json`` (inside the installed package).
They define allowed substructures, cardinalities, payload types, and
enumeration values for every standard GEDCOM 7 tag.

Usage::

    g7spec info
    g7spec export [path]
    g7spec load <path>
    g7spec reset

Commands
--------
info              Show rule counts and tag list.
export [path]     Write the active rules to a JSON file (default: spec_rules.json).
load <path>       Replace the bundled spec_rules.json with the given file.
reset             Restore the bundled spec_rules.json to compiled-in defaults.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional


def _get_spec():
    """Lazy import so the module is usable even before the package is installed."""
    from gedcomtools.gedcom7 import specification
    return specification


def cmd_info(_args: List[str]) -> int:
    spec = _get_spec()
    rules = spec._CORE_RULES
    print(f"Active rules file : {spec._RULES_FILE}")
    print(f"  exists          : {spec._RULES_FILE.exists()}")
    print(f"Tags in _CORE_RULES : {len(rules)}")
    print()
    print("Tags:")
    for tag in sorted(rules):
        entry = rules[tag]
        n_subs = len(entry.get("substructures") or {})
        payload = entry.get("payload_type", "?")
        print(f"  {tag:<12} payload={payload:<8} substructures={n_subs}")
    return 0


def cmd_export(args: List[str]) -> int:
    spec = _get_spec()
    if args:
        dest = Path(args[0])
    else:
        dest = spec._RULES_FILE
    spec.save_rules(dest)
    print(f"Exported {len(spec._CORE_RULES)} tags → {dest}")
    return 0


def cmd_load(args: List[str]) -> int:
    if not args:
        print("usage: g7spec load <path>", file=sys.stderr)
        return 1
    src = Path(args[0])
    if not src.exists():
        print(f"File not found: {src}", file=sys.stderr)
        return 1
    spec = _get_spec()
    # Load into memory first to validate
    spec.load_rules(src)
    # Then overwrite the bundled file
    spec.save_rules()
    print(f"Loaded {len(spec._CORE_RULES)} tags from {src}")
    print(f"Saved to {spec._RULES_FILE}")
    return 0


def cmd_reset(_args: List[str]) -> int:
    spec = _get_spec()
    spec.reset_rules()
    print(f"Rules reset to built-in defaults ({len(spec._CORE_RULES)} tags).")
    print(f"Saved to {spec._RULES_FILE}")
    return 0


_COMMANDS = {
    "info":   cmd_info,
    "export": cmd_export,
    "load":   cmd_load,
    "reset":  cmd_reset,
}


def main(argv: Optional[List[str]] = None) -> int:
    args = (argv if argv is not None else sys.argv)[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, *rest = args
    handler = _COMMANDS.get(cmd)
    if handler is None:
        print(f"Unknown command: {cmd!r}. Available: {', '.join(_COMMANDS)}", file=sys.stderr)
        return 1
    return handler(rest)


if __name__ == "__main__":
    sys.exit(main())
