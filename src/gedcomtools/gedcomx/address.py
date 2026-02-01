from typing import Any, Dict, Optional, List

"""
======================================================================
 Project: Gedcom-X
 File:    address.py
 Author:  David J. Cartwright
 Purpose: 

 Created: 2025-08-25
 Updated:
   - 2025-09-03: _from_json_ refactoring
   - 2025-09-09: added schema_class
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
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
class Address:
    """A GedcomX Address Data Type
    A GedcomX Address Data Type.

    Represents a postal address according to the GedcomX conceptual model.

    Args:
        value (str, optional): A complete address as a single string.
        city (str, optional): Name of the city or town.
        country (str, optional): Name of the country.
        postalCode (str, optional): Postal or ZIP code.
        stateOrProvince (str, optional): Name of the state, province, or region.
        street (str, optional): First street address line.
        street2 (str, optional): Second street address line.
        street3 (str, optional): Third street address line.
        street4 (str, optional): Fourth street address line.
        street5 (str, optional): Fifth street address line.
        street6 (str, optional): Sixth street address line.
    """

    identifier = "http://gedcomx.org/v1/Address"
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self, value: Optional[str] = None,
                 city: Optional[str] = None,
                 country: Optional[str] = None,
                 postalCode: Optional[str] = None,
                 stateOrProvince: Optional[str] = None,
                 street: Optional[str] = None,
                 street2: Optional[str] = None,
                 street3: Optional[str] = None,
                 street4: Optional[str] = None,
                 street5: Optional[str] = None,
                 street6: Optional[str] = None):
        
        self._value = value #TODO impliment a parser for date strings.
        self.city = city
        self.country = country
        self.postalCode = postalCode
        self.stateOrProvince = stateOrProvince
        self.street = street
        self.street2 = street2
        self.street3 = street3
        self.street4 = street4
        self.street5 = street5
        self.street6 = street6

    @property
    def value(self) -> str: 
        return ', '.join(filter(None, [
            self.street, self.street2, self.street3,
            self.street4, self.street5, self.street6,
            self.city, self.stateOrProvince,
            self.postalCode, self.country
        ]))
    
    @value.setter
    def value(self,value: str):
        self._value = value
        return
        raise NotImplementedError("Parsing of a full address is not implimented.")
    
    def _append(self,value):
        if self._value:
            self._value = self._value + ' ' + value
        else:
            self._value = value
             
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        
        return (
            self.value == other.value and
            self.city == other.city and
            self.country == other.country and
            self.postalCode == other.postalCode and
            self.stateOrProvince == other.stateOrProvince and
            self.street == other.street and
            self.street2 == other.street2 and
            self.street3 == other.street3 and
            self.street4 == other.street4 and
            self.street5 == other.street5 and
            self.street6 == other.street6
        )
    
    def __str__(self) -> str:
        # Combine non-empty address components into a formatted string
        parts = [
            self._value,
            self.street,
            self.street2,
            self.street3,
            self.street4,
            self.street5,
            self.street6,
            self.city,
            self.stateOrProvince,
            self.postalCode,
            self.country
        ]

        # Filter out any parts that are None or empty strings
        filtered_parts = [str(part) for part in parts if part]

        # Join the remaining parts with a comma and space
        return ', '.join(filtered_parts)
    
    
        
    
    