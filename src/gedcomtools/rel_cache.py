# -*- coding: utf-8 -*-
"""
======================================================================
 Project: gedcomtools
 File:    rel_cache.py
 Purpose: RelationshipCacheMixin — shared key-prefixed dict cache for
          get_parents / get_children_of / get_spouses in Gedcom5 and
          Gedcom7.

          Eliminates the duplicated cache check/store/clear pattern
          that previously lived in both facade classes.

 Created: 2026-04-01
======================================================================
"""
from __future__ import annotations


class RelationshipCacheMixin:
    """Mixin providing a keyed result cache for relationship traversal.

    Subclasses must call ``_cache_clear()`` whenever the underlying data
    is reloaded (e.g. in ``loadfile`` / ``parse_lines``).  The cache is
    **not** thread-safe; do not share a single instance across threads.

    Cache keys have the form ``"<prefix>:<XREF.upper()>"``, for example
    ``"p:@I1@"`` for the parents of ``@I1@``.
    """

    #: Populated by ``__init__`` in every concrete subclass.
    _rel_cache: dict[str, list]

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _cache_get(self, prefix: str, xref: str) -> list | None:
        """Return cached result or ``None`` if not yet computed."""
        return self._rel_cache.get(f"{prefix}:{xref.upper()}")

    def _cache_set(self, prefix: str, xref: str, result: list) -> None:
        """Store *result* in the cache."""
        self._rel_cache[f"{prefix}:{xref.upper()}"] = result

    def _cache_clear(self) -> None:
        """Discard all cached results (call on every data reload)."""
        self._rel_cache.clear()
