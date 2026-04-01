# -*- coding: utf-8 -*-
"""
======================================================================
 Project: gedcomtools
 File:    gctool_commands.py
 Purpose: cmd_info, cmd_validate, cmd_list, cmd_show, cmd_find, cmd_tree,
          cmd_stats, cmd_convert, cmd_version, cmd_spec, _package_version,
          _LIST_TYPES
 Created: 2026-04-01 — split from gctool.py
======================================================================
"""

from __future__ import annotations

import importlib.metadata
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from gedcomtools.glog import get_logger

log = get_logger(__name__)

from .gctool_output import (
    _bold, _cyan, _dim, _green, _kv, _norm_xref, _red, _table, _yellow,
)
from .gctool_load import _load


_LIST_TYPES = ("indi", "fam", "sour", "repo", "obje", "subm", "snote")


# ---------------------------------------------------------------------------
# Command: info
# ---------------------------------------------------------------------------

def cmd_info(args) -> int:
    """Handle the `info` command."""
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
        except (AttributeError, NotImplementedError):
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
    """Handle the `validate` command."""
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

def cmd_list(args) -> int:
    """Handle the `list` command."""
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
    """Handle the `show` command."""
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
        except (AttributeError, KeyError, ValueError):
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
    """Handle the `find` command."""
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
            except (AttributeError, TypeError):
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
            except (AttributeError, TypeError):
                children = []
            for child in children:
                _walk_g5(child, record_label, path_parts + [tag])

        try:
            roots = obj._parser.get_root_child_elements()
        except (AttributeError, TypeError) as exc:
            log.debug("get_root_child_elements failed in cmd_find: {}", exc)
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
    """Handle the `tree` command."""
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
        except (AttributeError, KeyError, ValueError):
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
        except (AttributeError, KeyError, ValueError):
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
        except (AttributeError, KeyError, ValueError):
            children = []
        for i, c in enumerate(children):
            _draw_descendants(c.xref_id or "", depth + 1, prefix + ext,
                              i == len(children) - 1)

    detail = None
    try:
        detail = obj.get_individual_detail(xref)
    except (AttributeError, KeyError, ValueError):
        pass
    if detail is None:
        print(f"error: individual {xref!r} not found", file=sys.stderr)
        return 1

    print(f"\n{_bold(_label(xref))}\n")

    print(_bold("Ancestors"))
    try:
        parents = obj.get_parents(xref)
    except (AttributeError, KeyError, ValueError):
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
    except (AttributeError, KeyError, ValueError):
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
    """Handle the `stats` command."""
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
    """Handle the `convert` command."""
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
    except importlib.metadata.PackageNotFoundError:
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
    """Handle the `version` command."""
    print(_package_version())
    return 0


# ---------------------------------------------------------------------------
# Command: spec  (passthrough to g7spec / spectools)
# ---------------------------------------------------------------------------

def cmd_spec(args) -> int:
    """Handle the `spec` command."""
    from gedcomtools.gedcom7.spectools import main as spectools_main
    return spectools_main(["g7spec"] + list(args.spec_args))
