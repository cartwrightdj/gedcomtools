from typing import Optional

"""
======================================================================
 Project: Gedcom-X
 File:    Qualifier.py
 Author:  David J. Cartwright
 Purpose: Python Object representation of GedcomX Qualifier Type

 Created: 2025-08-25
 Updated:
   - 2025-08-31: _as_dict_ to only create entries in dict for fields that 
   hold data, updated _from_json
   - 2025-09-03: _from_json_ refactor
   
======================================================================
"""
from .schemas import extensible
"""
======================================================================
Logging
======================================================================
"""
#=====================================================================

@extensible()
class Qualifier:
    """defines the data structure used to supply additional details, annotations,
    tags, or other qualifying data to a specific data element.

    
    Attributes:
        name str: The name of the Qualifier. *It is RECOMMENDED that the qualifier 
            name resolve to an element of a constrained vocabulary.*
            
        value (Optional[str]): The value of the Qualifier. *If provided, the name 
            MAY give the semantic meaning of the value.*

    """
    #TODO Extensibile Enum?
    identifier = 'http://gedcomx.org/v1/Qualifier'
    version = 'http://gedcomx.org/conceptual-model/v1'
    
    def __init__(self, name: str, value: Optional[str]) -> None:
        self.name = name
        self.value = value
    
    def _append(self,value: str):
        if value and isinstance(value,str):
            if self.value is None:
                self.value = value
            else:
                self.value += ' ' + value.strip()
        else:
            raise ValueError('value must be a string')
    
    def __str__(self) -> str:
        return f"{self.name}: {self.value}"


