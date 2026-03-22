
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

# GEDCOM Module Types
from typing import Optional
from .agent import Agent
from .textvalue import TextValue

class Header():
    def __init__(self) -> None:
        self.submiter: Optional[Agent] = None
        self.source: Optional[TextValue] = None
        self.name: Optional[TextValue] = None
        self.version: Optional[float] = None
