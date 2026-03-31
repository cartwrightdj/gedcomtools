#!/usr/bin/env python3
"""Interactive command-line shell for browsing, editing, and exporting GedcomX data.

This module is the public entry point.  The implementation has been split into:

  gxcli_output.py   — standalone helpers, constants, ANSI, settings
  gxcli_commands.py — _cmd_* mixin classes (_InfoMixin, _AhnenMixin, _NavMixin, _LoadMixin, _DataMixin)
  gxcli_schema.py   — _SchemaMixin (_cmd_schema, _cmd_extras, _cmd_type)
  gxcli_core.py     — Shell class (assembles all mixins) + prompt/run/tab-complete

Existing imports such as::

    from gedcomtools.gedcomx.gxcli import Shell, main

continue to work unchanged.
"""
from __future__ import annotations

# ======================================================================
#  Project: gedcomtools
#  File:    gxcli.py  (thin entry point)
#  Author:  David J. Cartwright
#  Purpose: cli to inspect GedcomX objects
#  Created: 2026-02-01
#  Updated: 2026-03-31 — split implementation into gxcli_output.py,
#                         gxcli_commands.py, gxcli_schema.py, gxcli_core.py;
#                         this file is now a thin re-exporting entry point;
#                         narrowed bare except Exception blocks
# ======================================================================

import argparse
import sys

# Re-export the public surface so that callers who do
#   from gedcomtools.gedcomx.gxcli import Shell, main
# continue to work identically.
from gedcomtools.gedcomx.gxcli_output import (  # noqa: F401
    ANSI,
    NO_DATA,
    JSON_LOAD,
    M_JSON_LD,
    XML_LOAD,
    CNVRT_GC5,
    SHELL_VERSION,
    init_logging,
    _level_from_str,
    _set_all_handler_levels,
    _sans_ansi,
    _pad_ansi,
    _clip,
    _human_type_name,
    _red,
    _json_loads,
    _json_dumps,
    _is_private,
    _coerce_token,
    _split_args_kwargs,
    _declaring_class,
    _format_signature,
    is_primitive,
    _maybe_as_dict,
    to_plain,
    short_preview,
    list_fields,
    type_of,
    as_indexable_list,
    _seg_to_key,
    _get_item_id,
    get_child,
    resolve_path,
    _typename,
    _print_table,
    _schema_fields_for_object,
    _parse_elem_from_type_str,
    _expected_element_type_from_parent,
    _names_match,
    smart_getattr,
    _SETTINGS_PATH,
    _HISTORY_PATH,
    _DEFAULT_SETTINGS,
    _load_settings,
    _save_settings,
    _grep_node,
)

from gedcomtools.gedcomx.gxcli_core import Shell  # noqa: F401


def main(argv: list[str] | None = None) -> int:
    """Run the command-line entry point."""
    init_logging(app_name="gedcomtools")
    parser = argparse.ArgumentParser(description="GEDCOM-X Inspector (schema-aware, cleaned)")
    parser.add_argument("path", nargs="?", help="optional file to load at start (.ged or .json)")
    args = parser.parse_args(argv)

    sh = Shell()
    if args.path:
        sh._cmd_load([args.path])
    sh.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
