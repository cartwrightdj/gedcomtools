"""
======================================================================
 Project: Gedcom Tools
 File:    cli.py
 Author:  David J. Cartwright
 Purpose: Main gedcomtools CLI entry point

 Created: 2026-03-16
======================================================================
"""

import argparse
import sys
from pathlib import Path

# -----------------------------------------------------------------------
# Exit codes
# -----------------------------------------------------------------------

OK                      = 0
ERR_FILE_NOT_FOUND      = 1
ERR_UNKNOWN_SOURCE_TYPE = 2
ERR_UNSUPPORTED_CONV    = 3
ERR_CONVERSION_FAILED   = 4
ERR_IO                  = 5

try:
    import orjson
    def _json_dumps(obj) -> bytes:
        return orjson.dumps(obj, option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE)
except ImportError:
    import json
    def _json_dumps(obj) -> bytes:
        return (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


# -----------------------------------------------------------------------
# Source type detection
# -----------------------------------------------------------------------

def _sniff_source_type(path: Path) -> str:
    """
    Return 'g5', 'g7', or 'gx' based on file content.
    Raises ValueError if type cannot be determined.
    """
    suffix = path.suffix.lower()

    # GedcomX JSON
    if suffix in (".json", ".gedcomx"):
        try:
            with open(path, "rb") as f:
                first = f.read(1)
            if first == b"{":
                return "gx"
        except OSError:
            pass

    # GEDCOM line-based file — sniff VERS tag
    if suffix in (".ged", ".gedcom", ""):
        try:
            with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    # Looking for:  2 VERS 7.0  or  2 VERS 5.5.x
                    if line.startswith("2 VERS"):
                        vers = line.split(None, 2)[2] if len(line.split(None, 2)) > 2 else ""
                        if vers.startswith("7"):
                            return "g7"
                        else:
                            return "g5"
                    # Stop after HEAD block (level 0 record other than HEAD means no VERS found)
                    if line.startswith("0 ") and "HEAD" not in line:
                        break
        except OSError as e:
            raise ValueError(f"Cannot read file: {e}")
        # No VERS found — fall back on extension, assume G5
        if suffix in (".ged", ".gedcom"):
            return "g5"

    raise ValueError(
        f"Cannot determine source type for '{path}'. "
        "Use a .ged / .gedcom (GEDCOM 5/7), .json / .gedcomx (GedcomX JSON) file."
    )


# -----------------------------------------------------------------------
# Conversion helpers
# -----------------------------------------------------------------------

def _load_g5(path: Path):
    from gedcomtools.gedcom5.parser import Gedcom5x
    p = Gedcom5x()
    p.parse_file(str(path), strict=True)
    return p


def _load_g7(path: Path):
    from gedcomtools.gedcom7.gedcom7 import Gedcom7
    return Gedcom7(str(path))


def _load_gx(path: Path):
    from gedcomtools.gedcomx.gedcomx import GedcomX
    from gedcomtools.gedcomx.serialization import Serialization
    try:
        import orjson
        with open(path, "rb") as f:
            data = orjson.loads(f.read())
    except ImportError:
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    return Serialization.deserialize(data=data, class_type=GedcomX)


def _convert_g5_to_gx(source_path: Path, dest_path: Path) -> int:
    from gedcomtools.gedcomx.conversion import GedcomConverter
    from gedcomtools.gedcomx.serialization import Serialization
    print(f"Loading GEDCOM 5 from {source_path} ...")
    try:
        g5 = _load_g5(source_path)
    except Exception as e:
        print(f"Error: failed to parse source file: {e}", file=sys.stderr)
        return ERR_CONVERSION_FAILED
    print(f"Converting to GedcomX ...")
    try:
        conv = GedcomConverter()
        gx = conv.Gedcom5x_GedcomX(g5)
        data = Serialization.serialize(gx)
    except Exception as e:
        print(f"Error: conversion failed: {e}", file=sys.stderr)
        return ERR_CONVERSION_FAILED
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(_json_dumps(data))
    except OSError as e:
        print(f"Error: could not write output file: {e}", file=sys.stderr)
        return ERR_IO
    print(f"Written to {dest_path}")
    if gx._import_unhandled_tags:
        print(f"Unhandled tags: {list(gx._import_unhandled_tags.keys())}")
    return OK


# Conversion dispatch table: (source_type, dest_type) -> callable(source_path, dest_path)
_CONVERSIONS = {
    ("g5", "gx"): _convert_g5_to_gx,
}


# -----------------------------------------------------------------------
# Subcommand: convert
# -----------------------------------------------------------------------

def cmd_convert(args) -> int:
    source_path = Path(args.source)
    dest_path = Path(args.dest)
    dest_type = args.dest_type.lower()

    if not source_path.exists():
        print(f"Error: source file not found: {source_path}", file=sys.stderr)
        return ERR_FILE_NOT_FOUND

    try:
        source_type = _sniff_source_type(source_path)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return ERR_UNKNOWN_SOURCE_TYPE

    print(f"Detected source type: {source_type.upper()}")

    if source_type == dest_type:
        print("Source and destination types are the same — nothing to do.")
        return OK

    converter = _CONVERSIONS.get((source_type, dest_type))
    if converter is None:
        print(
            f"Error: conversion {source_type.upper()} → {dest_type.upper()} is not yet supported.",
            file=sys.stderr,
        )
        return ERR_UNSUPPORTED_CONV

    return converter(source_path, dest_path)


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="gedcomtools",
        description="Gedcom Tools CLI",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    subparsers.required = True

    # -- convert --
    p_convert = subparsers.add_parser(
        "convert",
        help="Convert a genealogy file between formats",
        description=(
            "Convert a genealogy file from its detected format to a target format.\n\n"
            "Supported conversions:\n"
            "  g5 → gx\n\n"
            "Formats:\n"
            "  g5   GEDCOM 5.x  (.ged)\n"
            "  g7   GEDCOM 7.x  (.ged)\n"
            "  gx   GedcomX     (.json)\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_convert.add_argument("source", metavar="SOURCE", help="Path to the source file")
    p_convert.add_argument("dest", metavar="DEST", help="Path to the output file")
    fmt_group = p_convert.add_mutually_exclusive_group(required=True)
    fmt_group.add_argument("-g5", dest="dest_type", action="store_const", const="g5", help="Convert to GEDCOM 5.x")
    fmt_group.add_argument("-g7", dest="dest_type", action="store_const", const="g7", help="Convert to GEDCOM 7.x")
    fmt_group.add_argument("-gx", dest="dest_type", action="store_const", const="gx", help="Convert to GedcomX JSON")
    p_convert.set_defaults(func=cmd_convert)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
