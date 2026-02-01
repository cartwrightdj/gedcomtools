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
from ..logging_hub import hub, logging
from .schemas import extensible
"""
======================================================================
Logging
======================================================================
"""
log = logging.getLogger("gedcomx")
serial_log = "gedcomx.serialization"
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
    def _as_dict_(self):
        from .serialization import Serialization
        type_as_dict = {}
        if self.spatial:
            type_as_dict['spatial'] = getattr(self.spatial, '_as_dict_', self.spatial)
        if self.temporal:  # (fixed: no space after the dot)
            type_as_dict['temporal'] = getattr(self.temporal, '_as_dict_', self.temporal)
        return Serialization.serialize_dict(type_as_dict) 

    @classmethod
    def _from_json_(cls, data: dict):
        """
        Create a Coverage instance from a JSON-dict (already parsed).
        """
        from .place_reference import PlaceReference
        from .date import Date

        spatial = PlaceReference._from_json_(data.get('spatial')) if data.get('spatial') else None
        temporal = Date._from_json_(data.get('temporal')) if data.get('temporal') else None
        return cls(spatial=spatial, temporal=temporal)