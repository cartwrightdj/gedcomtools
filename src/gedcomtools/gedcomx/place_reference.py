from __future__ import annotations
from typing import Optional, Union, TYPE_CHECKING
if TYPE_CHECKING:
    from .place_description import PlaceDescription

"""
======================================================================
 Project: Gedcom-X
 File:    PlaceReference.py
 Author:  David J. Cartwright
 Purpose: Python Object representation of GedcomX PlaceReference Type

 Created: 2025-08-25
 Updated:
   - 2025-08-31: _as_dict_ to only create entries in dict for fields that hold data
   - 2025-09-03: _from_json refactored
   - 2025-09-09: added schema_class
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
from .resource import Resource
from .schemas import extensible
from ..logging_hub import hub, logging
from .uri import URI
"""
======================================================================
Logging
======================================================================
"""
log = logging.getLogger("gedcomx")
serial_log = "gedcomx.serialization"
#=====================================================================

@extensible()
class PlaceReference:
    """defines a reference to a PlaceDescription.

    
    Attributes:
        original (Optional[str]): The unnormalized, user- or source-provided place text.
            Keep punctuation and ordering exactly as recorded in the source.
        description (Optional[Resource|PlaceDescription]): A :class:`gedcomx.PlaceDescription` Object or pointer to it. (URI/:class:`~Resource`)

    """
    identifier = 'http://gedcomx.org/v1/PlaceReference'
    version = 'http://gedcomx.org/conceptual-model/v1'
    
    def __init__(self,
                 original: Optional[str] = None,
                 description: Optional[Union[Resource,URI, PlaceDescription]] = None) -> None:
        self.original = original
        self.description = description # descriptionRef

    @property
    def _as_dict_(self):
        
        type_as_dict = {}
        if self.original:
            type_as_dict['original'] = self.original
        if self.description:
            type_as_dict['description'] = URI(target=self.description)._as_dict_ 
        return type_as_dict if type_as_dict != {} else None
        
    
    @classmethod
    def _from_json_(cls, data, context=None) -> "PlaceReference":
        if not isinstance(data, dict):
            raise TypeError(f"{cls.__name__}._from_json_ expected dict or str, got {type(data)}")

        place_reference_data = {}

        # Scalars
        if (orig := data.get("original")) is not None:
            place_reference_data["original"] = orig
        if (desc := data.get("description")) is not None:
            place_reference_data["description"] = URI._from_json_(desc, context)
        
        return cls(**place_reference_data)



