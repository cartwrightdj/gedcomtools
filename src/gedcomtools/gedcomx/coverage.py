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

    @property
    def to_dict(self):
        from .serialization import Serialization
        type_as_dict = {}
        if self.spatial:
            type_as_dict['spatial'] = getattr(self.spatial, 'to_dict', self.spatial)
        if self.temporal:  # (fixed: no space after the dot)
            type_as_dict['temporal'] = getattr(self.temporal, 'to_dict', self.temporal)
        return Serialization.serialize_dict(type_as_dict) 

    @classmethod
    def from_json(cls, data: dict):
        """
        Create a Coverage instance from a JSON-dict (already parsed).
        """
        from .place_reference import PlaceReference
        from .date import Date

        spatial = PlaceReference.from_json(data.get('spatial')) if data.get('spatial') else None
        temporal = Date.from_json(data.get('temporal')) if data.get('temporal') else None
        return cls(spatial=spatial, temporal=temporal)