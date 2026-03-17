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
    
