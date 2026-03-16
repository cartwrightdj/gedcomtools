from typing import Optional, TYPE_CHECKING
"""
======================================================================
 Project: Gedcom-X
 File:    evidence_reference.py
 Author:  David J. Cartwright
 Purpose: 

 Created: 2025-08-25
 Updated:
    - 2025-09-09: added schema_class
   
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Type Imports
======================================================================
"""
from .attribution import Attribution
from .resource import Resource
from .schemas import extensible
if TYPE_CHECKING:
    from .subject import Subject
"""
======================================================================
Logging
======================================================================
"""
#=====================================================================

@extensible()
class EvidenceReference:
    identifier = 'http://gedcomx.org/v1/EvidenceReference'
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self, resource: "Resource | Subject", attribution: Optional[Attribution]) -> None:
        self.resource = resource
        self.attribution: Attribution = attribution
    
    def _validate(self):
        raise NotImplemented