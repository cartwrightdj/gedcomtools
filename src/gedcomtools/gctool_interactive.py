# -*- coding: utf-8 -*-
"""
======================================================================
 Project: gedcomtools
 File:    gctool_interactive.py
 Purpose: _attribution, _print_status, cmd_interactive, _INTERACTIVE_HELP
 Created: 2026-04-01 — split from gctool.py
 Updated: 2026-04-06 — REPL read-only commands now operate on the already
                       loaded in-memory object so `load URL` sessions no
                       longer fail by trying to reopen a fake local path
                       — track URL-backed sessions explicitly so path-based
                         commands cannot accidentally target same-named local
                         files in the working directory
======================================================================
"""

from __future__ import annotations
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from gedcomtools.glog import get_logger

log = get_logger(__name__)

from .gctool_output import (
    _bold, _cyan, _dim, _green, _kv, _norm_xref, _red, _table, _yellow,
)
from .gctool_load import _is_url, _load, _load_url
from .gctool_examine import _Node, _run_examine
from .gctool_dataops import cmd_diff, cmd_export, cmd_merge, cmd_repair
from .gctool_commands import _LIST_TYPES


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
                except (AttributeError, KeyError):
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
            except (AttributeError, TypeError) as exc:
                log.debug("HEAD parsing failed in _header_lines: {}", exc)
            if src:
                lines.append(f"  {'Source':<12} {src}")
            if subm:
                lines.append(f"  {'Submitter':<12} {subm}")
            if date:
                lines.append(f"  {'Date':<12} {date}")
    except (AttributeError, TypeError) as exc:
        log.debug("_header_lines failed: {}", exc)
    return lines


def _print_status(path: Optional[Path], fmt: Optional[str], obj: Optional[Any]) -> None:
    """Print the current-file status block shown at startup and after load."""
    print()
    if path is None or obj is None:
        print(f"  {_yellow('No GEDCOM loaded.')}  Use: load <file>")
    else:
        fmt_upper = (fmt or "").upper()
        print(f"  {_bold('File')}  {_cyan(str(path))}  {_dim(f'[{fmt_upper}]')}")
        for line in _attribution(fmt or "", obj):
            print(line)
    print()


def _record_counts(obj: Any) -> Dict[str, int]:
    """Return top-level record counts for a loaded Gedcom5/Gedcom7 object."""
    tag_method = {
        "INDI": "individuals", "FAM": "families", "SOUR": "sources",
        "REPO": "repositories", "OBJE": "media_objects", "SUBM": "submitters",
        "SNOTE": "shared_notes",
    }
    counts: Dict[str, int] = {}
    for tag, method in tag_method.items():
        try:
            items = getattr(obj, method)()
            if items:
                counts[tag] = len(items)
        except (AttributeError, NotImplementedError):
            pass
    return counts


def _show_info(path: Optional[Path], fmt: str, obj: Any) -> int:
    """Print an in-memory equivalent of ``gctool info``."""
    version = obj.detect_gedcom_version() or "unknown"
    counts = _record_counts(obj)
    print(f"File    : {path if path is not None else '(in-memory)'}")
    print(f"Format  : GEDCOM {fmt[-1]}  (version {_bold(version)})")
    print("Records :")
    for tag, n in counts.items():
        print(f"  {tag:<8} {_green(str(n))}")
    return 0


def _show_validate(obj: Any) -> int:
    """Print an in-memory equivalent of ``gctool validate``."""
    issues = obj.validate()
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]

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


def _show_list(fmt: str, obj: Any, rtype: str) -> int:
    """Print an in-memory equivalent of ``gctool list``."""
    if rtype == "indi":
        rows = [
            [d.xref, d.full_name, d.sex or "—",
             str(d.birth_year or "—"), str(d.death_year or "—")]
            for d in obj.individual_details()
        ]
        _table(["xref", "name", "sex", "born", "died"], rows)
    elif rtype == "fam":
        rows = [
            [d.xref, d.husband_xref or "—", d.wife_xref or "—",
             str(d.marriage_year or "—"), str(d.num_children)]
            for d in obj.family_details()
        ]
        _table(["xref", "husband", "wife", "married", "children"], rows)
    elif rtype == "sour":
        rows = [[d.xref, d.title or "—", d.author or "—"] for d in obj.source_details()]
        _table(["xref", "title", "author"], rows)
    elif rtype == "repo":
        rows = [[d.xref, d.name or "—", d.address or "—"] for d in obj.repository_details()]
        _table(["xref", "name", "address"], rows)
    elif rtype == "obje":
        rows = [[d.xref, d.title or "—", str(len(d.files))] for d in obj.media_details()]
        _table(["xref", "title", "files"], rows)
    elif rtype == "subm":
        rows = [[d.xref, d.name or "—"] for d in obj.submitter_details()]
        _table(["xref", "name"], rows)
    elif rtype == "snote":
        if fmt == "g5":
            print("error: SNOTE is a GEDCOM 7 feature.", file=sys.stderr)
            return 1
        rows = [
            [d.xref, (d.text[:60] + "…") if len(d.text) > 60 else d.text]
            for d in obj.shared_note_details()
        ]
        _table(["xref", "text"], rows)
    else:
        print(f"error: unknown type {rtype!r}. Choose: {', '.join(_LIST_TYPES)}", file=sys.stderr)
        return 1
    return 0


def _show_record(fmt: str, obj: Any, xref: str) -> int:
    """Print an in-memory equivalent of ``gctool show``."""
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
        print(f"\n{_bold(tag)}  {_yellow(xref)}\n")
        if tag == "INDI":
            born = (f"{d.birth.date or '?'}  {d.birth.place or ''}".strip() if d.birth else None)
            died = (f"{d.death.date or '?'}  {d.death.place or ''}".strip() if d.death else None)
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
            married = (f"{d.marriage.date or '?'}  {d.marriage.place or ''}".strip()
                       if d.marriage else None)
            divorced = (f"{d.divorce.date or '?'}  {d.divorce.place or ''}".strip()
                        if d.divorce else None)
            pairs = [
                ("xref", d.xref), ("husband", d.husband_xref),
                ("wife", d.wife_xref), ("married", married), ("divorced", divorced),
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
        else:
            text = d.text
            pairs = [
                ("xref", d.xref), ("mime", d.mime), ("language", d.language),
                ("text", (text[:200] + "…") if len(text) > 200 else text),
                ("uid", d.uid), ("last changed", d.last_changed),
            ]
        _kv(pairs)
        return 0

    print(f"error: record {xref!r} not found", file=sys.stderr)
    return 1


def _show_find(fmt: str, obj: Any, tag: str, payload_filter: Optional[str]) -> int:
    """Print an in-memory equivalent of ``gctool find``."""
    target = tag.upper()
    results: List[Dict[str, Any]] = []

    if fmt == "g7":
        def _walk_g7(node: Any, record_label: str) -> None:
            if node.tag == target:
                payload = node.payload.replace("\n", "↵") if node.payload else ""
                if payload_filter is None or payload_filter.lower() in payload.lower():
                    results.append({
                        "record": record_label,
                        "path": node.get_path(),
                        "line": node.line_num,
                        "payload": payload,
                    })
            for child in node.children:
                _walk_g7(child, record_label)

        for record in obj.records:
            label = record.xref_id or record.tag
            _walk_g7(record, label)
    else:
        def _walk_g5(elem: Any, record_label: str, path_parts: List[str]) -> None:
            etag = (getattr(elem, "tag", None) or "").upper()
            value = ""
            try:
                value = elem.get_value() or ""
            except (AttributeError, TypeError):
                pass
            if etag == target:
                payload = str(value).replace("\n", "↵")
                if payload_filter is None or payload_filter.lower() in payload.lower():
                    results.append({
                        "record": record_label,
                        "path": "/" + "/".join(path_parts + [etag]),
                        "line": None,
                        "payload": payload,
                    })
            try:
                children = elem.get_child_elements()
            except (AttributeError, TypeError):
                children = []
            for child in children:
                _walk_g5(child, record_label, path_parts + [etag])

        try:
            roots = obj._parser.get_root_child_elements()
        except (AttributeError, TypeError) as exc:
            log.debug("get_root_child_elements failed in _show_find: {}", exc)
            roots = []
        for root in roots:
            label = getattr(root, "xref_id", None) or getattr(root, "tag", "?")
            _walk_g5(root, label, [])

    filt_msg = f" containing {payload_filter!r}" if payload_filter else ""
    print(f"{_bold(str(len(results)))} result(s) for {_green(target)}{filt_msg}")
    for result in results[:100]:
        loc = f"line {result['line']}" if result["line"] else "—"
        print(f"  {_dim(loc.ljust(10))}{_yellow(result['path'])}  {result['payload'][:80]}")
    if len(results) > 100:
        print(f"  … {len(results) - 100} more")
    return 0


def _show_tree(obj: Any, xref: str, max_depth: int) -> int:
    """Print an in-memory equivalent of ``gctool tree``."""
    def _label(person_xref: str) -> str:
        try:
            detail = obj.get_individual_detail(person_xref)
            if detail:
                born = str(detail.birth_year or "?")
                died = str(detail.death_year or "?") if not detail.is_living else "living"
                return f"{detail.full_name}  {_dim(person_xref)}  {_dim(f'({born}–{died})')}"
        except (AttributeError, KeyError, ValueError):
            pass
        return person_xref

    def _draw_ancestors(person_xref: str, depth: int, prefix: str, is_last: bool) -> None:
        if depth > max_depth:
            return
        conn = "└── " if is_last else "├── "
        ext = "    " if is_last else "│   "
        print(prefix + conn + _label(person_xref))
        try:
            parents = obj.get_parents(person_xref)
        except (AttributeError, KeyError, ValueError):
            parents = []
        for i, parent in enumerate(parents):
            _draw_ancestors(parent.xref_id or "", depth + 1, prefix + ext, i == len(parents) - 1)

    def _draw_descendants(person_xref: str, depth: int, prefix: str, is_last: bool) -> None:
        if depth > max_depth:
            return
        conn = "└── " if is_last else "├── "
        ext = "    " if is_last else "│   "
        print(prefix + conn + _label(person_xref))
        try:
            children = obj.get_children_of(person_xref)
        except (AttributeError, KeyError, ValueError):
            children = []
        for i, child in enumerate(children):
            _draw_descendants(child.xref_id or "", depth + 1, prefix + ext, i == len(children) - 1)

    try:
        detail = obj.get_individual_detail(xref)
    except (AttributeError, KeyError, ValueError):
        detail = None
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
        for i, parent in enumerate(parents):
            _draw_ancestors(parent.xref_id or "", 1, "", i == len(parents) - 1)
    else:
        print("  (none recorded)")

    print()
    print(_bold("Descendants"))
    try:
        children = obj.get_children_of(xref)
    except (AttributeError, KeyError, ValueError):
        children = []
    if children:
        for i, child in enumerate(children):
            _draw_descendants(child.xref_id or "", 1, "", i == len(children) - 1)
    else:
        print("  (none recorded)")
    print()
    return 0


def _show_stats(obj: Any) -> int:
    """Print an in-memory equivalent of ``gctool stats``."""
    indis = obj.individual_details()
    fams = obj.family_details()
    n = len(indis)
    nf = len(fams)

    with_name = sum(1 for d in indis if d.full_name != "Unknown")
    with_birth = sum(1 for d in indis if d.birth_year)
    with_death = sum(1 for d in indis if d.death_year)
    living = sum(1 for d in indis if d.is_living)
    males = sum(1 for d in indis if d.sex == "M")
    females = sum(1 for d in indis if d.sex == "F")
    birth_years = [d.birth_year for d in indis if d.birth_year]
    with_marr = sum(1 for d in fams if d.marriage_year)

    def pct(num: int, den: int) -> str:
        return f"{100 * num // den}%" if den else "—"

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


def cmd_interactive(args) -> int:
    """Handle the interactive shell command."""
    try:
        import readline  # noqa: F401 — enables arrow-key history on most platforms
    except ImportError:
        pass
    import shlex

    print(_bold("gctool interactive") + "  —  type 'help' for commands, 'exit' to quit")

    # File is optional: may be None if invoked bare
    path: Optional[Path] = Path(args.file) if getattr(args, "file", None) else None
    display_path: Optional[Path] = path
    fmt: Optional[str] = None
    obj: Optional[Any] = None
    loaded_from_url = False

    if path is not None:
        fmt, obj = _load(path)

    _print_status(display_path, fmt, obj)

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
        nonlocal path, display_path, fmt, obj, loaded_from_url
        if len(tokens) < 2:
            print("usage: load FILE|URL")
            return False
        src = tokens[1]
        try:
            if _is_url(src):
                new_fmt, new_obj = _load_url(src)
                path = None
                display_path = Path(src.split("?")[0].split("/")[-1] or "remote.ged")
                loaded_from_url = True
            else:
                new_path = Path(src)
                new_fmt, new_obj = _load(new_path)
                path = new_path
                display_path = new_path
                loaded_from_url = False
        except SystemExit:
            return False  # _load/_load_url already printed the error
        fmt, obj = new_fmt, new_obj
        _print_status(display_path, fmt, obj)
        return False

    def _icmd_info(tokens: List[str]) -> bool:
        if not _need_file():
            assert fmt is not None and obj is not None
            _show_info(display_path, fmt, obj)
        return False

    def _icmd_validate(tokens: List[str]) -> bool:
        if not _need_file():
            assert obj is not None
            _show_validate(obj)
        return False

    def _icmd_stats(tokens: List[str]) -> bool:
        if not _need_file():
            assert obj is not None
            _show_stats(obj)
        return False

    def _icmd_list(tokens: List[str]) -> bool:
        if not _need_file():
            assert fmt is not None and obj is not None
            rtype = tokens[1].lower() if len(tokens) > 1 else "indi"
            _show_list(fmt, obj, rtype)
        return False

    def _icmd_show(tokens: List[str]) -> bool:
        if not _need_file():
            if len(tokens) < 2:
                print("usage: show XREF")
            else:
                assert fmt is not None and obj is not None
                _show_record(fmt, obj, _norm_xref(tokens[1]))
        return False

    def _icmd_find(tokens: List[str]) -> bool:
        if not _need_file():
            if len(tokens) < 2:
                print("usage: find TAG [TEXT]")
            else:
                assert fmt is not None and obj is not None
                payload = tokens[2] if len(tokens) > 2 else None
                _show_find(fmt, obj, tokens[1], payload)
        return False

    def _icmd_tree(tokens: List[str]) -> bool:
        if not _need_file():
            if len(tokens) < 2:
                print("usage: tree XREF [DEPTH]")
            else:
                assert obj is not None
                depth = int(tokens[2]) if len(tokens) > 2 else 3
                _show_tree(obj, _norm_xref(tokens[1]), depth)
        return False

    def _icmd_examine(tokens: List[str]) -> bool:
        nonlocal edit_mode
        if _need_file():
            return False
        assert obj is not None
        assert fmt is not None
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
        if loaded_from_url or path is None:
            print("merge requires a local file path; reload from disk to use it")
            return False
        out = tokens[2] if len(tokens) > 2 else None
        class _NS:
            def __init__(self, **kw):
                self.__dict__.update(kw)
        cmd_merge(_NS(file1=str(path), file2=tokens[1], out=out, no_interactive=False, json=False))
        return False

    def _icmd_diff(tokens: List[str]) -> bool:
        if _need_file():
            return False
        if len(tokens) < 2:
            print("usage: diff FILE2")
            return False
        if loaded_from_url or path is None:
            print("diff requires a local file path; reload from disk to use it")
            return False
        class _NS:
            def __init__(self, **kw):
                self.__dict__.update(kw)
        cmd_diff(_NS(file1=str(path), file2=tokens[1], json=False))
        return False

    def _icmd_export(tokens: List[str]) -> bool:
        if _need_file():
            return False
        if loaded_from_url or path is None:
            print("export requires a local file path; reload from disk to use it")
            return False
        fmt_arg = tokens[1].lower() if len(tokens) > 1 else "csv"
        out_arg = tokens[2] if len(tokens) > 2 else None
        class _NS:
            def __init__(self, **kw):
                self.__dict__.update(kw)
        cmd_export(_NS(file=str(path), to=fmt_arg, out=out_arg, json=False))
        return False

    def _icmd_repair(tokens: List[str]) -> bool:
        if _need_file():
            return False
        if loaded_from_url or path is None:
            print("repair requires a local file path; reload from disk to use it")
            return False
        out_arg = tokens[1] if len(tokens) > 1 else None
        class _NS:
            def __init__(self, **kw):
                self.__dict__.update(kw)
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
