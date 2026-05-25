"""
======================================================================
 Project: Gedcom Tools
 File:    cli.py
 Author:  David J. Cartwright
 Purpose: Main gedcomtools CLI entry point

 Created: 2026-03-16
 Updated: 2026-03-24 — added g5→g7 conversion; --on-unknown drop|convert flag
          2026-04-03 — added comment explaining errors="replace" is intentional
                        in _sniff_source_type (ASCII-only VERS tag inspection)
======================================================================
"""

import argparse
import sys
from contextlib import contextmanager, nullcontext, redirect_stderr
from io import StringIO
from pathlib import Path
from typing import Optional, Sequence

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
    def _json_dumps(obj, *, compact: bool = False) -> bytes:
        option = orjson.OPT_APPEND_NEWLINE
        if not compact:
            option |= orjson.OPT_INDENT_2
        return orjson.dumps(obj, option=option)
except ImportError:
    import json
    def _json_dumps(obj, *, compact: bool = False) -> bytes:
        if compact:
            text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
        else:
            text = json.dumps(obj, ensure_ascii=False, indent=2)
        return (text + "\n").encode("utf-8")


class _NullWriter:
    """Small file-like sink used for quiet status output."""

    def write(self, _text: str) -> int:
        return 0

    def flush(self) -> None:
        return None


def _is_stdout_path(path: Path) -> bool:
    """Return True when an output path means stdout."""
    return str(path) == "-"


def _status_stream(dest_path: Path, *, quiet: bool = False):
    """Send status messages to stderr when stdout is reserved for data."""
    if quiet:
        return _NullWriter()
    return sys.stderr if _is_stdout_path(dest_path) else sys.stdout


def _write_bytes_output(dest_path: Path, data: bytes) -> None:
    """Write bytes to a file or stdout when *dest_path* is ``-``."""
    if _is_stdout_path(dest_path):
        if hasattr(sys.stdout, "buffer"):
            sys.stdout.buffer.write(data)
        else:
            sys.stdout.write(data.decode("utf-8"))
            if not data.endswith(b"\n"):
                sys.stdout.write("\n")
            return
        if not data.endswith(b"\n"):
            sys.stdout.buffer.write(b"\n")
        return
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(data)


def _write_text_output(dest_path: Path, text: str) -> None:
    """Write text to a file or stdout when *dest_path* is ``-``."""
    if _is_stdout_path(dest_path):
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
        return
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_text(text, encoding="utf-8")


@contextmanager
def _quiet_tool_stderr(quiet: bool):
    """Suppress noisy converter/library stderr output in quiet mode."""
    if not quiet:
        with nullcontext():
            yield
        return
    try:
        from loguru import logger
    except ImportError:
        logger = None
    if logger is not None:
        logger.disable("")
    try:
        with redirect_stderr(StringIO()):
            yield
    finally:
        if logger is not None:
            logger.enable("")


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
                prefix = f.read(4096)
            if prefix.removeprefix(b"\xef\xbb\xbf").lstrip().startswith(b"{"):
                return "gx"
        except OSError:
            pass

    # GEDCOM line-based file — sniff VERS tag
    if suffix in (".ged", ".gedcom", ""):
        try:
            # errors="replace" is intentional: we only inspect ASCII VERS/HEAD
            # tags here, so replacement characters cannot affect the result.
            with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    # Looking for:  2 VERS 7.0  or  2 VERS 5.5.x
                    if line.startswith("2 VERS"):
                        vers = line.split(None, 2)[2] if len(line.split(None, 2)) > 2 else ""
                        if vers.startswith("7"):
                            return "g7"
                        return "g5"
                    # Stop after HEAD block (level 0 record other than HEAD means no VERS found)
                    if line.startswith("0 ") and "HEAD" not in line:
                        break
        except OSError as e:
            raise ValueError(f"Cannot read file: {e}") from e
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
    raw = path.read_bytes()
    try:
        import orjson  # pylint: disable=redefined-outer-name
        data = orjson.loads(raw.removeprefix(b"\xef\xbb\xbf"))
    except ImportError:
        import json  # pylint: disable=redefined-outer-name
        data = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object at root of {path}, got {type(data).__name__}")
    return Serialization.deserialize(data=data, class_type=GedcomX)


def _convert_g5_to_gx(source_path: Path, dest_path: Path, *, quiet: bool = False, compact: bool = False) -> int:
    from gedcomtools.gedcomx.conversion import GedcomConverter
    status = _status_stream(dest_path, quiet=quiet)
    print(f"Loading GEDCOM 5 from {source_path} ...", file=status)
    try:
        with _quiet_tool_stderr(quiet):
            g5 = _load_g5(source_path)
    except Exception as e:
        print(f"Error: failed to parse source file: {e}", file=sys.stderr)
        return ERR_CONVERSION_FAILED
    print("Converting to GedcomX ...", file=status)
    try:
        with _quiet_tool_stderr(quiet):
            conv = GedcomConverter()
            gx = conv.Gedcom5x_GedcomX(g5)
            data = gx._to_dict()
    except Exception as e:
        print(f"Error: conversion failed: {e}", file=sys.stderr)
        return ERR_CONVERSION_FAILED
    try:
        _write_bytes_output(dest_path, _json_dumps(data, compact=compact))
    except OSError as e:
        print(f"Error: could not write output file: {e}", file=sys.stderr)
        return ERR_IO
    print(f"Written to {dest_path}", file=status)
    if gx._import_unhandled_tags:
        print(f"Unhandled tags: {list(gx._import_unhandled_tags.keys())}", file=status)
    return OK


def _convert_g5_to_g7(
    source_path: Path,
    dest_path: Path,
    *,
    unknown_tags: str = "drop",
    quiet: bool = False,
    compact: bool = False,
) -> int:
    from gedcomtools.gedcom5.gedcom5 import Gedcom5
    from gedcomtools.gedcom5.g5tog7 import Gedcom5to7
    from gedcomtools.gedcom7.writer import Gedcom7Writer
    _ = compact
    status = _status_stream(dest_path, quiet=quiet)
    print(f"Loading GEDCOM 5 from {source_path} ...", file=status)
    try:
        with _quiet_tool_stderr(quiet):
            g5 = Gedcom5(source_path)
    except Exception as e:
        print(f"Error: failed to parse source file: {e}", file=sys.stderr)
        return ERR_CONVERSION_FAILED
    print("Converting to GEDCOM 7 ...", file=status)
    try:
        with _quiet_tool_stderr(quiet):
            conv = Gedcom5to7(unknown_tags=unknown_tags)
            records = conv.convert(g5)
    except Exception as e:
        print(f"Error: conversion failed: {e}", file=sys.stderr)
        return ERR_CONVERSION_FAILED
    for w in conv.warnings:
        print(f"  warning: {w}", file=status)
    try:
        writer = Gedcom7Writer()
        if _is_stdout_path(dest_path):
            _write_text_output(dest_path, writer.serialize(records))
        else:
            writer.write(records, dest_path)
    except OSError as e:
        print(f"Error: could not write output file: {e}", file=sys.stderr)
        return ERR_IO
    n_indi = sum(1 for r in records if r.tag == "INDI")
    n_fam  = sum(1 for r in records if r.tag == "FAM")
    print(f"Written to {dest_path}  ({n_indi} INDI · {n_fam} FAM)", file=status)
    return OK


def _convert_g7_to_gx(source_path: Path, dest_path: Path, *, quiet: bool = False, compact: bool = False) -> int:
    from gedcomtools.gedcom7.g7togx import Gedcom7Converter
    status = _status_stream(dest_path, quiet=quiet)
    print(f"Loading GEDCOM 7 from {source_path} ...", file=status)
    try:
        with _quiet_tool_stderr(quiet):
            g7 = _load_g7(source_path)
    except Exception as e:
        print(f"Error: failed to parse source file: {e}", file=sys.stderr)
        return ERR_CONVERSION_FAILED
    print("Converting to GedcomX ...", file=status)
    try:
        with _quiet_tool_stderr(quiet):
            gx = Gedcom7Converter().convert(g7)
            data = gx._to_dict()
    except Exception as e:
        print(f"Error: conversion failed: {e}", file=sys.stderr)
        return ERR_CONVERSION_FAILED
    try:
        _write_bytes_output(dest_path, _json_dumps(data, compact=compact))
    except OSError as e:
        print(f"Error: could not write output file: {e}", file=sys.stderr)
        return ERR_IO
    print(f"Written to {dest_path}", file=status)
    if gx._import_unhandled_tags:
        print(f"Unhandled tags: {list(gx._import_unhandled_tags.keys())}", file=status)
    return OK


def _convert_gx_to_g7(source_path: Path, dest_path: Path, *, quiet: bool = False, compact: bool = False) -> int:
    from gedcomtools.gedcom7.gxtog7 import GedcomXConverter
    from gedcomtools.gedcom7.writer import Gedcom7Writer
    _ = compact
    status = _status_stream(dest_path, quiet=quiet)
    print(f"Loading GedcomX from {source_path} ...", file=status)
    try:
        with _quiet_tool_stderr(quiet):
            gx = _load_gx(source_path)
    except Exception as e:
        print(f"Error: failed to parse source file: {e}", file=sys.stderr)
        return ERR_CONVERSION_FAILED
    print("Converting to GEDCOM 7 ...", file=status)
    try:
        with _quiet_tool_stderr(quiet):
            records = GedcomXConverter().convert(gx)
    except Exception as e:
        print(f"Error: conversion failed: {e}", file=sys.stderr)
        return ERR_CONVERSION_FAILED
    try:
        writer = Gedcom7Writer()
        if _is_stdout_path(dest_path):
            _write_text_output(dest_path, writer.serialize(records))
        else:
            writer.write(records, dest_path)
    except OSError as e:
        print(f"Error: could not write output file: {e}", file=sys.stderr)
        return ERR_IO
    n_indi = sum(1 for r in records if r.tag == "INDI")
    n_fam  = sum(1 for r in records if r.tag == "FAM")
    print(f"Written to {dest_path}  ({n_indi} INDI · {n_fam} FAM)", file=status)
    return OK


def _convert_gedcom_to_csv(source_path: Path, dest_path: Path, *, quiet: bool = False, compact: bool = False) -> int:
    """Export a GEDCOM 5/7 file to one CSV per top-level entity type."""
    from gedcomtools.gctool_dataops import export_gedcom_to_csv

    print(f"Exporting top-level GEDCOM entities from {source_path} to CSV ...", file=_status_stream(dest_path, quiet=quiet))
    return export_gedcom_to_csv(source_path, dest_path, quiet=quiet, compact=compact)


# Conversion dispatch table: (source_type, dest_type) -> callable(source_path, dest_path)
_CONVERSIONS = {
    ("g5", "gx"): _convert_g5_to_gx,
    ("g5", "g7"): _convert_g5_to_g7,
    ("g5", "csv"): _convert_gedcom_to_csv,
    ("g7", "gx"): _convert_g7_to_gx,
    ("g7", "csv"): _convert_gedcom_to_csv,
    ("gx", "g7"): _convert_gx_to_g7,
}


# -----------------------------------------------------------------------
# Subcommand: convert
# -----------------------------------------------------------------------

def cmd_convert(args) -> int:
    """Execute the ``convert`` subcommand: detect source type and run the appropriate converter.

    Args:
        args: Parsed argparse namespace with ``source``, ``dest``, and ``dest_type``.

    Returns:
        An integer exit code (0 = success).
    """
    source_path = Path(args.source)
    dest_path = Path(args.dest)
    dest_type = args.dest_type.lower()
    quiet = getattr(args, "quiet", False)
    compact = getattr(args, "compact", False)
    status = _status_stream(dest_path, quiet=quiet)

    if not source_path.exists():
        print(f"Error: source file not found: {source_path}", file=sys.stderr)
        return ERR_FILE_NOT_FOUND

    try:
        source_type = _sniff_source_type(source_path)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return ERR_UNKNOWN_SOURCE_TYPE

    print(f"Detected source type: {source_type.upper()}", file=status)

    if source_type == dest_type:
        print("Source and destination types are the same — nothing to do.", file=status)
        return OK

    converter = _CONVERSIONS.get((source_type, dest_type))
    if converter is None:
        print(
            f"Error: conversion {source_type.upper()} → {dest_type.upper()} is not yet supported.",
            file=sys.stderr,
        )
        return ERR_UNSUPPORTED_CONV

    kwargs = {}
    if (source_type, dest_type) == ("g5", "g7"):
        kwargs["unknown_tags"] = getattr(args, "on_unknown", "drop") or "drop"
    kwargs["quiet"] = quiet
    kwargs["compact"] = compact
    return converter(source_path, dest_path, **kwargs)


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------

def _legacy_convert_main(argv: Sequence[str]) -> int:
    """Run the historical ``gedcomtools convert SOURCE DEST -gx`` interface."""
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
            "  g5 → gx\n"
            "  g5 → g7\n"
            "  g7 → gx\n"
            "  gx → g7\n"
            "  g5/g7 → csv\n\n"
            "Formats:\n"
            "  g5   GEDCOM 5.x  (.ged)\n"
            "  g7   GEDCOM 7.x  (.ged)\n"
            "  gx   GedcomX     (.json)\n"
            "  csv  One CSV per top-level GEDCOM entity\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_convert.add_argument("source", metavar="SOURCE", help="Path to the source file")
    p_convert.add_argument("dest", metavar="DEST", help="Path to the output file")
    fmt_group = p_convert.add_mutually_exclusive_group(required=True)
    fmt_group.add_argument("-g5", dest="dest_type", action="store_const", const="g5", help="Convert to GEDCOM 5.x")
    fmt_group.add_argument("-g7", dest="dest_type", action="store_const", const="g7", help="Convert to GEDCOM 7.x")
    fmt_group.add_argument("-gx", dest="dest_type", action="store_const", const="gx", help="Convert to GedcomX JSON")
    fmt_group.add_argument("-csv", dest="dest_type", action="store_const", const="csv", help="Export to CSV files")
    p_convert.add_argument(
        "--on-unknown",
        dest="on_unknown",
        choices=["drop", "convert"],
        default="drop",
        help=(
            "How to handle vendor/non-standard G5 tags (RIN, FSID, AFN, WWW, ADR4-6) "
            "during G5→G7 conversion. "
            "'drop' (default) discards them; "
            "'convert' renames them to _TAG extension tags declared in HEAD.SCHMA."
        ),
    )
    p_convert.add_argument("--quiet", action="store_true", help="Suppress status output")
    p_convert.add_argument("--compact", action="store_true", help="Write compact JSON when the target is JSON")
    p_convert.set_defaults(func=cmd_convert)

    args = parser.parse_args(list(argv))
    return args.func(args)


def _looks_like_legacy_convert(argv: Sequence[str]) -> bool:
    """Return True for the old conversion syntax kept for compatibility."""
    if not argv or argv[0] != "convert":
        return False
    if any(arg in {"-g5", "-g7", "-gx", "-csv"} for arg in argv[1:]):
        return True
    if len(argv) >= 4 and not argv[2].startswith("-"):
        return True
    return False


def main(argv: Optional[Sequence[str]] = None) -> None:
    """Entry point for the ``gedcomtools`` CLI.

    ``gedcomtools`` now exposes the richer ``gctool`` command surface. The
    original ``gedcomtools convert SOURCE DEST -gx`` syntax is still accepted
    so existing scripts continue to work.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if _looks_like_legacy_convert(args):
        sys.exit(_legacy_convert_main(args))

    from gedcomtools.gctool import main as gctool_main

    sys.exit(gctool_main(args, prog="gedcomtools"))


if __name__ == "__main__":
    main()
