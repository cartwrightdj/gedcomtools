
"""
======================================================================
 Project: Gedcom-X
 File:    header.py
 Author:  David J. Cartwright
 Purpose: Object to hold the GedcomX Header Information

 Created: 2025-10-23
 Updated:
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
from .agent import Agent
from .identifier import Identifier
from .textvalue import TextValue

class Header():
    def __init__(self) -> None:
        self.submiter: Agent = None
        self.source: TextValue = None
        self.name: TextValue = None
        self.version: float | None = None

