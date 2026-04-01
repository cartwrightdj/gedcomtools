# -*- coding: utf-8 -*-
"""
======================================================================
 Project: gedcomtools
 File:    gctool_dataops.py
 Purpose: merge/diff/repair/export helpers + commands
 Created: 2026-04-01 — split from gctool.py
======================================================================
"""

from __future__ import annotations

import csv as _csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from gedcomtools.glog import get_logger

log = get_logger(__name__)

from .gctool_output import _bold, _dim, _green, _kv, _red, _table, _yellow
from .gctool_load import _load


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
    except (AttributeError, TypeError):
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
        except (AttributeError, TypeError):
            pass

    try:
        children = el.get_child_elements()
    except (AttributeError, TypeError):
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
        except (AttributeError, TypeError) as exc:
            log.debug("get_root_child_elements failed in cmd_repair: {}", exc)
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
