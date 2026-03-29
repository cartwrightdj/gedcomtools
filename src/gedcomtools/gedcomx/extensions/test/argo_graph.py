"""Compatibility wrapper for the legacy test extension graph helpers."""

from ..ae_arango.argo_graph import (
    ext_description_get,
    ext_description_set,
    ext_emb_narrative_get,
    ext_emb_narrative_set,
)

__all__ = [
    "ext_description_get",
    "ext_description_set",
    "ext_emb_narrative_get",
    "ext_emb_narrative_set",
]
