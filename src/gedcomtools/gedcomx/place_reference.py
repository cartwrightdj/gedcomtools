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
