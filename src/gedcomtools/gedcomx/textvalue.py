from typing import Any, Optional, Dict

"""
======================================================================
 Project: Gedcom-X
 File:    textvalue.py
 Author:  David J. Cartwright
 Purpose: 

 Created: 2025-08-25
 Updated:
   - 2025-09-03 _from_json_ refactor
   - 2025-09-04 added _str_ and _repr_ dunders
   - 2025-09-09: added schema_class
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
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
class TextValue:
    identifier = 'http://gedcomx.org/v1/TextValue'
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self, value: Optional[str] = None, lang: Optional[str] = None) -> None:
        self.lang = lang
        self.value = value
        

    
    def _append_to_value(self, value_to_append):
        if not isinstance(value_to_append, str):
            raise ValueError(f"Cannot append object of type {type(value_to_append)}.")
        if self.value is None: self.value = value_to_append
        else: self.value += ' ' + value_to_append
    
    def __str__(self):
        return f"{self.value} ({self.lang})"
    
    # --- identity & hashing -------------------------------------------------
    def _key(self) -> tuple[str, str]:
        # Normalize for equality/hash:
        # - treat missing lang as ""
        # - casefold lang to compare 'EN' == 'en'
        # - strip value to ignore surrounding whitespace
        return ((self.lang or "").casefold(), (self.value or "").strip())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TextValue):
            return NotImplemented
        return self._key() == other._key()

    
    
    # ...existing code...

    def __repr__(self) -> str:
        # Debug-friendly: unambiguous constructor-style representation
        cls = self.__class__.__name__
        return f"{cls}(value={self.value!r}, lang={self.lang!r})"
