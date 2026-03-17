"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/extensions/fs/Identifier.py
 Author:  David J. Cartwright
 Purpose: FamilySearch-specific identifier type enum for Gedcom-X extensions

 Created: 2025-08-25
 Updated:

======================================================================
"""

from enum import Enum

class fsIdentifierType(Enum):
    ChildAndParentsRelationship = "http://familysearch.org/v1/ChildAndParentsRelationship"
