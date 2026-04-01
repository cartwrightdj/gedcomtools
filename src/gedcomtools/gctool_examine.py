# -*- coding: utf-8 -*-
"""
======================================================================
 Project: gedcomtools
 File:    gctool_examine.py
 Purpose: _Node, _FileRoot, helpers, _run_examine, _EXAMINE_HELP
 Created: 2026-04-01 — split from gctool.py
======================================================================
"""

from __future__ import annotations

import re
import shlex
from collections import Counter
from typing import Any, Dict, List, Optional

from .gctool_output import _bold, _cyan, _dim, _yellow


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


class _Node:
    """Thin uniform wrapper around a G5 element or G7 GedcomStructure."""

    def __init__(self, raw: Any, fmt: str) -> None:
        self._raw = raw
        self._fmt = fmt

    # ---- identity ----------------------------------------------------------

    @property
    def tag(self) -> str:
        """Return the tag for this node."""
        t = self._raw.tag or ""
        return t.upper()

    @property
    def xref_id(self) -> Optional[str]:
        """Return the cross-reference identifier for this node."""
        if self._fmt == "g7":
            return getattr(self._raw, "xref_id", None) or None
        return getattr(self._raw, "xref", None) or None

    @property
    def payload(self) -> str:
        """Return the payload value for this node."""
        if self._fmt == "g7":
            return self._raw.payload or ""
        return self._raw.get_value() or ""

    # ---- tree traversal ----------------------------------------------------

    def children(self) -> List["_Node"]:
        """Return the child nodes."""
        if self._fmt == "g7":
            return [_Node(c, self._fmt) for c in self._raw.children]
        return [_Node(c, self._fmt) for c in self._raw.get_child_elements()]

    def parent(self) -> Optional["_Node"]:
        """Return the parent node."""
        if self._fmt == "g7":
            p = getattr(self._raw, "parent", None)
            return _Node(p, self._fmt) if p else None
        p = self._raw.get_parent_element()
        return _Node(p, self._fmt) if p else None

    # ---- mutation (G7 only — G5 elements have set_value) -------------------

    def set_payload(self, value: str) -> None:
        """Set the payload value for this node."""
        if self._fmt == "g7":
            self._raw.payload = value
        else:
            self._raw.set_value(value)

    def add_child(self, tag: str, value: str = "") -> "_Node":
        """Create and attach a child node using the active GEDCOM backend."""
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
        """Remove a child node."""
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
        """Return the child nodes."""
        return list(self._root_nodes)

    def parent(self) -> None:  # type: ignore[override]
        """Return the parent node."""
        return None

    def set_payload(self, value: str) -> None:
        """Set the payload value for this node."""
        raise ValueError("Cannot set payload on the file root.")

    def add_child(self, tag: str, value: str = "") -> _Node:
        """Reject record creation at the virtual file root."""
        raise ValueError("Cannot add records at the file root level.")

    def remove_child(self, child: _Node) -> None:
        """Remove a child node."""
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
