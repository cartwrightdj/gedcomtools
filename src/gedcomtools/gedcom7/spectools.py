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
    g7spec check [--no-cache] [--cache DIR] [--verbose]
    g7spec update [--no-cache] [--cache DIR] [--dry-run]

Commands
--------
info              Show rule counts and tag list.
export [path]     Write the active rules to a JSON file (default: spec_rules.json).
load <path>       Replace the bundled spec_rules.json with the given file.
reset             Restore the bundled spec_rules.json to compiled-in defaults.
check             Fetch the live GEDCOM 7 spec from gedcom.io and report diffs.
update            Fetch the live spec and apply missing/changed rules locally.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional


def _get_spec():
    """Lazy import so the module is usable even before the package is installed."""
    from gedcomtools.gedcom7 import specification
    return specification


def cmd_info(_args: List[str]) -> int:
    """Display information about the active GEDCOM 7 specification rules.

    Shows the active rules file path, whether it exists, the total number of
    tags, and a table of each tag's payload type and substructure count.

    Returns:
        0 always.
    """
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
    """Export the active GEDCOM 7 specification rules to a JSON file.

    Args:
        args: Optional list where args[0] is the destination path.
              Defaults to the bundled rules file if omitted.

    Returns:
        0 always.
    """
    spec = _get_spec()
    if args:
        dest = Path(args[0])
    else:
        dest = spec._RULES_FILE
    spec.save_rules(dest)
    print(f"Exported {len(spec._CORE_RULES)} tags → {dest}")
    return 0


def cmd_load(args: List[str]) -> int:
    """Load GEDCOM 7 specification rules from a JSON file, replacing the bundled rules.

    Args:
        args: List where args[0] is the path to the rules JSON file.

    Returns:
        0 on success, 1 if args is empty or the file does not exist.
    """
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
    """Reset the GEDCOM 7 specification rules to the built-in defaults.

    Returns:
        0 always.
    """
    spec = _get_spec()
    spec.reset_rules()
    print(f"Rules reset to built-in defaults ({len(spec._CORE_RULES)} tags).")
    print(f"Saved to {spec._RULES_FILE}")
    return 0


def cmd_check(args: List[str]) -> int:
    """Fetch live GEDCOM 7 spec and report differences from local rules."""
    ap = argparse.ArgumentParser(prog="g7spec check")
    ap.add_argument("--cache",    metavar="DIR", default=None,
                    help="Cache directory for fetched YAMLs")
    ap.add_argument("--no-cache", action="store_true",
                    help="Ignore existing cache; re-fetch all terms")
    ap.add_argument("--verbose",  "-v", action="store_true",
                    help="Also report extra locally-defined substructures")
    ns = ap.parse_args(args)

    try:
        from gedcomtools.gedcom7.spec_sync import (
            load_all_terms, build_spec_structures, compare,
        )
    except ImportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    cache_dir = Path(ns.cache) if ns.cache else None
    spec = _get_spec()

    print("Fetching live GEDCOM 7 spec from gedcom.io …", flush=True)
    try:
        terms = load_all_terms(cache_dir, no_cache=ns.no_cache, progress=True)
    except (RuntimeError, ImportError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"  {len(terms)} terms loaded.")
    structures = build_spec_structures(terms)
    print(f"  {len(structures)} structure-type terms.\n")

    report = compare(structures, spec._CORE_RULES, verbose=ns.verbose)
    print("\n".join(report))
    return 0


def cmd_update(args: List[str]) -> int:
    """Fetch live GEDCOM 7 spec and apply missing/changed rules locally."""
    ap = argparse.ArgumentParser(prog="g7spec update")
    ap.add_argument("--cache",    metavar="DIR", default=None,
                    help="Cache directory for fetched YAMLs")
    ap.add_argument("--no-cache", action="store_true",
                    help="Ignore existing cache; re-fetch all terms")
    ap.add_argument("--dry-run",  action="store_true",
                    help="Show what would change without modifying spec_rules.json")
    ns = ap.parse_args(args)

    try:
        from gedcomtools.gedcom7.spec_sync import (
            load_all_terms, build_spec_structures, apply_updates,
        )
    except ImportError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    cache_dir = Path(ns.cache) if ns.cache else None
    spec = _get_spec()

    print("Fetching live GEDCOM 7 spec from gedcom.io …", flush=True)
    try:
        terms = load_all_terms(cache_dir, no_cache=ns.no_cache, progress=True)
    except (RuntimeError, ImportError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"  {len(terms)} terms loaded.")
    structures = build_spec_structures(terms)
    print(f"  {len(structures)} structure-type terms.\n")

    if ns.dry_run:
        # Run compare to show what would change, then exit without saving
        from gedcomtools.gedcom7.spec_sync import compare
        report = compare(structures, spec._CORE_RULES)
        print("\n".join(report))
        print("\n(dry-run: no changes written)")
        return 0

    import copy
    scratch = copy.deepcopy(spec._CORE_RULES)
    added, updated = apply_updates(structures, scratch)

    if added == 0 and updated == 0:
        print("Local spec is already up to date — nothing to change.")
        return 0

    # Apply the patched dict to the live module state and save
    spec._CORE_RULES.clear()
    spec._CORE_RULES.update(scratch)
    spec.save_rules()

    print(f"Updated spec_rules.json:")
    print(f"  {added:>4} substructure(s) added")
    print(f"  {updated:>4} cardinality change(s) applied")
    print(f"Saved to {spec._RULES_FILE}")
    return 0


_COMMANDS = {
    "info":   cmd_info,
    "export": cmd_export,
    "load":   cmd_load,
    "reset":  cmd_reset,
    "check":  cmd_check,
    "update": cmd_update,
}


def main(argv: Optional[List[str]] = None) -> int:
    """Run the command-line entry point."""
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
