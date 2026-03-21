from __future__ import annotations
from typing import Any, Optional, List

from dataclasses import dataclass, field, fields, MISSING, make_dataclass

"""
======================================================================
 Project: Gedcom-X
 File:    rsLink.py
 Author:  David J. Cartwright
 Purpose: Link type of GedcomX RS 1.0 (Extension)
 https://github.com/FamilySearch/gedcomx-rs/blob/master/specifications/rs-specification.md

 Created: 2025-08-25
 Updated:
   - 
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
from ....glog import get_logger
from ...schemas import SCHEMA
from ...document import Document
from ...textvalue import TextValue
"""
======================================================================
Logging
======================================================================
"""
log = get_logger(__name__)
serial_log = "gedcomx.serialization"
deserial_log = "gedcomx.deserialization"
#=====================================================================

SCHEMA.register_extra(Document,'title',TextValue)
