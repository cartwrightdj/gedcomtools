#!/usr/bin/env python3
"""Schema and type browser mixin for the GedcomX interactive shell."""
from __future__ import annotations

# ======================================================================
#  Project: gedcomtools
#  File:    gxcli_schema.py
#  Purpose: _cmd_schema, _cmd_extras, _cmd_type as a mixin class.
#  Created: 2026-03-31 — split from gxcli.py
# ======================================================================
import json
from typing import Any, get_args, get_origin

from gedcomtools.gedcomx.schemas import SCHEMA, type_repr

from gedcomtools.gedcomx.gxcli_output import (
    ANSI,
    _typename,
    _print_table,
    resolve_path,
    type_of,
)


class _SchemaMixin:
    """Mixin providing schema inspection and type-browser commands."""

    def _cmd_schema(self, args: list[str]) -> None:
        """
        schema help
        schema here
        schema class <ClassName>
        schema extras [ClassName] [--all|--direct]
        schema find <field>
        schema where <TypeExpr>
        schema bases <ClassName>
        schema toplevel
        schema diff [PATH]
        schema json [ClassName]
        """
        if not args or args[0] in ("help", "-h", "--help"):
            print((self._cmd_schema.__doc__ or "").strip())
            return

        sub, *rest = args

        def _class_exists(name: str) -> bool:
            return name in SCHEMA.field_type_table

        def _fields_for_class(name: str) -> dict[str, Any]:
            return SCHEMA.get_class_fields(name) or {}

        def _do_here(_rest: list[str]) -> None:
            clsname = type(self.cur).__name__  # type: ignore[attr-defined]
            fields = _fields_for_class(clsname)
            if not fields:
                print(f"(no schema for {clsname})")
                return
            rows = [[fname, _typename(ftype)] for fname, ftype in sorted(fields.items())]
            _print_table(rows, ["field", "type"])

        def _do_class(_rest: list[str]) -> None:
            if not _rest:
                print("usage: schema class <ClassName>")
                return
            clsname = _rest[0]
            if not _class_exists(clsname):
                print(f"unknown class: {clsname}")
                return
            rows = [[fname, _typename(ftype)] for fname, ftype in sorted(_fields_for_class(clsname).items())]
            _print_table(rows, ["field", "type"])

        def _do_extras(_rest: list[str]) -> None:
            clsname = None
            mode = "--all"
            for a in _rest:
                if a in ("--all", "--direct"):
                    mode = a
                else:
                    clsname = a
            if clsname is None:
                clsname = type(self.cur).__name__  # type: ignore[attr-defined]
            if not _class_exists(clsname):
                print(f"unknown class: {clsname}")
                return
            extras = SCHEMA.get_all_extras(clsname) if mode == "--all" else SCHEMA.get_extras(clsname)
            if not extras:
                print("(no extras)")
                return
            rows = []
            for fname, ftype in sorted(extras.items()):
                src = "inherited" if fname in SCHEMA._inherited_extras.get(clsname, {}) else "direct"
                rows.append([fname, _typename(ftype), src])
            _print_table(rows, ["field", "type", "source"])

        def _do_find(_rest: list[str]) -> None:
            if not _rest:
                print("usage: schema find <field>")
                return
            target_field = _rest[0]
            rows = [
                [clsname, target_field, _typename(fields[target_field])]
                for clsname, fields in sorted(SCHEMA.field_type_table.items())
                if target_field in fields
            ]
            print("(no matches)") if not rows else _print_table(rows, ["class", "field", "type"])

        def _do_where(_rest: list[str]) -> None:
            if not _rest:
                print("usage: schema where <TypeExpr>")
                return
            needle = _rest[0]
            rows = [
                [clsname, fname, _typename(ftype)]
                for clsname, fields in sorted(SCHEMA.field_type_table.items())
                for fname, ftype in fields.items()
                if needle in _typename(ftype)
            ]
            print("(no matches)") if not rows else _print_table(rows, ["class", "field", "type"])

        def _do_bases(_rest: list[str]) -> None:
            if not _rest:
                print("usage: schema bases <ClassName>")
                return
            clsname = _rest[0]
            bases = SCHEMA._bases.get(clsname, [])
            subs = sorted(SCHEMA._subclasses.get(clsname, set()))
            print("Bases:", ", ".join(bases) if bases else "(none)")
            print("Subclasses:", ", ".join(subs) if subs else "(none)")

        def _do_toplevel(_rest: list[str]) -> None:
            tops = sorted(SCHEMA.get_toplevel().keys())
            if not tops:
                print("(no top-level classes)")
                return
            _print_table([[name] for name in tops], ["toplevel"])

        def _do_json(_rest: list[str]) -> None:
            if _rest:
                clsname = _rest[0]
                if not _class_exists(clsname):
                    print(f"unknown class: {clsname}")
                    return
                payload = {clsname: {k: _typename(v) for k, v in _fields_for_class(clsname).items()}}
            else:
                payload = {k: {f: _typename(t) for f, t in v.items()} for k, v in SCHEMA.field_type_table.items()}
            print(json.dumps(payload, indent=2, ensure_ascii=False))

        def _do_diff(_rest: list[str]) -> None:
            target = self.cur  # type: ignore[attr-defined]
            if _rest:
                try:
                    target, _ = resolve_path(self.root, self.cur, _rest[0])  # type: ignore[attr-defined]
                except Exception as e:
                    print(f"! bad path: {e}")
                    return
            clsname = type(target).__name__
            fields = _fields_for_class(clsname)
            if not fields:
                print(f"(no schema for {clsname})")
                return
            runtime: dict[str, Any] = {
                k: v for k, v in vars(target).items()
                if not k.startswith("_") and not callable(v)
            } if hasattr(target, "__dict__") else {}
            rows: list[list[str]] = []
            for fname, stype in sorted(fields.items()):
                sname = _typename(stype)
                if hasattr(target, fname):
                    val = getattr(target, fname)
                    rtype = type(val).__name__ if val is not None else "NoneType"
                    ok = (rtype == sname) or (rtype == getattr(stype, "__name__", rtype))
                    rows.append([
                        fname,
                        sname if ok else f"{ANSI['yellow']}{sname}{ANSI['reset']}",
                        rtype if ok else f"{ANSI['red']}{rtype}{ANSI['reset']}",
                        "ok" if ok else f"{ANSI['red']}mismatch{ANSI['reset']}",
                    ])
                else:
                    rows.append([fname, sname, f"{ANSI['red']}(missing){ANSI['reset']}", f"{ANSI['red']}missing{ANSI['reset']}"])
            for k in sorted(k for k in runtime if k not in fields):
                rows.append([
                    f"{ANSI['cyan']}{k}{ANSI['reset']}",
                    f"{ANSI['cyan']}(extra){ANSI['reset']}",
                    type_of(runtime[k]),
                    f"{ANSI['cyan']}extra{ANSI['reset']}",
                ])
            _print_table(rows, ["field", "schema", "runtime", "status"])

        _SCHEMA_SUBS: dict[str, Any] = {
            "here":     _do_here,
            "class":    _do_class,
            "extras":   _do_extras,
            "find":     _do_find,
            "where":    _do_where,
            "bases":    _do_bases,
            "toplevel": _do_toplevel,
            "json":     _do_json,
            "diff":     _do_diff,
        }

        handler = _SCHEMA_SUBS.get(sub)
        if handler is None:
            print(f"unknown subcommand: {sub!r}. Try 'schema help'.")
            return
        handler(rest)

    def _cmd_extras(self, args: list[str]) -> None:
        """
        extras [--all|--direct] [--filter SUBSTR]
        List extras across ALL classes in the schema.
        """
        mode = "--all"
        flt = None

        i = 0
        while i < len(args):
            a = args[i]
            if a in ("--all", "--direct"):
                mode = a
            elif a in ("-f", "--filter"):
                if i + 1 >= len(args):
                    print("missing value for --filter")
                    return
                flt = args[i + 1]
                i += 1
            else:
                print(self._cmd_extras.__doc__.strip())  # type: ignore[union-attr]
                return
            i += 1

        rows = []
        for clsname in sorted(SCHEMA.field_type_table):
            direct = SCHEMA.get_extras(clsname)
            items = (SCHEMA.get_all_extras(clsname) if mode == "--all" else direct).items()
            inherited_names = set(SCHEMA.get_all_extras(clsname).keys()) - set(direct.keys())

            for fname, ftype in sorted(items):
                tstr = _typename(ftype)
                src = "inherited" if fname in inherited_names else "direct"
                if flt and not any(flt in s for s in (clsname, fname, tstr)):
                    continue
                rows.append([clsname, fname, tstr, src])

        if not rows:
            print("(no extras)")
            return

        _print_table(rows, ["class", "field", "type", "source"])

    def _cmd_type(self, args: list[str]) -> None:
        """
        type                           → describe the current node's runtime type + schema (inferred)
        type <PATH|ATTR>               → describe that child/target
        type class <ClassName>         → describe a schema class directly

        Flags:
        --fields   : include the class' field table
        --mro      : show Python MRO
        -c/--class : force schema class by name (for current/target node)
        """
        show_fields = False
        show_mro = False
        forced_class: str | None = None
        pos: list[str] = []

        i = 0
        while i < len(args):
            a = args[i]
            if a == "--fields":
                show_fields = True
            elif a == "--mro":
                show_mro = True
            elif a in ("-c", "--class"):
                if i + 1 >= len(args):
                    print("missing class name for --class")
                    return
                forced_class = args[i + 1]
                i += 1
            else:
                pos.append(a)
            i += 1

        def _schema_class_exists(name: str) -> bool:
            return name in SCHEMA.field_type_table

        def _infer_schema_class_from_node(node) -> str | None:
            if node is not None:
                cname = type(node).__name__
                if _schema_class_exists(cname):
                    return cname
            item_t = getattr(node, "item_type", None)
            if item_t:
                cname = getattr(item_t, "__name__", None)
                if cname and _schema_class_exists(cname):
                    return cname
            if isinstance(node, (list, tuple)) and node:
                cname = type(node[0]).__name__
                if _schema_class_exists(cname):
                    return cname
            if getattr(self, "root", None) is not None:
                cname = type(self.root).__name__  # type: ignore[attr-defined]
                if _schema_class_exists(cname):
                    return cname
            return None

        def _summ_runtime(node) -> list[list[str]]:
            rows: list[list[str]] = []
            if node is None:
                rows.append(["runtime", "type", "NoneType"])
                return rows
            rtype = type(node)
            rows.append(["runtime", "type", f"{rtype.__module__}.{rtype.__name__}"])
            if isinstance(node, dict):
                rows.append(["runtime", "container", f"dict (len={len(node)})"])
            elif isinstance(node, (list, tuple, set)):
                rows.append(["runtime", "container", f"{rtype.__name__} (len={len(node)})"])
                if node:
                    rows.append(["runtime", "elem-type", type(next(iter(node))).__name__])
            if getattr(node, "item_type", None) is not None:
                it = node.item_type  # type: ignore[union-attr]
                rows.append(["runtime", "item_type", getattr(it, "__name__", str(it))])
                rows.append(["runtime", "size", str(len(node)) if hasattr(node, "__len__") else "?"])
            return rows

        if pos and pos[0] == "class":
            if len(pos) < 2:
                print("usage: type class <ClassName> [--fields] [--mro]")
                return
            clsname = pos[1]
            if not _schema_class_exists(clsname):
                print(f"unknown class: {clsname}")
                return
            print(f"=== type: class {clsname} ===")
            bases = SCHEMA._bases.get(clsname, [])
            subs = sorted(SCHEMA._subclasses.get(clsname, set()))
            print("bases     :", ", ".join(bases) if bases else "(none)")
            print("subclasses:", ", ".join(subs) if subs else "(none)")
            fields = SCHEMA.get_class_fields(clsname) or {}
            print(f"fields    : {len(fields)}")
            if show_fields and fields:
                rows = []
                direct_ex = SCHEMA.get_extras(clsname)
                inh_all = SCHEMA.get_all_extras(clsname)
                inh_names = set(inh_all.keys()) - set(direct_ex.keys())
                for fname, ftype in sorted(fields.items()):
                    src = (
                        "extra:direct"
                        if fname in direct_ex
                        else ("extra:inherited" if fname in inh_names else "")
                    )
                    rows.append([fname, _typename(ftype), src])
                _print_table(rows, ["field", "schema-type", "note"])
            return

        target = self.cur  # type: ignore[attr-defined]
        field_name = None
        parent_for_field = None

        if pos:
            if len(pos) == 1 and hasattr(self.cur, pos[0]):  # type: ignore[attr-defined]
                field_name = pos[0]
                parent_for_field = self.cur  # type: ignore[attr-defined]
                target = getattr(self.cur, field_name)  # type: ignore[attr-defined]
            else:
                try:
                    node, stack = resolve_path(self.root, self.cur, pos[0])  # type: ignore[attr-defined]
                except Exception as e:
                    print(f"! bad path: {e}")
                    return
                target = node
                if stack:
                    field_name = stack[-1]
                    try:
                        parent_for_field, _ = resolve_path(self.root, self.cur, "/".join(stack[:-1]))  # type: ignore[attr-defined]
                    except Exception:
                        parent_for_field = None

        print(f"=== type: {('field ' + field_name) if field_name else 'node'} ===")
        rows = _summ_runtime(target)

        if forced_class:
            if not _schema_class_exists(forced_class):
                print(f"unknown class: {forced_class}")
                return
            clsname = forced_class
            rows.append(["schema", "class (forced)", clsname])
        else:
            clsname = _infer_schema_class_from_node(target)
            rows.append(["schema", "class", clsname or "(none)"])

        if clsname:
            bases = SCHEMA._bases.get(clsname, [])
            subs = sorted(SCHEMA._subclasses.get(clsname, set()))
            rows.append(["schema", "bases", ", ".join(bases) if bases else "(none)"])
            rows.append(["schema", "subs", ", ".join(subs) if subs else "(none)"])

        if field_name and parent_for_field is not None:
            parent_cls = type(parent_for_field).__name__
            ftable = SCHEMA.get_class_fields(parent_cls) or {}
            sch_type = _typename(ftable.get(field_name, "(not in schema)"))
            run_type = type(target).__name__ if target is not None else "NoneType"
            rows.append(["field", "parent-class", parent_cls])
            rows.append(["field", "schema-type", sch_type])
            rows.append(["field", "runtime-type", run_type])
            if field_name in ftable:
                s_ok = (run_type == getattr(ftable[field_name], "__name__", run_type)) or (run_type == sch_type)
                rows.append(["field", "match", "ok" if s_ok else "MISMATCH"])

        _print_table(rows, ["scope", "key", "value"])

        if show_fields and clsname:
            fields = SCHEMA.get_class_fields(clsname) or {}
            if fields:
                print("\n--- fields ---")
                rows2 = []
                direct_ex = SCHEMA.get_extras(clsname)
                inh_all = SCHEMA.get_all_extras(clsname)
                inh_names = set(inh_all.keys()) - set(direct_ex.keys())
                for fname, ftype in sorted(fields.items()):
                    src = (
                        "extra:direct"
                        if fname in direct_ex
                        else ("extra:inherited" if fname in inh_names else "")
                    )
                    rows2.append([fname, _typename(ftype), src])
                _print_table(rows2, ["field", "schema-type", "note"])

        if show_mro and target is not None:
            try:
                mro_names = [c.__name__ for c in type(target).mro()]
                print("\n--- mro ---")
                print(" → ".join(mro_names))
            except Exception:
                pass
