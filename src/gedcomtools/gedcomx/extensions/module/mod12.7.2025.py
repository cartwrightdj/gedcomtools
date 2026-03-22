from __future__ import annotations

# ======================================================================
#  Project: Gedcom-X
#  File:    mod12.7.2025.py
#  Author:  David J. Cartwright
#  Purpose: Link type of GedcomX RS 1.0 (Extension)
#  Created: 2025-08-25
# ======================================================================

# GEDCOM Module Types
from ....glog import get_logger
from ...schemas import SCHEMA
from ...document import Document
from ...textvalue import TextValue
# ======================================================================
# Logging
# ======================================================================
log = get_logger(__name__)
serial_log = "gedcomx.serialization"
deserial_log = "gedcomx.deserialization"
#=====================================================================

SCHEMA.register_extra(Document,'title',TextValue)
