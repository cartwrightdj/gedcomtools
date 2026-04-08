"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/extensions/fs/__init__.py
 Purpose: FamilySearch GedcomX extension package.

 Importing this package loads all FS extension submodules, registering
 extension fields and making all FS types available.

 Created: 2026-03-21
 Updated: 2026-04-08 — include FamilySearch RS/REST support types moved
                        from the legacy rs10 extension package
          2026-04-08 — re-export key FamilySearch deserialization types
                        including FamilySearchPersonEnvelope
======================================================================
"""
from . import (
    additional_attribution,
    fs_types_alternate,
    fs_types_artifact,
    fs_types_change,
    fs_types_core,
    fs_types_discussion,
    fs_types_group,
    fs_types_link,
    fs_types_merge,
    fs_types_node,
    fs_types_ordinance,
    fs_types_place_ext,
    fs_types_platform,
    fs_types_relationship,
    fs_types_rs,
    fs_types_vocab,
)

from .fs_types_core import FieldInfo, FsFieldInfo, PersonInfo
from .fs_types_node import NameFormInfo, NameFormOrder
from .fs_types_platform import FamilySearchPersonEnvelope, FamilySearchPlatform
from .fs_types_relationship import ChildAndParentsRelationship, FsRelationshipType, RelationshipType
from .fs_types_rs import DisplayProperties, FamilyView, RsLink, RsLinks

__all__ = [
    "ChildAndParentsRelationship",
    "DisplayProperties",
    "FamilySearchPersonEnvelope",
    "FamilySearchPlatform",
    "FamilyView",
    "FieldInfo",
    "FsFieldInfo",
    "FsRelationshipType",
    "NameFormInfo",
    "NameFormOrder",
    "PersonInfo",
    "RelationshipType",
    "RsLink",
    "RsLinks",
]
