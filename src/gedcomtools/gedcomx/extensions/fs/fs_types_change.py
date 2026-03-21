"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/extensions/fs/fs_types_change.py
 Purpose: FamilySearch GedcomX change-history extension types.

 Types: ChangeOperation, ChangeObjectType, ChangeObjectModifier, ChangeInfo

 Specification:
   https://github.com/FamilySearch/gedcomx-fs/blob/master/specifications/
   fs-gedcomx-extension-specification.md

 Created: 2026-03-21
======================================================================
"""
from __future__ import annotations

import enum
from typing import ClassVar, Optional

from gedcomtools.gedcomx.gx_base import GedcomXModel
from gedcomtools.gedcomx.resource import Resource
from gedcomtools.glog import get_logger

log = get_logger(__name__)


class ChangeOperation(str, enum.Enum):
    """URI constants representing change operations."""

    Create = "http://familysearch.org/v1/Create"
    Update = "http://familysearch.org/v1/Update"
    Delete = "http://familysearch.org/v1/Delete"
    Merge = "http://familysearch.org/v1/Merge"


class ChangeObjectType(str, enum.Enum):
    """URI constants representing the type of object that was changed."""

    Person = "http://gedcomx.org/Person"
    Relationship = "http://gedcomx.org/Relationship"
    SourceDescription = "http://gedcomx.org/SourceDescription"
    Name = "http://gedcomx.org/Name"
    Fact = "http://gedcomx.org/Fact"
    Gender = "http://gedcomx.org/Gender"


class ChangeObjectModifier(str, enum.Enum):
    """URI constants that further qualify the object type in a change entry."""

    Person = "http://gedcomx.org/Person"
    Couple = "http://gedcomx.org/Couple"
    ChildAndParentsRelationship = "http://familysearch.org/v1/ChildAndParentsRelationship"


class ChangeInfo(GedcomXModel):
    """Metadata about a single entry in a FamilySearch change history.

    Fields:
        operation:      The operation of the change (see ChangeOperation).
        objectType:     The type of the object (see ChangeObjectType).
        objectModifier: An optional modifier for the object (see ChangeObjectModifier).
        reason:         The reason for the change.
        parent:         The parent change that triggered this change.
        previous:       Subject representing previous values before change.
        resulting:      Subject representing result of the change.
        original:       Subject representing original values.
        removed:        Subject representing removed values.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/ChangeInfo"

    operation: Optional[str] = None
    objectType: Optional[str] = None
    objectModifier: Optional[str] = None
    reason: Optional[str] = None
    parent: Optional[Resource] = None
    previous: Optional[Resource] = None
    resulting: Optional[Resource] = None
    original: Optional[Resource] = None
    removed: Optional[Resource] = None


log.debug(
    "fs_types_change extension loaded — "
    "ChangeOperation, ChangeObjectType, ChangeObjectModifier, ChangeInfo defined"
)
