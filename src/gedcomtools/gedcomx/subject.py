import warnings
from typing import List, Optional 
"""
======================================================================
 Project: Gedcom-X
 File:    subject.py
 Author:  David J. Cartwright
 Purpose: 

 Created: 2025-08-25
 Updated:
   - 2025-09-03: _from_json_ refactor 
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
from .attribution import Attribution
from .conclusion import ConfidenceLevel, Conclusion
from .evidence_reference import EvidenceReference
from .identifier import Identifier, IdentifierList
from ..logging_hub import hub, logging
from .note import Note
from .resource import Resource
from .source_reference import SourceReference
from. uri import URI
"""
======================================================================
Logging
======================================================================
"""
log = logging.getLogger("gedcomx")
serial_log = "gedcomx.serialization"
#=====================================================================


class Subject(Conclusion):
    identifier = 'http://gedcomx.org/v1/Subject'
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self,
                 id: Optional[str],
                 lang: Optional[str] = 'en',
                 sources: Optional[List[SourceReference]] = None,
                 analysis: Optional[Resource] = None,
                 notes: Optional[List[Note]] = None,
                 confidence: Optional[ConfidenceLevel] = None,
                 attribution: Optional[Attribution] = None,
                 extracted: Optional[bool] = None,
                 evidence: Optional[List[EvidenceReference]] = None,
                 media: Optional[List[SourceReference]] = None,
                 identifiers: Optional[IdentifierList] = None,):
        super().__init__(id, lang, sources, analysis, notes, confidence, attribution)
        self.extracted = extracted
        self.evidence = evidence if evidence else []
        self.media = media if media else []
        self.identifiers = identifiers if identifiers else IdentifierList()
        
        
    '''
    def __setattr__(self, name, value):
        print(f"SET {name} = {value!r}")
        # example: simple validation/coercion
        if name == "identifiers" and value is not None:
            if isinstance(value, list):
                raise TypeError("Why is this being set as a list")
        object.__setattr__(self, name, value)
    '''
                  
        
    def add_identifier(self, identifier_to_add: Identifier):
        if identifier_to_add and isinstance(identifier_to_add,Identifier):
            if not self.identifiers.contains(identifier_to_add):
                self.identifiers.append(identifier_to_add)
            return
        raise ValueError()
   
