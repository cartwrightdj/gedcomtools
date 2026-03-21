"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/extensions/fs/additional_attribution.py
 Purpose: AdditionalAttribution FamilySearch GedcomX extension.

 Specification:
   https://github.com/FamilySearch/gedcomx-fs/blob/master/specifications/
   fs-gedcomx-extension-specification.md

 URI:     http://familysearch.org/v1/AdditionalAttribution
 Extends: Attribution

 Registers `additionalAttributions` as an extra list field on Conclusion
 so that any attributed GedcomX record can carry supplementary attribution
 entries (e.g. multiple editors from different systems).

 Created: 2026-03-21
======================================================================
"""
from __future__ import annotations

from typing import ClassVar, List, Optional

from gedcomtools.gedcomx.attribution import Attribution
from gedcomtools.gedcomx.schemas import SCHEMA
from gedcomtools.gedcomx.conclusion import Conclusion
from gedcomtools.glog import get_logger

log = get_logger(__name__)


class AdditionalAttribution(Attribution):
    """An additional attribution on an already-attributed GedcomX object.

    Extends :class:`~gedcomtools.gedcomx.attribution.Attribution` with an
    ``id`` field (from *ExtensibleData*) so that individual entries in the
    ``additionalAttributions`` list can be identified and referenced.

    All Attribution properties are inherited:
      - ``contributor``      — ResourceReference to the contributor.
      - ``modified``         — Modified timestamp.
      - ``changeMessage``    — Human-readable change message.
      - ``changeMessageResource`` — URI reference to the change message.
      - ``creator``          — ResourceReference to the original creator.
      - ``created``          — Created timestamp.

    Additional property (from ExtensibleData):
      - ``id``               — Local context-specific id for this entry.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/AdditionalAttribution"

    id: Optional[str] = None

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from gedcomtools.gedcomx.validation import check_nonempty
        if self.id is not None:
            check_nonempty(result, "id", self.id)

    def __str__(self) -> str:
        base = super().__str__().replace("Attribution(", "AdditionalAttribution(", 1)
        if self.id:
            # Prepend id= to the content
            inner_start = base.index("(") + 1
            id_part = f"id={self.id!r}, "
            return base[:inner_start] + id_part + base[inner_start:]
        return base

    def __repr__(self) -> str:
        return (
            f"AdditionalAttribution("
            f"id={self.id!r}, "
            f"contributor={self.contributor!r}, "
            f"modified={self.modified!r}, "
            f"changeMessage={self.changeMessage!r}, "
            f"changeMessageResource={self.changeMessageResource!r}, "
            f"creator={self.creator!r}, "
            f"created={self.created!r})"
        )


# ---------------------------------------------------------------------------
# Register additionalAttributions as an extra field on Conclusion.
#
# Any Conclusion subclass (Person, Relationship, Fact, …) will gain an
# `additionalAttributions` field that accepts a list of AdditionalAttribution
# objects.  Because SCHEMA.register_extra() now calls define_ext() for
# pydantic models, this becomes a proper typed model field.
# ---------------------------------------------------------------------------
SCHEMA.register_extra(Conclusion, "additionalAttributions", List[AdditionalAttribution])

log.debug(
    "AdditionalAttribution extension loaded — "
    "additionalAttributions registered on Conclusion"
)
