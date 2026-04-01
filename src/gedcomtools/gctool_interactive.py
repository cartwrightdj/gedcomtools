# -*- coding: utf-8 -*-
"""
======================================================================
 Project: gedcomtools
 File:    gctool_interactive.py
 Purpose: _attribution, _print_status, cmd_interactive, _INTERACTIVE_HELP
 Created: 2026-04-01 — split from gctool.py
======================================================================
"""

from __future__ import annotations

import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from gedcomtools.glog import get_logger

log = get_logger(__name__)

from .gctool_output import _bold, _cyan, _dim, _norm_xref, _yellow
from .gctool_load import _is_url, _load, _load_url
from .gctool_commands import (
    cmd_find, cmd_info, cmd_list, cmd_show, cmd_stats, cmd_tree, cmd_validate,
)
from .gctool_examine import _Node, _run_examine
from .gctool_dataops import cmd_diff, cmd_export, cmd_merge, cmd_repair


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
        print(f"  {_bold('File')}  {_cyan(str(path))}  {_dim(f'[{fmt.upper()}]')}")
        for line in _attribution(fmt, obj):
            print(line)
    print()


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
            print("usage: load FILE|URL")
            return False
        src = tokens[1]
        try:
            if _is_url(src):
                new_fmt, new_obj = _load_url(src)
                new_path = Path(src.split("?")[0].split("/")[-1] or "remote.ged")
            else:
                new_path = Path(src)
                new_fmt, new_obj = _load(new_path)
        except SystemExit:
            return False  # _load/_load_url already printed the error
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
