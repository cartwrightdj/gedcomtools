"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/extensions/fs/fs_types_link.py
 Purpose: FamilySearch GedcomX hypermedia link type.

 Types: Link

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


class Link(GedcomXModel):
    """A hypermedia link in the FamilySearch API (HAL-style).

    Fields:
        href:      The resolved href of the link.
        template:  The URI template for the link (RFC 6570).
        title:     A human-readable title.
        type:      The media type of the linked resource.
        accept:    The media type the server will accept for this link.
        allow:     HTTP methods allowed on the linked resource.
        hreflang:  BCP 47 language tag for the linked resource.
        count:     The number of items in the linked collection.
        offset:    The offset into the linked collection.
        results:   The total count of results in the linked collection.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/Link"

    href: Optional[str] = None
    template: Optional[str] = None
    title: Optional[str] = None
    type: Optional[str] = None
    accept: Optional[str] = None
    allow: Optional[str] = None
    hreflang: Optional[str] = None
    count: Optional[int] = None
    offset: Optional[int] = None
    results: Optional[int] = None


log.debug(
    "fs_types_link extension loaded — "
    "Link defined"
)
