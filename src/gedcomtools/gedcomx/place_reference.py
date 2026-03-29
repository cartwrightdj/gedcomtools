"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/place_reference.py
 Author:  David J. Cartwright
 Purpose: GedcomX PlaceReference model: reference to a place with optional description

 Created: 2025-08-25
 Updated:
======================================================================
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Any, ClassVar, Optional

from pydantic import Field, field_validator

from .gx_base import GedcomXModel
from .resource import Resource
from .uri import URI

if TYPE_CHECKING:
    pass


class PlaceReference(GedcomXModel):
    """Reference to a PlaceDescription."""

    identifier: ClassVar[str] = "http://gedcomx.org/v1/PlaceReference"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    original: Optional[str] = None
    descriptionRef: Optional[Any] = Field(default=None, alias="description")  # Resource | URI | PlaceDescription

    @field_validator("descriptionRef", mode="before")
    @classmethod
    def _coerce_description(cls, v: Any) -> Any:
        if isinstance(v, dict):
            return Resource.model_validate(v)
        if isinstance(v, str):
            return URI(value=v)
        return v

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_instance
        if self.original is None and self.descriptionRef is None:
            result.warn("", "PlaceReference has neither original nor description")
        if self.descriptionRef is not None:
            from .place_description import PlaceDescription
            check_instance(result, "description", self.descriptionRef,
                           Resource, URI, PlaceDescription)
