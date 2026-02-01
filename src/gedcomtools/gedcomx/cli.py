from typing import Any, Iterable, Sequence, get_origin
from .schemas import SCHEMA   # adjust as needed


def _is_collection_type(tp: Any) -> bool:
    """
    Decide if a schema field type represents a collection (list/set/tuple).
    Works with both real types and string-encoded types from Schema.
    """
    if isinstance(tp, str):
        s = tp.strip()
        return s.startswith(("List[", "Set[", "Tuple[")) or s in ("List", "Set", "Tuple")

    origin = get_origin(tp)
    return origin in (list, set, tuple)


def _value_to_str(v: Any) -> str:
    """Best-effort stringifier for your GedcomX-style objects."""
    if v is None:
        return ""
    if hasattr(v, "value"):
        return str(v.value)
    if hasattr(v, "to_string"):
        return v.to_string()
    return str(v)


def _collection_to_str(seq: Iterable[Any]) -> str:
    return ", ".join(_value_to_str(x) for x in seq)


def objects_to_schema_table(
    objs: Sequence[Any],
    *,
    include: set[str] | None = None,
    exclude: set[str] | None = None,
    max_col_width: int | None = 60,
) -> str:
    """
    Build a text table for a homogeneous list of objects using SCHEMA
    to determine which fields exist and how to treat collections.

    - objs: sequence of objects of the same class
    - include: optional set of field names to include (default: all schema fields)
    - exclude: optional set of field names to skip
    - max_col_width: truncate cell contents if longer than this (per column)
    """
    if not objs:
        return "(no rows)"

    cls = objs[0].__class__
    type_name = cls.__name__

    fields = SCHEMA.get_class_fields(type_name) or {}
    if not fields:
        return f"(no schema registered for {type_name})"

    include = include or set(fields.keys())
    exclude = exclude or set()

    # Final ordered list of field names
    field_names = [f for f in sorted(fields.keys()) if f in include and f not in exclude]

    # Build raw rows
    table_rows: list[list[str]] = []

    for obj in objs:
        row: list[str] = []
        for fname in field_names:
            ftype = fields.get(fname)
            is_coll = _is_collection_type(ftype)

            val = getattr(obj, fname, None)
            if is_coll:
                if val is None:
                    text = ""
                else:
                    text = _collection_to_str(val)
            else:
                text = _value_to_str(val)

            # truncate if needed
            if max_col_width is not None and len(text) > max_col_width:
                text = text[: max_col_width - 1] + "…"

            row.append(text)
        table_rows.append(row)

    # Column headers
    headers = [name for name in field_names]

    # Compute column widths
    col_widths = []
    for col_idx in range(len(headers)):
        col_vals = [headers[col_idx]] + [r[col_idx] for r in table_rows]
        col_widths.append(max(len(str(v)) for v in col_vals))

    def fmt_row(vals: list[str]) -> str:
        return " | ".join(str(vals[i]).ljust(col_widths[i]) for i in range(len(vals)))

    # Build final table string
    lines: list[str] = []
    lines.append(fmt_row(headers))
    lines.append("-+-".join("-" * w for w in col_widths))
    for r in table_rows:
        lines.append(fmt_row(r))

    return "\n".join(lines)
