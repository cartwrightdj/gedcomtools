"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/extensions/fs/fs_types_alternate.py
 Purpose: FamilySearch GedcomX alternate date/place extension types.

 Types: AlternateDate, AlternatePlaceReference

 Specification:
   https://github.com/FamilySearch/gedcomx-fs/blob/master/specifications/
   fs-gedcomx-extension-specification.md

 Created: 2026-03-21
======================================================================
"""
from __future__ import annotations

from typing import ClassVar

from gedcomtools.gedcomx.date import Date
from gedcomtools.gedcomx.place_reference import PlaceReference
from gedcomtools.glog import get_logger

log = get_logger(__name__)


class AlternateDate(Date):
    """A FamilySearch alternate date conclusion.

    Extends :class:`~gedcomtools.gedcomx.date.Date` as a distinct type.
    Inherits all fields: ``original``, ``formal``, ``normalized``.

    The ``identifier`` class variable marks this as the FS-specific subtype.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/AlternateDate"


class AlternatePlaceReference(PlaceReference):
    """A FamilySearch alternate place reference.

    Extends :class:`~gedcomtools.gedcomx.place_reference.PlaceReference` as
    a distinct type.  Inherits all fields: ``original``, ``description``.

    The ``identifier`` class variable marks this as the FS-specific subtype.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/AlternatePlaceReference"


log.debug(
    "fs_types_alternate extension loaded — "
    "AlternateDate, AlternatePlaceReference defined"
)
