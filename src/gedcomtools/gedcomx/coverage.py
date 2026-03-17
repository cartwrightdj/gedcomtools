from typing import Optional
"""
======================================================================
 Project: Gedcom-X
 File:    coverage.py
 Author:  David J. Cartwright
 Purpose: 

 Created: 2025-08-25
 Updated:
   - 2025-09-03: _from_json_ refactor 
   - 2025-09-09: added schema_class
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
from .date import Date
from .place_reference import PlaceReference
from .schemas import extensible
"""
======================================================================
Logging
======================================================================
"""
#=====================================================================

@extensible()
class Coverage:
    identifier = 'http://gedcomx.org/v1/Coverage'
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self,spatial: Optional[PlaceReference], temporal: Optional[Date]) -> None:
        self.spatial = spatial
        self.temporal = temporal    
    
    # ...existing code...