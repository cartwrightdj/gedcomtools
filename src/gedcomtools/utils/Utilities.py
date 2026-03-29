"""
======================================================================
 Project: gedcomtools
 File:    utils/Utilities.py
 Author:  David J. Cartwright
 Purpose: Utility functions including dynamic enum combination helper

 Created: 2025-07-01
 Updated:

======================================================================
"""
from enum import Enum

def combine_enums(name: str, *enums, allow_aliases=False, prefix_on_conflict=False) -> Enum:
    """Combine enum-like classes into a single iterable mapping."""
    items: dict[str, object] = {}
    seen_values: set[object] = set()

    for E in enums:
        for m in E:
            key = m.name
            val = m.value

            name_conflict = key in items
            value_conflict = (val in seen_values) and not allow_aliases

            if name_conflict or value_conflict:
                if prefix_on_conflict:
                    key = f"{E.__name__}_{key}"
                    if key in items:
                        raise ValueError(f"duplicate even after prefix: {key}")
                else:
                    raise ValueError(f"conflict on name={m.name!r} or value={m.value!r}")

            items[key] = val
            seen_values.add(val)

    return Enum(name, items)

