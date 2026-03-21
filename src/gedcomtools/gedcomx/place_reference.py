from __future__ import annotations
from typing import TYPE_CHECKING, Any, ClassVar, Optional, Union

from .gx_base import GedcomXModel
from .resource import Resource
from .uri import URI

if TYPE_CHECKING:
    from .place_description import PlaceDescription


class PlaceReference(GedcomXModel):
    """Reference to a PlaceDescription."""

    identifier: ClassVar[str] = "http://gedcomx.org/v1/PlaceReference"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    original: Optional[str] = None
    description: Optional[Any] = None   # Resource | URI | PlaceDescription

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_instance
        if self.original is None and self.description is None:
            result.warn("", "PlaceReference has neither original nor description")
        if self.description is not None:
            from .place_description import PlaceDescription
            check_instance(result, "description", self.description,
                           Resource, URI, PlaceDescription)
