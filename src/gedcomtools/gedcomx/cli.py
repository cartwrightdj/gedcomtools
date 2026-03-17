from typing import Any, Iterable, Sequence, get_origin
from .schemas import SCHEMA   # adjust as needed
from .serialization import Serialization
from pathlib import Path
import json


from gedcomtools.loggingkit import setup_logging, get_log 
log = get_log()

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

def write_jsonl(
    top_level_collection: Iterable,
    output_file: Path,
    overwrite: bool = False,
    append: bool = False,
) -> int:
    """
    Write an iterable of objects to a JSONL file.
    Returns the number of records written.

    Args:
        top_level_collection: Iterable of serializable objects.
        output_file: Path to the output .jsonl file.
        overwrite: If True, overwrite existing file. Mutually exclusive with append.
        append: If True, append to existing file. Mutually exclusive with overwrite.

    Raises:
        FileExistsError: if file exists and neither overwrite nor append is set.
        ValueError: if both overwrite and append are set.
    """
    log.debug("Starting jsonl write")
    if overwrite and append:
        raise ValueError("overwrite and append are mutually exclusive.")

    if output_file.exists():
        if overwrite:
            log.info("Overwriting existing file: %s", output_file.name)
        elif append:
            log.info("Appending to existing file: %s", output_file.name)
        else:
            raise FileExistsError(f"Output file already exists: {output_file}. Use overwrite=True or append=True.")
    else:
        output_file.parent.mkdir(parents=True, exist_ok=True)

    mode = "a" if append else "w"
    count = 0

    with output_file.open(mode, encoding="utf-8") as f:
        for item in top_level_collection:
            data = Serialization.serialize(item)
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
            count += 1

    log.info("Wrote %d records to %s", count, output_file.name)
    return count