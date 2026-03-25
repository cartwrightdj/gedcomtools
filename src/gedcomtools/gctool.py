#!/usr/bin/env python3
"""
======================================================================
 Project: gedcomtools
 File:    gctool.py
 Purpose: GEDCOM 5/7 command-line utility.

 Created: 2026-03-22
 Updated: 2026-03-24 — dispatch table refactor (examine + interactive REPLs);
                        merge, diff, export, repair subcommands
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
import json
import os
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# ANSI colour helpers
# ---------------------------------------------------------------------------

def _colour_ok() -> bool:
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _c(code: str, text: str) -> str:
    return f"\x1b[{code}m{text}\x1b[0m" if _colour_ok() else text


def _green(t: str) -> str: return _c("32", t)
def _yellow(t: str) -> str: return _c("33", t)
def _red(t: str) -> str: return _c("31", t)
def _cyan(t: str) -> str: return _c("36", t)
def _bold(t: str) -> str: return _c("1", t)
def _dim(t: str) -> str: return _c("2", t)


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

def _sniff(path: Path) -> str:
    """Return 'g5', 'g7', or 'gx'.  Raises ValueError if unknown."""
    suffix = path.suffix.lower()

    if suffix in (".json", ".gedcomx"):
        try:
            with open(path, "rb") as fh:
                if fh.read(1) == b"{":
                    return "gx"
        except OSError:
            pass

    if suffix in (".ged", ".gedcom", ".gdz", ""):
        if suffix == ".gdz":
            return "g7"  # .gdz is always a zipped GEDCOM 7 archive
        try:
            with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if line.startswith("2 VERS"):
                        parts = line.split(None, 2)
                        vers = parts[2] if len(parts) > 2 else ""
                        return "g7" if vers.startswith("7") else "g5"
                    if line.startswith("0 ") and "HEAD" not in line:
                        break
        except OSError:
            pass
        return "g5"  # no VERS found — assume GEDCOM 5

    raise ValueError(
        f"Cannot determine format for {path.name!r}. "
        "Expected .ged/.gedcom/.gdz (GEDCOM) or .json/.gedcomx (GedcomX)."
    )


# ---------------------------------------------------------------------------
# Unified loader
# ---------------------------------------------------------------------------

def _load(path: Path) -> Tuple[str, Any]:
    """Return ``(fmt, obj)`` where *obj* is a ``Gedcom5`` or ``Gedcom7`` instance."""
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        fmt = _sniff(path)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    if fmt == "gx":
        print("error: gctool operates on GEDCOM 5/7 files. Use gxcli for GedcomX.", file=sys.stderr)
        sys.exit(1)

    if fmt == "g5":
        from gedcomtools.gedcom5.gedcom5 import Gedcom5
        obj = Gedcom5()
        try:
            obj.loadfile(path)
        except Exception as exc:
            print(f"error loading {path}: {exc}", file=sys.stderr)
            sys.exit(1)
        return "g5", obj

    # g7
    from gedcomtools.gedcom7.gedcom7 import Gedcom7
    obj = Gedcom7()
    try:
        if path.suffix.lower() == ".gdz":
            with zipfile.ZipFile(path) as zf:
                ged_names = [n for n in zf.namelist() if n.endswith(".ged")]
                if not ged_names:
                    print(f"error: no .ged file inside {path.name}", file=sys.stderr)
                    sys.exit(1)
                obj.parse_string(zf.read(ged_names[0]).decode("utf-8-sig"))
        else:
            obj.loadfile(path)
    except Exception as exc:
        print(f"error loading {path}: {exc}", file=sys.stderr)
        sys.exit(1)
    return "g7", obj


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _table(
    headers: List[str],
    rows: List[List[str]],
    *,
    json_out: bool = False,
    json_key: str = "records",
) -> None:
    if json_out:
        data = [
            {h: (row[i] if i < len(row) else "") for i, h in enumerate(headers)}
            for row in rows
        ]
        print(json.dumps({json_key: data}, ensure_ascii=False, indent=2))
        return
    if not rows:
        print("  (no records)")
        return
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(_bold(fmt.format(*headers)))
    print(_dim("  ".join("-" * w for w in widths)))
    for row in rows:
        padded = [str(row[i]) if i < len(row) else "" for i in range(len(headers))]
        print(fmt.format(*padded))


def _kv(pairs: List[Tuple[str, Any]], *, json_out: bool = False) -> None:
    if json_out:
        print(json.dumps(
            {k: v for k, v in pairs if v is not None},
            ensure_ascii=False, indent=2, default=str,
        ))
        return
    width = max((len(k) for k, _ in pairs), default=10)
    for k, v in pairs:
        if v is not None and v != [] and v != "":
            print(f"  {_cyan(k.ljust(width))}  {v}")


def _norm_xref(xref: str) -> str:
    xref = xref.strip()
    if not xref.startswith("@"):
        xref = f"@{xref}@"
    return xref.upper()


# ---------------------------------------------------------------------------
# Command: info
# ---------------------------------------------------------------------------

def cmd_info(args) -> int:
    path = Path(args.file)
    fmt, obj = _load(path)
    version = obj.detect_gedcom_version() or "unknown"

    _TAG_METHOD = {
        "INDI": "individuals", "FAM": "families", "SOUR": "sources",
        "REPO": "repositories", "OBJE": "media_objects", "SUBM": "submitters",
        "SNOTE": "shared_notes",
    }
    counts: Dict[str, int] = {}
    for tag, method in _TAG_METHOD.items():
        try:
            items = getattr(obj, method)()
            if items:
                counts[tag] = len(items)
        except Exception:
            pass

    if args.json:
        print(json.dumps({
            "file": str(path), "format": f"GEDCOM {fmt[-1]}",
            "version": version, "counts": counts,
        }, indent=2))
        return 0

    print(f"File    : {path}")
    print(f"Format  : GEDCOM {fmt[-1]}  (version {_bold(version)})")
    print(f"Records :")
    for tag, n in counts.items():
        print(f"  {tag:<8} {_green(str(n))}")
    return 0


# ---------------------------------------------------------------------------
# Command: validate
# ---------------------------------------------------------------------------

def cmd_validate(args) -> int:
    path = Path(args.file)
    fmt, obj = _load(path)

    issues = obj.validate()
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]

    if args.json:
        print(json.dumps({
            "format": fmt,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "issues": [
                {"severity": i.severity, "code": i.code, "message": i.message,
                 "line": i.line_num, "tag": i.tag}
                for i in issues
            ],
        }, indent=2))
        return 1 if errors else 0

    for w in warnings:
        loc = f"line {w.line_num}" if w.line_num else "—"
        tag = f" [{w.tag}]" if w.tag else ""
        print(f"  {_yellow('warning')}  {loc}{tag}  {w.code}: {w.message}")
    for e in errors:
        loc = f"line {e.line_num}" if e.line_num else "—"
        tag = f" [{e.tag}]" if e.tag else ""
        print(f"  {_red('error')}    {loc}{tag}  {e.code}: {e.message}")

    status = _red(f"{len(errors)} error(s)") if errors else _green("0 error(s)")
    print(f"\n{status}, {_yellow(str(len(warnings)))} warning(s)")
    return 1 if errors else 0


# ---------------------------------------------------------------------------
# Command: list
# ---------------------------------------------------------------------------

_LIST_TYPES = ("indi", "fam", "sour", "repo", "obje", "subm", "snote")


def cmd_list(args) -> int:
    path = Path(args.file)
    rtype = (args.type or "indi").lower()
    fmt, obj = _load(path)

    if rtype == "indi":
        rows = [
            [d.xref, d.full_name, d.sex or "—",
             str(d.birth_year or "—"), str(d.death_year or "—")]
            for d in obj.individual_details()
        ]
        _table(["xref", "name", "sex", "born", "died"], rows,
               json_out=args.json, json_key="individuals")

    elif rtype == "fam":
        rows = [
            [d.xref, d.husband_xref or "—", d.wife_xref or "—",
             str(d.marriage_year or "—"), str(d.num_children)]
            for d in obj.family_details()
        ]
        _table(["xref", "husband", "wife", "married", "children"], rows,
               json_out=args.json, json_key="families")

    elif rtype == "sour":
        rows = [
            [d.xref, d.title or "—", d.author or "—"]
            for d in obj.source_details()
        ]
        _table(["xref", "title", "author"], rows,
               json_out=args.json, json_key="sources")

    elif rtype == "repo":
        rows = [
            [d.xref, d.name or "—", d.address or "—"]
            for d in obj.repository_details()
        ]
        _table(["xref", "name", "address"], rows,
               json_out=args.json, json_key="repositories")

    elif rtype == "obje":
        rows = [
            [d.xref, d.title or "—", str(len(d.files))]
            for d in obj.media_details()
        ]
        _table(["xref", "title", "files"], rows,
               json_out=args.json, json_key="media")

    elif rtype == "subm":
        rows = [
            [d.xref, d.name or "—"]
            for d in obj.submitter_details()
        ]
        _table(["xref", "name"], rows,
               json_out=args.json, json_key="submitters")

    elif rtype == "snote":
        if fmt == "g5":
            print("error: SNOTE is a GEDCOM 7 feature.", file=sys.stderr)
            return 1
        rows = [
            [d.xref, (d.text[:60] + "…") if len(d.text) > 60 else d.text]
            for d in obj.shared_note_details()
        ]
        _table(["xref", "text"], rows,
               json_out=args.json, json_key="shared_notes")

    else:
        print(f"error: unknown type {rtype!r}. Choose: {', '.join(_LIST_TYPES)}", file=sys.stderr)
        return 1

    return 0


# ---------------------------------------------------------------------------
# Command: show
# ---------------------------------------------------------------------------

def cmd_show(args) -> int:
    path = Path(args.file)
    xref = _norm_xref(args.xref)
    fmt, obj = _load(path)

    lookup = [
        ("INDI", obj.get_individual_detail),
        ("FAM",  obj.get_family_detail),
        ("SOUR", obj.get_source_detail),
        ("REPO", obj.get_repository_detail),
        ("OBJE", obj.get_media_detail),
        ("SUBM", obj.get_submitter_detail),
    ]
    if fmt == "g7":
        lookup.append(("SNOTE", obj.get_shared_note_detail))

    for tag, getter in lookup:
        try:
            detail = getter(xref)
        except Exception:
            continue
        if detail is None:
            continue

        d = detail
        if not args.json:
            print(f"\n{_bold(tag)}  {_yellow(xref)}\n")

        if tag == "INDI":
            born = (f"{d.birth.date or '?'}  {d.birth.place or ''}".strip()
                    if d.birth else None)
            died = (f"{d.death.date or '?'}  {d.death.place or ''}".strip()
                    if d.death else None)
            pairs = [
                ("xref", d.xref), ("name", d.full_name), ("sex", d.sex),
                ("born", born), ("died", died),
                ("occupation", d.occupation), ("title", d.title),
                ("religion", d.religion), ("nationality", d.nationality),
                ("family (child)", ", ".join(lnk.xref for lnk in d.families_as_child) or None),
                ("family (spouse)", ", ".join(d.families_as_spouse) or None),
                ("sources", len(d.source_citations) or None),
                ("notes", len(d.note_texts) or None),
                ("uid", d.uid), ("restriction", d.restriction),
                ("last changed", d.last_changed),
            ]
        elif tag == "FAM":
            born_m = (f"{d.marriage.date or '?'}  {d.marriage.place or ''}".strip()
                      if d.marriage else None)
            div = (f"{d.divorce.date or '?'}  {d.divorce.place or ''}".strip()
                   if d.divorce else None)
            pairs = [
                ("xref", d.xref), ("husband", d.husband_xref),
                ("wife", d.wife_xref), ("married", born_m), ("divorced", div),
                ("children", ", ".join(d.children_xrefs) or None),
                ("# children", d.num_children or None),
                ("uid", d.uid), ("restriction", d.restriction),
            ]
        elif tag == "SOUR":
            pairs = [
                ("xref", d.xref), ("title", d.title), ("author", d.author),
                ("publication", d.publication), ("abbreviation", d.abbreviation),
                ("repositories", ", ".join(d.repository_refs) or None),
                ("uid", d.uid), ("last changed", d.last_changed),
            ]
        elif tag == "REPO":
            pairs = [
                ("xref", d.xref), ("name", d.name), ("address", d.address),
                ("phone", d.phone), ("email", d.email), ("website", d.website),
                ("uid", d.uid), ("last changed", d.last_changed),
            ]
        elif tag == "OBJE":
            pairs = [("xref", d.xref), ("title", d.title)]
            for fp, form in d.files:
                pairs.append(("file", f"{fp}  [{form}]" if form else fp))
            pairs += [("uid", d.uid), ("last changed", d.last_changed)]
        elif tag == "SUBM":
            pairs = [
                ("xref", d.xref), ("name", d.name), ("address", d.address),
                ("phone", d.phone), ("email", d.email), ("website", d.website),
                ("language", d.language), ("uid", d.uid),
            ]
        elif tag == "SNOTE":
            text = d.text
            pairs = [
                ("xref", d.xref), ("mime", d.mime), ("language", d.language),
                ("text", (text[:200] + "…") if len(text) > 200 else text),
                ("uid", d.uid), ("last changed", d.last_changed),
            ]
        else:
            pairs = []

        _kv(pairs, json_out=args.json)
        return 0

    print(f"error: record {xref!r} not found", file=sys.stderr)
    return 1


# ---------------------------------------------------------------------------
# Command: find
# ---------------------------------------------------------------------------

def cmd_find(args) -> int:
    path = Path(args.file)
    target = args.tag.upper()
    payload_filter: Optional[str] = args.payload
    fmt, obj = _load(path)

    results: List[Dict[str, Any]] = []

    if fmt == "g7":
        def _walk_g7(node: Any, record_label: str) -> None:
            if node.tag == target:
                p = node.payload.replace("\n", "↵") if node.payload else ""
                if payload_filter is None or payload_filter.lower() in p.lower():
                    results.append({
                        "record": record_label,
                        "path": node.get_path(),
                        "line": node.line_num,
                        "payload": p,
                    })
            for child in node.children:
                _walk_g7(child, record_label)

        for record in obj.records:
            label = record.xref_id or record.tag
            _walk_g7(record, label)

    else:
        def _walk_g5(elem: Any, record_label: str, path_parts: List[str]) -> None:
            tag = (getattr(elem, "tag", None) or "").upper()
            val = ""
            try:
                val = elem.get_value() or ""
            except Exception:
                pass
            if tag == target:
                p_str = str(val).replace("\n", "↵")
                if payload_filter is None or payload_filter.lower() in p_str.lower():
                    results.append({
                        "record": record_label,
                        "path": "/" + "/".join(path_parts + [tag]),
                        "line": None,
                        "payload": p_str,
                    })
            try:
                children = elem.get_child_elements()
            except Exception:
                children = []
            for child in children:
                _walk_g5(child, record_label, path_parts + [tag])

        try:
            roots = obj._parser.get_root_child_elements()
        except Exception:
            roots = []
        for root in roots:
            label = getattr(root, "xref_id", None) or getattr(root, "tag", "?")
            _walk_g5(root, label, [])

    if args.json:
        print(json.dumps(
            {"tag": target, "count": len(results), "results": results},
            ensure_ascii=False, indent=2,
        ))
        return 0

    filt_msg = f" containing {payload_filter!r}" if payload_filter else ""
    print(f"{_bold(str(len(results)))} result(s) for {_green(target)}{filt_msg}")
    for r in results[:100]:
        loc = f"line {r['line']}" if r["line"] else "—"
        print(f"  {_dim(loc.ljust(10))}{_yellow(r['path'])}  {r['payload'][:80]}")
    if len(results) > 100:
        print(f"  … {len(results) - 100} more (use --json to see all)")
    return 0


# ---------------------------------------------------------------------------
# Command: tree
# ---------------------------------------------------------------------------

def cmd_tree(args) -> int:
    path = Path(args.file)
    xref = _norm_xref(args.xref)
    max_depth: int = args.depth
    fmt, obj = _load(path)

    def _label(x: str) -> str:
        try:
            d = obj.get_individual_detail(x)
            if d:
                born = str(d.birth_year or "?")
                died = str(d.death_year or "?") if not d.is_living else "living"
                return f"{d.full_name}  {_dim(x)}  {_dim(f'({born}–{died})')}"
        except Exception:
            pass
        return x

    def _draw_ancestors(x: str, depth: int, prefix: str, is_last: bool) -> None:
        if depth > max_depth:
            return
        conn = "└── " if is_last else "├── "
        ext  = "    " if is_last else "│   "
        print(prefix + conn + _label(x))
        try:
            parents = obj.get_parents(x)
        except Exception:
            parents = []
        for i, p in enumerate(parents):
            _draw_ancestors(p.xref_id or "", depth + 1, prefix + ext,
                            i == len(parents) - 1)

    def _draw_descendants(x: str, depth: int, prefix: str, is_last: bool) -> None:
        if depth > max_depth:
            return
        conn = "└── " if is_last else "├── "
        ext  = "    " if is_last else "│   "
        print(prefix + conn + _label(x))
        try:
            children = obj.get_children_of(x)
        except Exception:
            children = []
        for i, c in enumerate(children):
            _draw_descendants(c.xref_id or "", depth + 1, prefix + ext,
                              i == len(children) - 1)

    detail = None
    try:
        detail = obj.get_individual_detail(xref)
    except Exception:
        pass
    if detail is None:
        print(f"error: individual {xref!r} not found", file=sys.stderr)
        return 1

    print(f"\n{_bold(_label(xref))}\n")

    print(_bold("Ancestors"))
    try:
        parents = obj.get_parents(xref)
    except Exception:
        parents = []
    if parents:
        for i, p in enumerate(parents):
            _draw_ancestors(p.xref_id or "", 1, "", i == len(parents) - 1)
    else:
        print("  (none recorded)")

    print()
    print(_bold("Descendants"))
    try:
        children = obj.get_children_of(xref)
    except Exception:
        children = []
    if children:
        for i, c in enumerate(children):
            _draw_descendants(c.xref_id or "", 1, "", i == len(children) - 1)
    else:
        print("  (none recorded)")

    print()
    return 0


# ---------------------------------------------------------------------------
# Command: stats
# ---------------------------------------------------------------------------

def cmd_stats(args) -> int:
    path = Path(args.file)
    fmt, obj = _load(path)

    indis = obj.individual_details()
    fams  = obj.family_details()
    n  = len(indis)
    nf = len(fams)

    with_name  = sum(1 for d in indis if d.full_name != "Unknown")
    with_birth = sum(1 for d in indis if d.birth_year)
    with_death = sum(1 for d in indis if d.death_year)
    living     = sum(1 for d in indis if d.is_living)
    males      = sum(1 for d in indis if d.sex == "M")
    females    = sum(1 for d in indis if d.sex == "F")
    birth_years = [d.birth_year for d in indis if d.birth_year]
    with_marr  = sum(1 for d in fams if d.marriage_year)

    def pct(num: int, den: int) -> str:
        return f"{100 * num // den}%" if den else "—"

    if args.json:
        print(json.dumps({
            "individuals": {
                "total": n, "with_name": with_name,
                "with_birth_year": with_birth, "with_death_year": with_death,
                "living": living, "male": males, "female": females,
                "earliest_birth": min(birth_years) if birth_years else None,
                "latest_birth":   max(birth_years) if birth_years else None,
            },
            "families": {
                "total": nf, "with_marriage_year": with_marr,
            },
        }, indent=2))
        return 0

    print(f"{_bold('Individuals')}  {_green(str(n))}")
    print(f"  with name         {with_name:>6}  {pct(with_name, n)}")
    print(f"  with birth year   {with_birth:>6}  {pct(with_birth, n)}")
    print(f"  with death year   {with_death:>6}  {pct(with_death, n)}")
    print(f"  living            {living:>6}  {pct(living, n)}")
    print(f"  male              {males:>6}  {pct(males, n)}")
    print(f"  female            {females:>6}  {pct(females, n)}")
    if birth_years:
        print(f"  birth range       {min(birth_years)} – {max(birth_years)}")
    print()
    print(f"{_bold('Families')}   {_green(str(nf))}")
    print(f"  with marriage year {with_marr:>5}  {pct(with_marr, nf)}")
    return 0


# ---------------------------------------------------------------------------
# Command: convert
# ---------------------------------------------------------------------------

def cmd_convert(args) -> int:
    from gedcomtools.cli import _sniff_source_type, _CONVERSIONS
    source_path = Path(args.file)
    dest_type = args.to.lower()

    if not source_path.exists():
        print(f"error: file not found: {source_path}", file=sys.stderr)
        return 1

    try:
        source_type = _sniff_source_type(source_path)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if source_type == dest_type:
        print("Source and destination formats are the same — nothing to do.")
        return 0

    dest_ext = {"gx": ".json", "g7": ".ged", "g5": ".ged"}.get(dest_type, ".ged")
    dest_path = Path(args.out) if args.out else source_path.with_suffix(dest_ext)

    converter = _CONVERSIONS.get((source_type, dest_type))
    if converter is None:
        supported = ", ".join(f"{s}→{d}" for s, d in _CONVERSIONS)
        print(
            f"error: {source_type.upper()} → {dest_type.upper()} is not supported yet.\n"
            f"Supported conversions: {supported}",
            file=sys.stderr,
        )
        return 1

    return converter(source_path, dest_path)


# ---------------------------------------------------------------------------
# Command: version
# ---------------------------------------------------------------------------

def _package_version() -> str:
    try:
        from importlib.metadata import version
        return version("gedcomtools")
    except Exception:
        pass
    # Fallback for editable installs where metadata may not be present
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            return "unknown"
    toml_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    if toml_path.exists():
        with open(toml_path, "rb") as fh:
            data = tomllib.load(fh)
        return data.get("project", {}).get("version", "unknown")
    return "unknown"


def cmd_version(args) -> int:
    print(_package_version())
    return 0


# ---------------------------------------------------------------------------
# Command: spec  (passthrough to g7spec / spectools)
# ---------------------------------------------------------------------------

def cmd_spec(args) -> int:
    from gedcomtools.gedcom7.spectools import main as spectools_main
    return spectools_main(["g7spec"] + list(args.spec_args))


# ---------------------------------------------------------------------------
# Examine / Edit subsystem
# ---------------------------------------------------------------------------

class _Node:
    """Thin uniform wrapper around a G5 element or G7 GedcomStructure."""

    def __init__(self, raw: Any, fmt: str) -> None:
        self._raw = raw
        self._fmt = fmt

    # ---- identity ----------------------------------------------------------

    @property
    def tag(self) -> str:
        t = self._raw.tag or ""
        return t.upper()

    @property
    def xref_id(self) -> Optional[str]:
        if self._fmt == "g7":
            return getattr(self._raw, "xref_id", None) or None
        return getattr(self._raw, "xref", None) or None

    @property
    def payload(self) -> str:
        if self._fmt == "g7":
            return self._raw.payload or ""
        return self._raw.get_value() or ""

    # ---- tree traversal ----------------------------------------------------

    def children(self) -> List["_Node"]:
        if self._fmt == "g7":
            return [_Node(c, self._fmt) for c in self._raw.children]
        return [_Node(c, self._fmt) for c in self._raw.get_child_elements()]

    def parent(self) -> Optional["_Node"]:
        if self._fmt == "g7":
            p = getattr(self._raw, "parent", None)
            return _Node(p, self._fmt) if p else None
        p = self._raw.get_parent_element()
        return _Node(p, self._fmt) if p else None

    # ---- mutation (G7 only — G5 elements have set_value) -------------------

    def set_payload(self, value: str) -> None:
        if self._fmt == "g7":
            self._raw.payload = value
        else:
            self._raw.set_value(value)

    def add_child(self, tag: str, value: str = "") -> "_Node":
        if self._fmt == "g7":
            from gedcomtools.gedcom7.structure import GedcomStructure
            child_level = (getattr(self._raw, "level", 0) or 0) + 1
            child = GedcomStructure(level=child_level, tag=tag, payload=value)
            self._raw.add_child(child)
            return _Node(child, self._fmt)
        else:
            from gedcomtools.gedcom5.elements import Element
            child_level = (self._raw.level or 0) + 1
            child = Element(child_level, "", tag, value)
            self._raw.add_child_element(child)
            return _Node(child, self._fmt)

    def remove_child(self, child: "_Node") -> None:
        if self._fmt == "g7":
            self._raw.children.remove(child._raw)
            child._raw.parent = None
        else:
            kids = self._raw.get_child_elements()
            if child._raw in kids:
                kids.remove(child._raw)
                child._raw.set_parent_element(None)


# ---- path helpers ----------------------------------------------------------

def _build_label(node: _Node, siblings: List[_Node]) -> str:
    """Return 'TAG' or 'TAG[n]' depending on whether tag is unique among siblings."""
    same = [s for s in siblings if s.tag == node.tag]
    if len(same) <= 1:
        return node.tag
    return f"{node.tag}[{same.index(node)}]"


def _path_str(breadcrumbs: List[str]) -> str:
    return "/".join(breadcrumbs) if breadcrumbs else "/"


# ---- ls display ------------------------------------------------------------

def _ls(node: _Node) -> None:
    kids = node.children()
    if not kids:
        print("  (no children)")
        return
    # Count occurrences of each tag to decide when to show [n] suffix
    from collections import Counter
    tag_counts = Counter(k.tag for k in kids)
    tag_seen: Dict[str, int] = {}
    for i, child in enumerate(kids):
        tag = child.tag
        label = tag if tag_counts[tag] == 1 else f"{tag}[{tag_seen.get(tag, 0)}]"
        tag_seen[tag] = tag_seen.get(tag, 0) + 1
        xref = f"  {_dim(child.xref_id)}" if child.xref_id else ""
        payload = child.payload
        if payload:
            payload = (payload[:60] + _dim("…")) if len(payload) > 60 else payload
        has_kids = "+" if child.children() else " "
        print(f"  {_dim(str(i).rjust(3))}  {has_kids} {_cyan(label):<18}{xref}  {payload}")


# ---- examine/edit REPL -----------------------------------------------------

_EXAMINE_HELP = """\
Navigation:
  ls  [or just Enter]      List children of current node
  cd <n|TAG|TAG[n]>        Enter child by index or tag
  ..                       Go up to parent
  /                        Go to root
  pwd                      Show current path

Inspection:
  show                     Full detail of current node
  raw                      Raw tag/level/payload of current node

Edit mode only:
  set <value>              Change payload of current node
  add <TAG> [value]        Append a child to current node
  del                      Delete current node (moves up)
  save                     Persist changes back to the loaded object

  exit / quit              Return to main REPL
"""


class _FileRoot:
    """Virtual root node representing the whole file.

    Contains all top-level records as its children.  Has no parent.
    Allows normal ``ls`` / ``cd`` navigation but refuses mutations.
    """

    tag = "/"
    xref_id: Optional[str] = None
    payload: str = ""

    def __init__(self, fmt: str, root_nodes: List[_Node]) -> None:
        self._fmt = fmt
        self._root_nodes = root_nodes

    def children(self) -> List[_Node]:
        return list(self._root_nodes)

    def parent(self) -> None:  # type: ignore[override]
        return None

    def set_payload(self, value: str) -> None:
        raise ValueError("Cannot set payload on the file root.")

    def add_child(self, tag: str, value: str = "") -> _Node:
        raise ValueError("Cannot add records at the file root level.")

    def remove_child(self, child: _Node) -> None:
        raise ValueError("Cannot remove records at the file root level.")


def _run_examine(
    roots: List[_Node],
    fmt: str,
    *,
    allow_edit: bool,
) -> None:
    """Inner REPL for examine / edit mode."""
    import shlex

    if not roots:
        print("No records to examine.")
        return

    file_root = _FileRoot(fmt, roots)

    # Start at the file root so the user sees all top-level records first.
    # cursor may be a _Node or the _FileRoot sentinel.
    cursor: Any = file_root
    breadcrumbs: List[str] = ["/"]

    def _at_file_root() -> bool:
        return cursor is file_root

    def _is_top_level(node: Any) -> bool:
        """True when *node* is a direct child of the file root."""
        p = node.parent()
        # G7: top-level nodes have no parent
        # G5: top-level nodes' parent is the RootElement (tag "ROOT", level -1)
        if p is None:
            return True
        raw_tag = (getattr(p._raw, "tag", "") or "").upper() if isinstance(p, _Node) else ""
        return raw_tag == "ROOT"

    def _prompt() -> str:
        path = _path_str(breadcrumbs)
        sep = "#" if allow_edit else ">"
        return _bold(fmt) + ":" + _dim(path) + f":{sep} "

    def _find_child(tokens_rest: List[str]) -> Optional[_Node]:
        if not tokens_rest:
            return None
        arg = tokens_rest[0]
        kids = cursor.children()   # works for both _FileRoot and _Node
        # by index
        if arg.isdigit():
            idx = int(arg)
            if idx < len(kids):
                return kids[idx]
            print(f"  index {idx} out of range (0–{len(kids)-1})")
            return None
        # by TAG[n] or TAG
        m = __import__("re").match(r"^([A-Z_][A-Z0-9_]*)(?:\[(\d+)\])?$", arg.upper())
        if not m:
            print(f"  unrecognised target: {arg!r}")
            return None
        wanted_tag = m.group(1)
        wanted_idx = int(m.group(2)) if m.group(2) else None
        matches = [k for k in kids if k.tag == wanted_tag]
        if not matches:
            print(f"  no child with tag {wanted_tag!r}")
            return None
        if wanted_idx is not None:
            if wanted_idx < len(matches):
                return matches[wanted_idx]
            print(f"  {wanted_tag}[{wanted_idx}] out of range (0–{len(matches)-1})")
            return None
        if len(matches) == 1:
            return matches[0]
        # ambiguous — show options
        print(f"  {len(matches)} children with tag {wanted_tag!r}, specify index:")
        kids_all = cursor.children()
        from collections import Counter
        tag_counts = Counter(k.tag for k in kids_all)
        tag_seen: Dict[str, int] = {}
        for i, child in enumerate(kids_all):
            t = child.tag
            label = t if tag_counts[t] == 1 else f"{t}[{tag_seen.get(t, 0)}]"
            tag_seen[t] = tag_seen.get(t, 0) + 1
            if child in matches:
                print(f"    {_dim(str(i).rjust(3))}  {_cyan(label)}  {child.payload[:60]}")
        return None

    print(f"  {'examine' if not allow_edit else _yellow('edit')} mode  —  "
          f"type 'help' for commands, 'exit' to return")
    print()
    _ls(cursor)
    print()

    # ---- dispatch table for examine/edit REPL --------------------------------

    def _do_help(_rest: List[str]) -> bool:
        print(_EXAMINE_HELP)
        return False

    def _do_ls(_rest: List[str]) -> bool:
        _ls(cursor)
        return False

    def _do_pwd(_rest: List[str]) -> bool:
        print(f"  {_path_str(breadcrumbs)}")
        return False

    def _do_show(_rest: List[str]) -> bool:
        xr = f"  xref     {cursor.xref_id}" if cursor.xref_id else ""
        print(f"  tag      {_cyan(cursor.tag)}")
        if xr:
            print(xr)
        print(f"  payload  {cursor.payload or _dim('(empty)')}")
        print(f"  children {len(cursor.children())}")
        return False

    def _do_raw(_rest: List[str]) -> bool:
        print(f"  {cursor.tag}  {cursor.payload}")
        return False

    def _do_cd(rest: List[str]) -> bool:
        nonlocal cursor, breadcrumbs
        child = _find_child(rest)
        if child is not None:
            label = _build_label(child, cursor.children())
            breadcrumbs.append(label)
            cursor = child
        return False

    def _do_dotdot(_rest: List[str]) -> bool:
        nonlocal cursor, breadcrumbs
        if _at_file_root():
            print("  already at file root")
        elif _is_top_level(cursor):
            cursor = file_root
            breadcrumbs = ["/"]
            _ls(cursor)
        else:
            p: Optional[Any] = cursor.parent()
            if p is None or (isinstance(p, _Node) and
                             (getattr(p._raw, "tag", "") or "").upper() == "ROOT"):
                cursor = file_root
                breadcrumbs = ["/"]
            else:
                breadcrumbs.pop() if len(breadcrumbs) > 1 else None
                cursor = p
        return False

    def _do_root(_rest: List[str]) -> bool:
        nonlocal cursor, breadcrumbs
        cursor = file_root
        breadcrumbs = ["/"]
        _ls(cursor)
        return False

    def _do_set(rest: List[str]) -> bool:
        if not allow_edit:
            print("  use 'edit' mode to modify nodes")
        elif _at_file_root():
            print("  cannot set payload on the file root")
        elif not rest:
            print("  usage: set <value>")
        else:
            new_val = " ".join(rest)
            cursor.set_payload(new_val)
            print(f"  set → {new_val}")
        return False

    def _do_add(rest: List[str]) -> bool:
        if not allow_edit:
            print("  use 'edit' mode to modify nodes")
        elif _at_file_root():
            print("  cannot add records at the file root level")
        elif not rest:
            print("  usage: add <TAG> [value]")
        else:
            new_tag = rest[0].upper()
            new_val = " ".join(rest[1:])
            try:
                new_child = cursor.add_child(new_tag, new_val)
                print(f"  added {new_child.tag}  {new_val}")
                _ls(cursor)
            except Exception as exc:
                print(f"  error: {exc}")
        return False

    def _do_del(_rest: List[str]) -> bool:
        nonlocal cursor, breadcrumbs
        if not allow_edit:
            print("  use 'edit' mode to modify nodes")
        elif _at_file_root():
            print("  cannot delete the file root")
        else:
            parent: Optional[Any] = cursor.parent()
            if parent is None or _is_top_level(cursor):
                print("  cannot delete a root record")
            else:
                confirm = input(f"  delete {cursor.tag!r}? [y/N] ").strip().lower()
                if confirm == "y":
                    parent.remove_child(cursor)
                    breadcrumbs.pop() if len(breadcrumbs) > 1 else None
                    cursor = parent
                    print(f"  deleted — now at {_path_str(breadcrumbs)}")
                    _ls(cursor)
        return False

    def _do_save(_rest: List[str]) -> bool:
        if not allow_edit:
            print("  nothing to save in examine mode")
        else:
            print("  (changes are held in memory — use 'convert' or write to save to disk)")
        return False

    _examine_dispatch: Dict[str, Any] = {
        "help":     _do_help,
        "ls":       _do_ls,
        "list":     _do_ls,
        "pwd":      _do_pwd,
        "show":     _do_show,
        "raw":      _do_raw,
        "cd":       _do_cd,
        "cl":       _do_cd,
        "chlevel":  _do_cd,
        "..":       _do_dotdot,
        "/":        _do_root,
        "set":      _do_set,
        "add":      _do_add,
        "del":      _do_del,
        "save":     _do_save,
    }

    # ---- REPL loop -----------------------------------------------------------

    while True:
        try:
            line = input(_prompt()).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            _ls(cursor)
            continue
        try:
            tokens = shlex.split(line)
        except ValueError as exc:
            print(f"  parse error: {exc}")
            continue

        cmd = tokens[0].lower()
        rest = tokens[1:]

        if cmd in ("exit", "quit"):
            break

        handler = _examine_dispatch.get(cmd)
        if handler is not None:
            handler(rest)
        elif re.match(r"^[A-Z_][A-Z0-9_]*(\[\d+\])?$", cmd.upper()):
            # plain TAG (or TAG[n]) as shortcut for cd
            _do_cd([cmd.upper()] + rest)
        else:
            print(f"  unknown command: {cmd!r}  (type 'help' for a list)")

    # nothing to clean up — outer edit_mode is managed by the caller


# ---------------------------------------------------------------------------
# Command: interactive
# ---------------------------------------------------------------------------

_INTERACTIVE_HELP = """\
Commands:
  load FILE                Load a GEDCOM file
  info                     File summary
  validate                 Validate the file
  list [TYPE]              List records (indi|fam|sour|repo|obje|subm|snote)
  show XREF                Show all fields for a record
  find TAG [TEXT]          Find nodes by tag (optional payload filter)
  tree XREF [DEPTH]        ASCII ancestry/descendant tree
  stats                    Completeness summary
  examine [XREF]           Browse the GEDCOM tree (read-only)
  edit    [XREF]           Browse and modify the GEDCOM tree
  merge FILE2 [OUT]        Merge current file with FILE2
  diff  FILE2              Structural diff against FILE2
  export [csv [OUT]]       Dump individuals/families to CSV
  repair [OUT]             Auto-fix common validation issues
  help                     Show this message
  exit / quit              Exit the REPL
"""


def _attribution(fmt: str, obj: Any) -> List[str]:
    """Return lines describing the HEAD attribution of a loaded file."""
    lines: List[str] = []
    try:
        if fmt == "g7":
            head = next((r for r in obj.records if r.tag == "HEAD"), None)
            if head is None:
                return lines
            def _first(node, *tags):
                cur = node
                for tag in tags:
                    cur = cur.first_child(tag) if cur else None
                return (cur.payload or "").strip() if cur else None

            src  = _first(head, "SOUR")
            ver  = _first(head, "SOUR", "VERS")
            corp = _first(head, "SOUR", "CORP")
            date = _first(head, "DATE")
            lang = _first(head, "LANG")
            subm_xref = _first(head, "SUBM")
            subm_name = None
            if subm_xref:
                try:
                    sd = obj.get_submitter_detail(subm_xref)
                    subm_name = sd.name if sd else None
                except Exception:
                    pass

            if src:
                label = src
                if ver:
                    label += f" {ver}"
                if corp:
                    label += f" ({corp})"
                lines.append(f"  {'Source':<12} {label}")
            if subm_name:
                lines.append(f"  {'Submitter':<12} {subm_name}")
            if date:
                lines.append(f"  {'Date':<12} {date}")
            if lang:
                lines.append(f"  {'Language':<12} {lang}")

        else:  # g5
            src  = None
            date = None
            subm = None
            try:
                for el in obj._parser.get_root_child_elements():
                    tag = (getattr(el, "tag", "") or "").upper()
                    if tag != "HEAD":
                        continue
                    for ch in el.get_child_elements():
                        ctag = (getattr(ch, "tag", "") or "").upper()
                        if ctag == "SOUR":
                            src = ch.get_value() or None
                        elif ctag == "DATE":
                            date = ch.get_value() or None
                        elif ctag == "SUBM":
                            subm_xref = (ch.get_value() or "").strip()
                            if subm_xref:
                                xref_dict = obj._parser.get_element_dictionary()
                                subm_el = xref_dict.get(subm_xref.upper())
                                if subm_el is not None:
                                    for sc in subm_el.get_child_elements():
                                        if (getattr(sc, "tag", "") or "").upper() == "NAME":
                                            subm = sc.get_value() or subm_xref
                                            break
                                    else:
                                        subm = subm_xref
                                else:
                                    subm = subm_xref
            except Exception:
                pass
            if src:
                lines.append(f"  {'Source':<12} {src}")
            if subm:
                lines.append(f"  {'Submitter':<12} {subm}")
            if date:
                lines.append(f"  {'Date':<12} {date}")
    except Exception:
        pass
    return lines


def _print_status(path: Optional[Path], fmt: Optional[str], obj: Optional[Any]) -> None:
    """Print the current-file status block shown at startup and after load."""
    print()
    if path is None or obj is None:
        print(f"  {_yellow('No GEDCOM loaded.')}  Use: load <file>")
    else:
        print(f"  {_bold('File')}  {_cyan(str(path))}  {_dim(f'[{fmt.upper()}]')}")
        for line in _attribution(fmt, obj):
            print(line)
    print()


def cmd_interactive(args) -> int:
    try:
        import readline  # noqa: F401 — enables arrow-key history on most platforms
    except ImportError:
        pass
    import shlex

    print(_bold("gctool interactive") + "  —  type 'help' for commands, 'exit' to quit")

    # File is optional: may be None if invoked bare
    path: Optional[Path] = Path(args.file) if getattr(args, "file", None) else None
    fmt:  Optional[str]  = None
    obj:  Optional[Any]  = None

    if path is not None:
        fmt, obj = _load(path)

    _print_status(path, fmt, obj)

    # Minimal namespace: reuse existing cmd_* functions by faking an args object
    class _NS:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    edit_mode = False

    def _prompt() -> str:
        tag = "gct" if fmt is None else fmt   # "gct", "g5", or "g7"
        sep = "#" if edit_mode else ">"
        return _bold(tag) + f":{sep} "

    def _need_file() -> bool:
        if obj is None:
            print("No file loaded.  Use: load <file>")
            return True
        return False

    # ---- dispatch table for interactive REPL ---------------------------------

    def _icmd_help(tokens: List[str]) -> bool:
        print(_INTERACTIVE_HELP)
        return False

    def _icmd_load(tokens: List[str]) -> bool:
        nonlocal path, fmt, obj
        if len(tokens) < 2:
            print("usage: load FILE")
            return False
        new_path = Path(tokens[1])
        try:
            new_fmt, new_obj = _load(new_path)
        except SystemExit:
            return False  # _load already printed the error
        path, fmt, obj = new_path, new_fmt, new_obj
        _print_status(path, fmt, obj)
        return False

    def _icmd_info(tokens: List[str]) -> bool:
        if not _need_file():
            cmd_info(_NS(file=str(path), json=False))
        return False

    def _icmd_validate(tokens: List[str]) -> bool:
        if not _need_file():
            cmd_validate(_NS(file=str(path), json=False))
        return False

    def _icmd_stats(tokens: List[str]) -> bool:
        if not _need_file():
            cmd_stats(_NS(file=str(path), json=False))
        return False

    def _icmd_list(tokens: List[str]) -> bool:
        if not _need_file():
            rtype = tokens[1].lower() if len(tokens) > 1 else "indi"
            cmd_list(_NS(file=str(path), json=False, type=rtype))
        return False

    def _icmd_show(tokens: List[str]) -> bool:
        if not _need_file():
            if len(tokens) < 2:
                print("usage: show XREF")
            else:
                cmd_show(_NS(file=str(path), json=False, xref=tokens[1]))
        return False

    def _icmd_find(tokens: List[str]) -> bool:
        if not _need_file():
            if len(tokens) < 2:
                print("usage: find TAG [TEXT]")
            else:
                payload = tokens[2] if len(tokens) > 2 else None
                cmd_find(_NS(file=str(path), json=False, tag=tokens[1], payload=payload))
        return False

    def _icmd_tree(tokens: List[str]) -> bool:
        if not _need_file():
            if len(tokens) < 2:
                print("usage: tree XREF [DEPTH]")
            else:
                depth = int(tokens[2]) if len(tokens) > 2 else 3
                cmd_tree(_NS(file=str(path), json=False, xref=tokens[1], depth=depth))
        return False

    def _icmd_examine(tokens: List[str]) -> bool:
        nonlocal edit_mode
        if _need_file():
            return False
        allow_edit = (tokens[0].lower() == "edit")
        raw_roots = obj.records if fmt == "g7" else list(obj._parser.get_root_child_elements())
        xref_arg = tokens[1] if len(tokens) > 1 else None
        if xref_arg:
            target = _norm_xref(xref_arg)
            if fmt == "g7":
                raw_roots = [r for r in raw_roots if getattr(r, "xref_id", None) == target]
            else:
                raw_roots = [r for r in raw_roots
                             if (getattr(r, "xref", None) or "").upper() == target]
            if not raw_roots:
                print(f"  record {xref_arg!r} not found")
                return False
        nodes = [_Node(r, fmt) for r in raw_roots]
        _run_examine(nodes, fmt, allow_edit=allow_edit)
        edit_mode = False
        return False

    def _icmd_merge(tokens: List[str]) -> bool:
        if _need_file():
            return False
        if len(tokens) < 2:
            print("usage: merge FILE2 [OUT]")
            return False
        out = tokens[2] if len(tokens) > 2 else None
        cmd_merge(_NS(file1=str(path), file2=tokens[1], out=out,
                      no_interactive=False, json=False))
        return False

    def _icmd_diff(tokens: List[str]) -> bool:
        if _need_file():
            return False
        if len(tokens) < 2:
            print("usage: diff FILE2")
            return False
        cmd_diff(_NS(file1=str(path), file2=tokens[1], json=False))
        return False

    def _icmd_export(tokens: List[str]) -> bool:
        if _need_file():
            return False
        fmt_arg = tokens[1].lower() if len(tokens) > 1 else "csv"
        out_arg = tokens[2] if len(tokens) > 2 else None
        cmd_export(_NS(file=str(path), to=fmt_arg, out=out_arg, json=False))
        return False

    def _icmd_repair(tokens: List[str]) -> bool:
        if _need_file():
            return False
        out_arg = tokens[1] if len(tokens) > 1 else None
        cmd_repair(_NS(file=str(path), out=out_arg,
                       dry_run=False, fix_links=False, json=False))
        return False

    _interactive_dispatch: Dict[str, Any] = {
        "help":     _icmd_help,
        "load":     _icmd_load,
        "info":     _icmd_info,
        "validate": _icmd_validate,
        "stats":    _icmd_stats,
        "list":     _icmd_list,
        "show":     _icmd_show,
        "find":     _icmd_find,
        "tree":     _icmd_tree,
        "examine":  _icmd_examine,
        "edit":     _icmd_examine,
        "merge":    _icmd_merge,
        "diff":     _icmd_diff,
        "export":   _icmd_export,
        "repair":   _icmd_repair,
    }

    # ---- REPL loop -----------------------------------------------------------

    while True:
        try:
            line = input(_prompt()).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        try:
            tokens = shlex.split(line)
        except ValueError as exc:
            print(f"parse error: {exc}")
            continue

        cmd = tokens[0].lower()

        if cmd in ("exit", "quit"):
            break

        handler = _interactive_dispatch.get(cmd)
        if handler is not None:
            handler(tokens)
        else:
            print(f"unknown command: {cmd!r}. Type 'help' for a list.")

    return 0


# ---------------------------------------------------------------------------
# Helpers: shared by merge / diff / export / repair
# ---------------------------------------------------------------------------

_MONTH_ABBREVS = frozenset(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
     "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
)

_SEX_NORM: Dict[str, str] = {
    "m": "M", "male": "M", "f": "F", "female": "F",
    "x": "X", "intersex": "X", "u": "U", "unknown": "U",
}


def _normalise_name(s: str) -> str:
    """Lowercase, strip GEDCOM surname slashes, collapse whitespace."""
    s = re.sub(r"/([^/]*)/", r"\1", s)
    return " ".join(s.lower().split())


def _merge_key(d: Any) -> Tuple:
    """Duplicate-detection key: (normalised_name, birth_year)."""
    return (_normalise_name(d.full_name), d.birth_year or 0)


def _norm_date_str(s: str) -> str:
    """Normalise a GEDCOM date: collapse whitespace, uppercase month names."""
    parts = s.split()
    return " ".join(p.upper() if p.upper() in _MONTH_ABBREVS else p for p in parts)


def _alloc_xref_remap(obj1: Any, obj2: Any, fmt1: str, fmt2: str) -> Dict[str, str]:
    """Build old-xref → new-xref mapping for every record in obj2 safe for obj1."""
    xrefs1: set = set()
    if fmt1 == "g7":
        for r in obj1.records:
            if r.xref_id:
                xrefs1.add(r.xref_id.upper())
    else:
        for el in obj1._parser.get_root_child_elements():
            xr = (getattr(el, "xref_id", None) or getattr(el, "xref", None) or "").strip()
            if xr:
                xrefs1.add(xr.upper())

    pat = re.compile(r"^@([A-Z_]+)(\d+)@$")
    max_idx: Dict[str, int] = {}
    for x in xrefs1:
        m = pat.match(x)
        if m:
            max_idx[m.group(1)] = max(max_idx.get(m.group(1), 0), int(m.group(2)))

    counters: Dict[str, int] = dict(max_idx)

    def _next(prefix: str) -> str:
        counters[prefix] = counters.get(prefix, 0) + 1
        cand = f"@{prefix}{counters[prefix]}@"
        while cand.upper() in xrefs1:
            counters[prefix] += 1
            cand = f"@{prefix}{counters[prefix]}@"
        xrefs1.add(cand.upper())
        return cand

    remap: Dict[str, str] = {}
    if fmt2 == "g7":
        for r in obj2.records:
            if r.xref_id:
                old = r.xref_id.upper()
                m = pat.match(old)
                remap[old] = _next(m.group(1) if m else r.tag[:4].upper())
    else:
        for el in obj2._parser.get_root_child_elements():
            xr = (getattr(el, "xref_id", None) or getattr(el, "xref", None) or "").strip()
            tag = (getattr(el, "tag", None) or "UNKN").upper()
            if xr:
                old = xr.upper()
                m = pat.match(old)
                remap[old] = _next(m.group(1) if m else tag[:4].upper())
    return remap


def _clone_g7_node(
    node: Any,
    remap: Dict[str, str],
    parent: Optional[Any] = None,
    level: int = 0,
) -> Any:
    """Recursively deep-copy a GedcomStructure, rewriting xrefs via remap."""
    from gedcomtools.gedcom7.structure import GedcomStructure
    new_xref = remap.get((node.xref_id or "").upper()) or node.xref_id
    payload = node.payload
    if node.payload_is_pointer and payload:
        payload = remap.get(payload.upper(), payload)
    clone = GedcomStructure(
        level=level,
        tag=node.tag,
        xref_id=new_xref,
        payload=payload,
        payload_is_pointer=node.payload_is_pointer,
        parent=parent,  # auto-appends to parent.children when not None
    )
    for child in node.children:
        _clone_g7_node(child, remap, parent=clone, level=level + 1)
    return clone


def _parse_g5_blocks(path: Path) -> List[Tuple[str, str, str]]:
    """Parse a G5 file into [(xref, tag, raw_text), …] for every level-0 record."""
    blocks: List[List[str]] = []
    cur: List[str] = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\r\n")
            if line.startswith("0 "):
                if cur:
                    blocks.append(cur)
                cur = [line]
            elif cur:
                cur.append(line)
    if cur:
        blocks.append(cur)

    result: List[Tuple[str, str, str]] = []
    for blk in blocks:
        parts = blk[0].split(None, 3)
        if len(parts) >= 3 and parts[1].startswith("@"):
            xref, tag = parts[1].upper(), parts[2].upper()
        elif len(parts) >= 2:
            xref, tag = "", parts[1].upper()
        else:
            xref, tag = "", ""
        result.append((xref, tag, "\n".join(blk)))
    return result


def _subst_xrefs(text: str, remap: Dict[str, str]) -> str:
    """Replace every @XREF@ token in text using remap (case-insensitive keys)."""
    return re.sub(
        r"@[^@\s]+@",
        lambda m: remap.get(m.group(0).upper(), m.group(0)),
        text,
    )


def _repair_walk_g7(node: Any, counts: Dict[str, int]) -> None:
    """Apply in-place fixes to a G7 node and recurse into children."""
    if node.payload:
        stripped = node.payload.strip()
        if stripped != node.payload:
            node.payload = stripped
            counts["trim_payload"] = counts.get("trim_payload", 0) + 1

    if node.tag == "SEX":
        normed = _SEX_NORM.get(node.payload.lower(), "")
        if normed and normed != node.payload:
            node.payload = normed
            counts["norm_sex"] = counts.get("norm_sex", 0) + 1

    if node.tag == "DATE" and node.payload:
        fixed = _norm_date_str(node.payload)
        if fixed != node.payload:
            node.payload = fixed
            counts["norm_date"] = counts.get("norm_date", 0) + 1

    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", node.payload)
    if cleaned != node.payload:
        node.payload = cleaned
        counts["strip_ctrl"] = counts.get("strip_ctrl", 0) + 1

    for child in node.children:
        _repair_walk_g7(child, counts)


def _repair_walk_g5(el: Any, counts: Dict[str, int]) -> None:
    """Apply in-place fixes to a G5 element and recurse into children."""
    tag = (getattr(el, "tag", None) or "").upper()
    try:
        val = el.get_value() or ""
    except Exception:
        val = ""
    new_val = val

    stripped = new_val.strip()
    if stripped != new_val:
        new_val = stripped
        counts["trim_payload"] = counts.get("trim_payload", 0) + 1

    if tag == "SEX":
        normed = _SEX_NORM.get(new_val.lower(), "")
        if normed and normed != new_val:
            new_val = normed
            counts["norm_sex"] = counts.get("norm_sex", 0) + 1

    if tag == "DATE" and new_val:
        fixed = _norm_date_str(new_val)
        if fixed != new_val:
            new_val = fixed
            counts["norm_date"] = counts.get("norm_date", 0) + 1

    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", new_val)
    if cleaned != new_val:
        new_val = cleaned
        counts["strip_ctrl"] = counts.get("strip_ctrl", 0) + 1

    if new_val != val:
        try:
            el.set_value(new_val)
        except Exception:
            pass

    try:
        children = el.get_child_elements()
    except Exception:
        children = []
    for child in children:
        _repair_walk_g5(child, counts)


# ---------------------------------------------------------------------------
# Command: repair
# ---------------------------------------------------------------------------

def cmd_repair(args) -> int:
    """Auto-fix common validation issues and write a corrected file."""
    path = Path(args.file)
    fmt, obj = _load(path)

    issues_before = obj.validate()
    errors_before  = sum(1 for i in issues_before if i.severity == "error")
    warnings_before = len(issues_before) - errors_before

    counts: Dict[str, int] = {}
    if fmt == "g7":
        for record in obj.records:
            _repair_walk_g7(record, counts)
    else:
        try:
            roots = obj._parser.get_root_child_elements()
        except Exception:
            roots = []
        for el in roots:
            _repair_walk_g5(el, counts)

    issues_after  = obj.validate()
    errors_after   = sum(1 for i in issues_after if i.severity == "error")
    warnings_after = len(issues_after) - errors_after

    out_path = Path(args.out) if args.out else path.with_stem(path.stem + "_repaired")
    dry_run  = getattr(args, "dry_run", False)

    if not dry_run:
        if fmt == "g7":
            obj.write(out_path)
        else:
            with open(out_path, "w", encoding="utf-8") as fh:
                obj._parser.save_gedcom(fh)

    if args.json:
        print(json.dumps({
            "before":  {"errors": errors_before, "warnings": warnings_before},
            "after":   {"errors": errors_after,  "warnings": warnings_after},
            "fixes":   [{"code": k, "count": v} for k, v in sorted(counts.items())],
            "output":  str(out_path) if not dry_run else None,
            "dry_run": dry_run,
        }, indent=2))
    else:
        def _pl(n: int, word: str) -> str:
            return f"{n} {word}{'s' if n != 1 else ''}"
        print(f"Before: {_pl(errors_before, 'error')}, {_pl(warnings_before, 'warning')}")
        if counts:
            print("Fixes applied:")
            for code, n in sorted(counts.items()):
                print(f"  [{code}]  {_pl(n, 'node')}")
        else:
            print("No fixes needed.")
        print(f"After:  {_pl(errors_after, 'error')}, {_pl(warnings_after, 'warning')}")
        if dry_run:
            print(f"[dry-run] would write to: {out_path}")
        else:
            print(f"Repaired file written to: {out_path}")
    return 0


# ---------------------------------------------------------------------------
# Command: export
# ---------------------------------------------------------------------------

def cmd_export(args) -> int:
    """Dump individuals and families to CSV files."""
    import csv as _csv
    path = Path(args.file)
    fmt, obj = _load(path)  # noqa: F841

    if args.to.lower() != "csv":
        print(f"error: unsupported export format {args.to!r}", file=sys.stderr)
        return 1

    base = Path(args.out) if args.out else path.with_suffix("")
    indi_path = base.parent / (base.name + "_individuals.csv")
    fam_path  = base.parent / (base.name + "_families.csv")

    indis = obj.individual_details()
    fams  = obj.family_details()

    with open(indi_path, "w", newline="", encoding="utf-8") as f:
        w = _csv.writer(f)
        w.writerow(["xref", "full_name", "sex",
                    "birth_date", "birth_year", "birth_place",
                    "death_date", "death_year", "death_place",
                    "occupation", "families_as_child", "families_as_spouse"])
        for d in indis:
            w.writerow([
                d.xref, d.full_name, d.sex or "",
                (d.birth.date  or "") if d.birth  else "",
                d.birth_year or "",
                (d.birth.place or "") if d.birth  else "",
                (d.death.date  or "") if d.death  else "",
                d.death_year or "",
                (d.death.place or "") if d.death  else "",
                d.occupation or "",
                ";".join(lnk.xref for lnk in d.families_as_child),
                ";".join(d.families_as_spouse),
            ])

    with open(fam_path, "w", newline="", encoding="utf-8") as f:
        w = _csv.writer(f)
        w.writerow(["xref", "husband_xref", "wife_xref",
                    "marriage_date", "marriage_year", "marriage_place",
                    "divorce_date", "num_children", "children_xrefs"])
        for d in fams:
            w.writerow([
                d.xref, d.husband_xref or "", d.wife_xref or "",
                (d.marriage.date  or "") if d.marriage else "",
                (d.marriage.year  or "") if d.marriage else "",
                (d.marriage.place or "") if d.marriage else "",
                (d.divorce.date   or "") if d.divorce  else "",
                len(d.children_xrefs),
                ";".join(d.children_xrefs),
            ])

    if args.json:
        print(json.dumps({
            "individuals": {"path": str(indi_path), "rows": len(indis)},
            "families":    {"path": str(fam_path),  "rows": len(fams)},
        }, indent=2))
    else:
        print(f"Individuals: {indi_path}  ({len(indis)} rows)")
        print(f"Families:    {fam_path}  ({len(fams)} rows)")
    return 0


# ---------------------------------------------------------------------------
# Command: diff
# ---------------------------------------------------------------------------

def cmd_diff(args) -> int:
    """Show structural differences between two GEDCOM files."""
    fmt1, obj1 = _load(Path(args.file1))
    fmt2, obj2 = _load(Path(args.file2))

    indis1 = {d.xref: d for d in obj1.individual_details()}
    indis2 = {d.xref: d for d in obj2.individual_details()}
    fams1  = {d.xref: d for d in obj1.family_details()}
    fams2  = {d.xref: d for d in obj2.family_details()}

    def _indi_fields(d: Any) -> Dict[str, Any]:
        return {
            "full_name":   d.full_name,
            "sex":         d.sex or "",
            "birth_year":  d.birth_year,
            "birth_place": (d.birth.place  or "") if d.birth  else "",
            "death_year":  d.death_year,
            "death_place": (d.death.place  or "") if d.death  else "",
            "occupation":  d.occupation or "",
        }

    def _fam_fields(d: Any) -> Dict[str, Any]:
        return {
            "husband_xref":   d.husband_xref or "",
            "wife_xref":      d.wife_xref or "",
            "marriage_year":  (d.marriage.year  or "") if d.marriage else "",
            "marriage_place": (d.marriage.place or "") if d.marriage else "",
            "num_children":   len(d.children_xrefs),
        }

    result: Dict[str, Any] = {
        "file1": str(args.file1),
        "file2": str(args.file2),
        "indi": {"added": [], "removed": [], "changed": []},
        "fam":  {"added": [], "removed": [], "changed": []},
    }

    for xref in sorted(set(indis1) | set(indis2)):
        if xref not in indis1:
            result["indi"]["added"].append({"xref": xref, **_indi_fields(indis2[xref])})
        elif xref not in indis2:
            result["indi"]["removed"].append({"xref": xref, **_indi_fields(indis1[xref])})
        else:
            f1, f2 = _indi_fields(indis1[xref]), _indi_fields(indis2[xref])
            diffs = {k: (f1[k], f2[k]) for k in f1 if f1[k] != f2[k]}
            if diffs:
                result["indi"]["changed"].append({"xref": xref, "changes": diffs})

    for xref in sorted(set(fams1) | set(fams2)):
        if xref not in fams1:
            result["fam"]["added"].append({"xref": xref, **_fam_fields(fams2[xref])})
        elif xref not in fams2:
            result["fam"]["removed"].append({"xref": xref, **_fam_fields(fams1[xref])})
        else:
            f1, f2 = _fam_fields(fams1[xref]), _fam_fields(fams2[xref])
            diffs = {k: (f1[k], f2[k]) for k in f1 if f1[k] != f2[k]}
            if diffs:
                result["fam"]["changed"].append({"xref": xref, "changes": diffs})

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    # Human-readable output
    print(f"--- {args.file1}  ({len(indis1)} INDI · {len(fams1)} FAM)")
    print(f"+++ {args.file2}  ({len(indis2)} INDI · {len(fams2)} FAM)")

    def _section(label: str, sec: Dict[str, Any]) -> None:
        total = sum(len(v) for v in sec.values())
        bar = "─" * max(0, 50 - len(label))
        print(f"\n── {label} {bar}")
        if total == 0:
            print("  (no changes)")
            return
        for item in sec["added"]:
            name = item.get("full_name") or item.get("husband_xref") or ""
            print(f"  {_green('+')} {item['xref']:<12} {name}  [added]")
        for item in sec["removed"]:
            name = item.get("full_name") or item.get("husband_xref") or ""
            print(f"  {_red('-')} {item['xref']:<12} {name}  [removed]")
        for item in sec["changed"]:
            print(f"  {_yellow('~')} {item['xref']:<12} [changed]")
            for field, (old, new) in item["changes"].items():
                o = str(old) if old not in (None, "") else "(none)"
                n = str(new) if new not in (None, "") else "(none)"
                print(f"      {field:<18} {o} → {n}")

    _section("INDI", result["indi"])
    _section("FAM",  result["fam"])

    total = sum(
        len(v) for s in (result["indi"], result["fam"]) for v in s.values()
    )
    print(f"\n{total} change{'s' if total != 1 else ''} total")
    return 0


# ---------------------------------------------------------------------------
# Command: merge
# ---------------------------------------------------------------------------

def cmd_merge(args) -> int:
    """Merge two GEDCOM files, detecting duplicate individuals."""
    fmt1, obj1 = _load(Path(args.file1))
    fmt2, obj2 = _load(Path(args.file2))

    if fmt1 != fmt2:
        print(
            f"error: merge requires both files in the same format "
            f"(got {fmt1.upper()} and {fmt2.upper()}). "
            "Convert one file first.",
            file=sys.stderr,
        )
        return 1

    indis1 = obj1.individual_details()
    indis2 = obj2.individual_details()
    fams2  = obj2.family_details()

    n1i = len(indis1)
    n1f = len(obj1.family_details())
    n2i = len(indis2)
    n2f = len(fams2)
    print(f"Loaded {args.file1}: {n1i} individuals, {n1f} families")
    print(f"Loaded {args.file2}: {n2i} individuals, {n2f} families")

    keys1 = {_merge_key(d): d.xref for d in indis1}
    conflicts: List[Tuple[Any, Any]] = []   # (detail1, detail2)
    new_indis:  List[Any] = []

    for d2 in indis2:
        k = _merge_key(d2)
        if k in keys1:
            conflicts.append((keys1[k], d2))
        else:
            new_indis.append(d2)

    print(f"  {len(conflicts)} potential duplicate{'s' if len(conflicts) != 1 else ''} found")

    # Conflict resolution: sets of xrefs from file2 to skip
    skip_xrefs2: set = set()
    no_interactive = getattr(args, "no_interactive", False) or not sys.stdin.isatty()

    for xref1, d2 in conflicts:
        d1_info = f"FILE1  {xref1:<10} {indis1[0].full_name if indis1 else '?'}"
        # find d1 by xref
        d1 = next((d for d in indis1 if d.xref == xref1), None)
        name1 = f"{d1.full_name}  b.{d1.birth_year}" if d1 else xref1
        name2 = f"{d2.full_name}  b.{d2.birth_year or '?'}"
        if no_interactive:
            # default: keep both
            continue
        print(f"\n  Possible duplicate:")
        print(f"    FILE1  {xref1:<10} {name1}")
        print(f"    FILE2  {d2.xref:<10} {name2}")
        while True:
            choice = input(
                "  → (1) keep file1  (2) keep file2  (3) keep both  [Enter] keep both: "
            ).strip()
            if choice == "1":
                skip_xrefs2.add(d2.xref.upper())
                break
            elif choice == "2":
                # remove from file1 — not supported in this implementation
                print("    (keeping file2 version is not yet supported; keeping both)")
                break
            elif choice in ("3", ""):
                break
            else:
                print("    Please enter 1, 2, 3 or press Enter.")

    # Build xref remap for file2
    remap = _alloc_xref_remap(obj1, obj2, fmt1, fmt2)

    # Determine output path
    stem = Path(args.file1).stem
    suffix = Path(args.file1).suffix or ".ged"
    out_path = Path(args.out) if args.out else Path(args.file1).with_name(
        stem + "_merged" + suffix
    )

    added = 0

    if fmt1 == "g7":
        for record in obj2.records:
            # skip HEAD and TRLR from file2
            if record.tag in ("HEAD", "TRLR"):
                continue
            xref_key = (record.xref_id or "").upper()
            if xref_key in skip_xrefs2:
                continue
            clone = _clone_g7_node(record, remap, parent=None, level=0)
            obj1.records.append(clone)
            added += 1
        obj1._rebuild_tag_index()
        obj1.write(out_path)

    else:  # g5 text-based merge
        # read file1 text, strip TRLR
        f1_lines: List[str] = []
        with open(Path(args.file1), encoding="utf-8", errors="replace") as f:
            for line in f:
                stripped = line.rstrip("\r\n")
                if stripped.strip() == "0 TRLR":
                    break
                f1_lines.append(stripped)

        # collect new blocks from file2
        blocks2 = _parse_g5_blocks(Path(args.file2))
        new_blocks: List[str] = []
        for xref, tag, text in blocks2:
            if tag in ("HEAD", "TRLR"):
                continue
            if xref.upper() in skip_xrefs2:
                continue
            new_blocks.append(_subst_xrefs(text, remap))
            added += 1

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(f1_lines))
            if f1_lines:
                f.write("\n")
            for blk in new_blocks:
                f.write(blk + "\n")
            f.write("0 TRLR\n")

    print(f"  {added} record{'s' if added != 1 else ''} added from {args.file2}")
    print(f"Merged file written to: {out_path}")
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

_LIST_TYPES_STR = "|".join(_LIST_TYPES)


def main(argv: Optional[List[str]] = None) -> int:
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
