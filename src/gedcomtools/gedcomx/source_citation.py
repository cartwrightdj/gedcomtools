"""
======================================================================
 Project: Gedcom-X
 File:    source_citation.py
 Author:  David J. Cartwright
 Purpose: 

 Created: 2025-07-25
 Updated:
   - 2025-09-09 added schema_class
 
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
from .schemas import extensible
from typing import Optional
"""
======================================================================
Logging
======================================================================
"""
#=====================================================================

@extensible()
class SourceCitation:
    identifier = 'http://gedcomx.org/v1/SourceCitation'
    version = 'http://gedcomx.org/conceptual-model/v1'
    
    def __init__(self, lang: Optional[str], value: str) -> None:
        self.lang = lang if lang else 'en'
        self.value = value
    
    # ...existing code...

    @classmethod
    def from_json(cls, data: dict, context = None):
        """
        Create a SourceCitation instance from a JSON-dict (already parsed).
        """
        object_data = {}
        if (lang := data.get('lang')) is not None:
            object_data['lang'] = lang
        if (value := data.get('value')) is not None:
            object_data['value'] = value
        return cls(**object_data)
    
    @property
    def to_dict(self):
        return {'lang':self.lang,
                'value': self.value}