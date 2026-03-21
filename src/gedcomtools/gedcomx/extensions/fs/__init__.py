"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/extensions/fs/__init__.py
 Purpose: FamilySearch GedcomX extension package.

 Importing this package loads all FS extension submodules, registering
 extension fields and making all FS types available.

 Created: 2026-03-21
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
    fs_types_vocab,
)
