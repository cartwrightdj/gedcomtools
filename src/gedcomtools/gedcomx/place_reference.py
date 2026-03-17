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
from .uri import URI
"""
======================================================================
Logging
======================================================================
"""
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




