#!/usr/bin/env python3
"""
======================================================================
 Project: gedcomtools
 File:    gedcom7/g7cli.py
 Author:  David J. Cartwright
 Purpose: Interactive GEDCOM 7 browser and editor shell.

 Created: 2026-03-15
 Updated:
   - 2026-03-15: initial implementation; load/edit/write/validate/find
   - 2026-03-15: unsaved-changes guard; payload search in find command
   - 2026-03-16: added reload command; _rebuild_tag_index() after add/rm top-level;
                 warn when adding top-level record that requires an xref id;
                 show command displays model summary for INDI/FAM top-level nodes;
                 find results show full node path via get_path()
   - 2026-03-16: import updated GedcomStructure.py → structure.py
======================================================================

g7cli — interactive GEDCOM 7 browser / editor.

Usage::

    g7cli [file.ged]

Commands
--------
load <path>            Load a GEDCOM 7 file.
write <path>           Write the current file to *path*.
validate               Run the GEDCOM 7 validator and show issues.
info                   Show file-level summary.
ls                     List children of the current node (or top-level records).
cd <ref>               Navigate: index, tag name, xref id (@I1@), or .. to go up.
pwd                    Print the current path.
show [--all]           Show the current node's fields.  --all includes children.
find <tag> [--payload <text>]   Search for nodes by tag, optionally filtering by payload text.
reload                 Re-read the current file from disk, discarding in-memory changes.
set payload <value>    Change the payload of the current node.
set tag <value>        Change the tag of the current node.
set xref <value>       Change the xref id of the current node.
add <tag> [payload]    Add a child to the current node.
rm <index>             Remove child at *index* from the current node.
help                   Show this help.
quit / exit            Exit the shell.
"""

from __future__ import annotations

import os
import re
import shlex
import sys
from pathlib import Path
from typing import List, Optional

from .structure import GedcomStructure
from .gedcom7 import Gedcom7, GedcomValidationError
from .writer import Gedcom7Writer
from .models import individual_detail, family_detail

_VERSION = "0.1"

# ---------------------------------------------------------------------------
# ANSI colour helpers (disabled when not a tty)
# ---------------------------------------------------------------------------

def _colour_enabled() -> bool:
    return sys.stdout.isatty() or "WT_SESSION" in os.environ


def _ansi(code: str, text: str) -> str:
    if not _colour_enabled():
        return text
    return f"\x1b[{code}m{text}\x1b[0m"


def _green(t: str) -> str:  return _ansi("32", t)
def _yellow(t: str) -> str: return _ansi("33", t)
def _cyan(t: str) -> str:   return _ansi("36", t)
def _red(t: str) -> str:    return _ansi("31", t)
def _bold(t: str) -> str:   return _ansi("1",  t)
def _dim(t: str) -> str:    return _ansi("2",  t)


def _clip(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


# ---------------------------------------------------------------------------
# Shell
# ---------------------------------------------------------------------------

class Shell:
    """Interactive GEDCOM 7 shell."""

    def __init__(self) -> None:
        self.g: Optional[Gedcom7] = None          # loaded file
        self.filepath: Optional[Path] = None
        self.cur: Optional[GedcomStructure] = None # current node; None = root
        self._stack: List[GedcomStructure] = []    # navigation history
        self._dirty: bool = False   # True when in-memory tree differs from disk

        self.commands = {
            "load":     self._cmd_load,
            "ld":       self._cmd_load,
            "reload":   self._cmd_reload,
            "rl":       self._cmd_reload,
            "write":    self._cmd_write,
            "validate": self._cmd_validate,
            "val":      self._cmd_validate,
            "info":     self._cmd_info,
            "ls":       self._cmd_ls,
            "list":     self._cmd_ls,
            "cd":       self._cmd_cd,
            "pwd":      self._cmd_pwd,
            "show":     self._cmd_show,
            "find":     self._cmd_find,
            "set":      self._cmd_set,
            "add":      self._cmd_add,
            "rm":       self._cmd_rm,
            "help":     self._cmd_help,
            "?":        self._cmd_help,
        }

    # ------------------------------------------------------------------
    # REPL loop
    # ------------------------------------------------------------------

    def run(self, initial_file: Optional[str] = None) -> None:
        print(f"g7cli {_VERSION}  —  GEDCOM 7 browser/editor  —  type 'help' or '?' for commands")
        if initial_file:
            self._do_load(initial_file)

        while True:
            try:
                line = input(self._prompt()).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return

            if not line:
                continue

            try:
                parts = shlex.split(line)
            except ValueError as exc:
                print(f"! {exc}")
                continue

            cmd, *args = parts

            if cmd in ("quit", "exit", "q"):
                if self._dirty:
                    try:
                        answer = input("Unsaved changes. Quit anyway? [y/N] ").strip().lower()
                    except (EOFError, KeyboardInterrupt):
                        print()
                        return
                    if answer not in ("y", "yes"):
                        continue
                return

            handler = self.commands.get(cmd)
            if handler is None:
                print(f"Unknown command: {cmd!r}. Type 'help' for a list.")
                continue

            try:
                handler(args)
            except Exception as exc:
                print(f"! {type(exc).__name__}: {exc}")

    def _prompt(self) -> str:
        path_str = "/".join(self._path_labels())
        return _bold(_cyan("g7")) + _dim(":/") + _cyan(path_str) + _bold("> ")

    def _path_labels(self) -> List[str]:
        labels = []
        for node in self._stack:
            part = node.tag
            if node.xref_id:
                part = node.xref_id
            labels.append(part)
        if self.cur is not None:
            part = self.cur.tag
            if self.cur.xref_id:
                part = self.cur.xref_id
            labels.append(part)
        return labels

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------

    @property
    def _children(self) -> List[GedcomStructure]:
        """Children of the current node, or top-level records."""
        if self.cur is None:
            return self.g.records if self.g else []
        return self.cur.children

    def _resolve_ref(self, ref: str) -> Optional[GedcomStructure]:
        """Resolve an index, tag name, or xref id to a child node."""
        children = self._children

        # Numeric index
        if re.fullmatch(r"-?\d+", ref):
            idx = int(ref)
            if 0 <= idx < len(children):
                return children[idx]
            print(f"! Index {idx} out of range (0–{len(children)-1}).")
            return None

        # Xref id  (@I1@)
        if ref.startswith("@") and ref.endswith("@"):
            xref = ref.upper()
            for node in children:
                if node.xref_id and node.xref_id.upper() == xref:
                    return node
            # Also search the whole tree if at root
            if self.cur is None and self.g:
                found = self._find_by_xref(xref)
                if found:
                    return found
            print(f"! No child with xref id {ref!r}.")
            return None

        # Tag name (first match)
        tag = ref.upper()
        for node in children:
            if node.tag == tag:
                return node
        print(f"! No child with tag {tag!r}.")
        return None

    def _find_by_xref(self, xref: str) -> Optional[GedcomStructure]:
        if not self.g:
            return None
        for record in self.g.records:
            result = self._walk_for_xref(record, xref)
            if result:
                return result
        return None

    def _walk_for_xref(
        self, node: GedcomStructure, xref: str
    ) -> Optional[GedcomStructure]:
        if node.xref_id and node.xref_id.upper() == xref:
            return node
        for child in node.children:
            result = self._walk_for_xref(child, xref)
            if result:
                return result
        return None

    def _require_file(self) -> bool:
        if self.g is None:
            print("! No file loaded. Use: load <path.ged>")
            return False
        return True

    def _require_node(self) -> bool:
        if self.cur is None:
            print("! No node selected. Use 'cd' to navigate into a record first.")
            return False
        return True

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def _cmd_load(self, args: List[str]) -> None:
        """load <path>  — load a GEDCOM 7 file."""
        if len(args) != 1:
            print("usage: load <path.ged>")
            return
        self._do_load(args[0])

    def _cmd_reload(self, args: List[str]) -> None:
        """reload  — re-read the current file from disk, discarding in-memory changes."""
        if self.filepath is None:
            print("! No file loaded. Use: load <path.ged>")
            return
        # Bypass dirty-check: caller explicitly wants to discard changes
        path = self.filepath
        self._dirty = False
        self._do_load(str(path))

    def _do_load(self, path: str) -> None:
        if self._dirty:
            try:
                answer = input("Unsaved changes will be lost. Continue? [y/N] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if answer not in ("y", "yes"):
                print("Load cancelled.")
                return
        p = Path(path)
        if not p.exists():
            print(f"! File not found: {p}")
            return
        print(f"Loading {p} …")
        g = Gedcom7(p)
        if g.errors:
            print(f"  {_yellow(str(len(g.errors)))} parse issue(s):")
            for e in g.errors[:5]:
                loc = f"line {e.line_num}" if e.line_num else "—"
                print(f"    {loc}: {e.message}")
            if len(g.errors) > 5:
                print(f"    … {len(g.errors) - 5} more")
        self.g = g
        self._dirty = False
        self.filepath = p
        self.cur = None
        self._stack = []
        ver = g.detect_gedcom_version() or "?"
        print(
            f"  Loaded {_green(str(len(g.records)))} records  "
            f"GEDCOM {_bold(ver)}  "
            f"{_dim(str(p))}"
        )

    def _cmd_write(self, args: List[str]) -> None:
        """write <path>  — write the loaded records to a GEDCOM 7 file."""
        if not self._require_file():
            return
        if len(args) != 1:
            print("usage: write <path.ged>")
            return
        dest = Path(args[0])
        writer = Gedcom7Writer()
        writer.write(self.g.records, dest)
        print(f"Written to {_green(str(dest))}")
        self._dirty = False

    def _cmd_validate(self, args: List[str]) -> None:
        """validate  — run the GEDCOM 7 validator."""
        if not self._require_file():
            return
        issues = self.g.validate()
        errors   = [i for i in issues if i.severity == "error"]
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

    def _cmd_info(self, args: List[str]) -> None:
        """info  — file-level summary."""
        if not self._require_file():
            return
        from collections import Counter
        ver = self.g.detect_gedcom_version() or "unknown"
        counts = Counter(r.tag for r in self.g.records)
        print(f"File   : {self.filepath}")
        print(f"Version: GEDCOM {ver}")
        print(f"Records: {len(self.g.records)} total")
        for tag, n in sorted(counts.items()):
            print(f"  {tag:<8} {n}")

    def _cmd_ls(self, args: List[str]) -> None:
        """ls  — list children of the current node (or top-level records)."""
        if not self._require_file():
            return
        children = self._children
        if not children:
            print("(empty)")
            return

        import shutil
        term_width = shutil.get_terminal_size((120, 24)).columns
        w_idx  = max(3, len(str(len(children) - 1)))
        w_xref = max(6, min(12, max((len(n.xref_id or "") for n in children), default=0)))
        w_tag  = max(4, min(10, max((len(n.tag) for n in children), default=0)))
        w_ch   = 4
        w_pay  = term_width - w_idx - w_xref - w_tag - w_ch - 12

        header = (
            f"{'#'.rjust(w_idx)}  "
            f"{'xref'.ljust(w_xref)}  "
            f"{'tag'.ljust(w_tag)}  "
            f"{'ch'.rjust(w_ch)}  "
            f"payload"
        )
        print(_dim(header))
        print(_dim("-" * min(term_width, len(header) + w_pay)))

        for idx, node in enumerate(children):
            xref = node.xref_id or ""
            tag  = node.tag
            ch   = str(len(node.children))
            pay  = node.payload.replace("\n", "↵")
            line = (
                f"{str(idx).rjust(w_idx)}  "
                f"{_yellow(xref.ljust(w_xref))}  "
                f"{_green(tag.ljust(w_tag))}  "
                f"{ch.rjust(w_ch)}  "
                f"{_clip(pay, max(w_pay, 8))}"
            )
            print(line)

    def _cmd_cd(self, args: List[str]) -> None:
        """cd <ref>  — navigate (index, tag, xref, or '..' to go up)."""
        if not self._require_file():
            return
        if not args:
            print("usage: cd <index|tag|@xref@|..>")
            return

        ref = args[0]

        if ref == "..":
            if self._stack:
                self.cur = self._stack.pop()
            else:
                self.cur = None
            return

        if ref == "/":
            self.cur = None
            self._stack = []
            return

        node = self._resolve_ref(ref)
        if node is None:
            return
        if self.cur is not None:
            self._stack.append(self.cur)
        self.cur = node

    def _cmd_pwd(self, args: List[str]) -> None:
        """pwd  — print the current path."""
        labels = self._path_labels()
        print("g7:/" + "/".join(labels))

    def _cmd_show(self, args: List[str]) -> None:
        """show [--all]  — show fields of the current node.  --all includes children."""
        if not self._require_file():
            return

        show_all = "--all" in args

        if self.cur is None:
            ver = self.g.detect_gedcom_version() or "?"
            print(f"Root  GEDCOM {ver}  {len(self.g.records)} records  {self.filepath}")
            return

        n = self.cur
        print(f"level      : {n.level}")
        print(f"tag        : {_green(n.tag)}")
        if n.xref_id:
            print(f"xref_id    : {_yellow(n.xref_id)}")
        if n.payload:
            # Show payload with embedded newlines as ↵
            pay_display = n.payload.replace("\n", "↵")
            print(f"payload    : {pay_display}")
        print(f"is_pointer : {n.payload_is_pointer}")
        print(f"uri        : {_dim(n.uri or '—')}")
        if n.line_num:
            print(f"source line: {n.line_num}")
        print(f"children   : {len(n.children)}")

        # Model summary for top-level INDI and FAM records
        if n.parent is None and n.tag == "INDI":
            d = individual_detail(n)
            print()
            print(f"  name     : {d.full_name}")
            print(f"  sex      : {d.sex or '—'}")
            print(f"  born     : {d.birth.date if d.birth else '—'}"
                  + (f"  ({d.birth.place})" if d.birth and d.birth.place else ""))
            print(f"  died     : {d.death.date if d.death else '—'}"
                  + (f"  ({d.death.place})" if d.death and d.death.place else ""))
            print(f"  families : child of {len(d.families_as_child)}"
                  f", spouse in {len(d.families_as_spouse)}")
        elif n.parent is None and n.tag == "FAM":
            d = family_detail(n)
            print()
            print(f"  husband  : {d.husband_xref or '—'}")
            print(f"  wife     : {d.wife_xref or '—'}")
            print(f"  children : {d.num_children}")
            print(f"  married  : {d.marriage.date if d.marriage else '—'}")
            print(f"  divorced : {d.divorce.date if d.divorce else '—'}")

        if show_all and n.children:
            print()
            self._cmd_ls([])

    def _cmd_find(self, args: List[str]) -> None:
        """find <tag> [--payload <text>]  — search the whole tree.

        --payload <text>  Only show nodes whose payload contains <text>
                          (case-insensitive).
        """
        if not self._require_file():
            return

        # Parse args: find TAG [--payload TEXT]
        pos: List[str] = []
        payload_filter: Optional[str] = None
        i = 0
        while i < len(args):
            if args[i] == "--payload" and i + 1 < len(args):
                payload_filter = args[i + 1]
                i += 2
            else:
                pos.append(args[i])
                i += 1

        if not pos:
            print("usage: find <tag> [--payload <text>]")
            return

        target = pos[0].upper()
        results: List[GedcomStructure] = []

        def _walk(node: GedcomStructure) -> None:
            if node.tag == target:
                if payload_filter is None or payload_filter.lower() in node.payload.lower():
                    results.append(node)
            for child in node.children:
                _walk(child)

        for record in self.g.records:
            _walk(record)

        if not results:
            filt_msg = f" containing {payload_filter!r}" if payload_filter else ""
            print(f"No nodes found with tag {target!r}{filt_msg}.")
            return

        filt_msg = f" (payload contains {payload_filter!r})" if payload_filter else ""
        print(f"{len(results)} node(s) with tag {_green(target)}{filt_msg}:")
        for node in results[:50]:
            loc = f"line {node.line_num}" if node.line_num else "—"
            pay = _clip(node.payload.replace("\n", "↵"), 50)
            path = node.get_path()
            print(f"  {_dim(loc.ljust(10))}{_yellow(path)}  {pay}")
        if len(results) > 50:
            print(f"  … {len(results) - 50} more results")

    def _cmd_set(self, args: List[str]) -> None:
        """set <field> <value>  — edit a field on the current node.

        Fields: payload, tag, xref
        """
        if not self._require_node():
            return
        if len(args) < 1:
            print("usage: set payload|tag|xref <value>")
            return

        field = args[0].lower()
        value = " ".join(args[1:]) if len(args) > 1 else ""

        if field == "payload":
            self.cur.payload = value
            self.cur.payload_is_pointer = (
                bool(value)
                and value.startswith("@")
                and value.endswith("@")
                and " " not in value
            )
            print(f"payload set to {value!r}")
            self._dirty = True

        elif field == "tag":
            if not value:
                print("! Tag cannot be empty.")
                return
            self.cur.tag = value.upper()
            print(f"tag set to {self.cur.tag!r}")
            self._dirty = True

        elif field in ("xref", "xref_id"):
            self.cur.xref_id = value if value else None
            print(f"xref_id set to {self.cur.xref_id!r}")
            self._dirty = True

        else:
            print(f"! Unknown field {field!r}. Use: payload, tag, or xref")

    def _cmd_add(self, args: List[str]) -> None:
        """add <tag> [payload]  — append a child to the current node."""
        if not self._require_file():
            return
        if not args:
            print("usage: add <tag> [payload]")
            return

        parent = self.cur
        level = (parent.level + 1) if parent is not None else 0
        tag = args[0].upper()
        payload = " ".join(args[1:]) if len(args) > 1 else ""
        payload_is_pointer = (
            bool(payload)
            and payload.startswith("@")
            and payload.endswith("@")
            and " " not in payload
        )

        child = GedcomStructure(
            level=level,
            tag=tag,
            payload=payload,
            payload_is_pointer=payload_is_pointer,
            parent=parent,
        )

        if parent is None:
            # Insert before TRLR if present
            records = self.g.records
            if records and records[-1].tag == "TRLR":
                records.insert(len(records) - 1, child)
            else:
                records.append(child)
            self.g._rebuild_tag_index()
            print(f"Added top-level {_green(tag)} (index {records.index(child)})")
            _REQUIRES_XREF = {"INDI", "FAM", "OBJE", "REPO", "SNOTE", "SOUR", "SUBM"}
            if tag in _REQUIRES_XREF and not child.xref_id:
                print(_yellow(f"  warning: {tag} records must have an xref id — use: set xref <@ID@>"))
        else:
            # GedcomStructure.__init__ already appended via parent.children.append
            print(f"Added child {_green(tag)} at index {len(parent.children) - 1}")
        self._dirty = True

    def _cmd_rm(self, args: List[str]) -> None:
        """rm <index>  — remove a child of the current node by index."""
        if not self._require_file():
            return
        if not args or not re.fullmatch(r"\d+", args[0]):
            print("usage: rm <index>")
            return

        idx = int(args[0])
        children = self._children

        if idx >= len(children):
            print(f"! Index {idx} out of range (0–{len(children)-1}).")
            return

        node = children[idx]
        if self.cur is None:
            self.g.records.pop(idx)
            self.g._rebuild_tag_index()
        else:
            self.cur.children.pop(idx)
            if node.parent is self.cur:
                node.parent = None

        print(f"Removed {_green(node.tag)} (was index {idx})")
        self._dirty = True

    def _cmd_help(self, args: List[str]) -> None:
        """help  — show available commands."""
        print(__doc__)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    args = (argv if argv is not None else sys.argv)[1:]
    shell = Shell()
    shell.run(initial_file=args[0] if args else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
