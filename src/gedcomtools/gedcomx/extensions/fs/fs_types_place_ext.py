"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/extensions/fs/fs_types_place_ext.py
 Purpose: FamilySearch GedcomX place extension types.

 Types: PlaceAttribute, PlaceDescriptionInfo

 Specification:
   https://github.com/FamilySearch/gedcomx-fs/blob/master/specifications/
   fs-gedcomx-extension-specification.md

 Created: 2026-03-21
======================================================================
"""
from __future__ import annotations

from typing import ClassVar, Optional

from gedcomtools.gedcomx.gx_base import GedcomXModel
from gedcomtools.glog import get_logger

log = get_logger(__name__)


class PlaceAttribute(GedcomXModel):
    """A typed attribute associated with a FamilySearch place description.

    Fields:
        attributeId:   The local identifier of this attribute.
        typeName:      Human-readable attribute type label.
        typeId:        Identifier of the attribute type.
        descriptionId: The place-description identifier this applies to.
        value:         The attribute value text.
        year:          A year associated with this attribute.
        locale:        BCP 47 locale of the value text.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/PlaceAttribute"

    attributeId: Optional[str] = None
    typeName: Optional[str] = None
    typeId: Optional[str] = None
    descriptionId: Optional[str] = None
    value: Optional[str] = None
    year: Optional[int] = None
    locale: Optional[str] = None


class PlaceDescriptionInfo(GedcomXModel):
    """FamilySearch-specific display metadata for a place description.

    Fields:
        zoomLevel:      The zoom level for map display.
        relatedType:    The type of related place.
        relatedSubType: The sub-type of related place.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/PlaceDescriptionInfo"

    zoomLevel: Optional[int] = None
    relatedType: Optional[str] = None
    relatedSubType: Optional[str] = None


log.debug(
    "fs_types_place_ext extension loaded — "
    "PlaceAttribute, PlaceDescriptionInfo defined"
)
