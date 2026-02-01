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
                 sources: Optional[List[SourceReference]] = [],
                 analysis: Optional[Resource] = None,
                 notes: Optional[List[Note]] = [],
                 confidence: Optional[ConfidenceLevel] = None,
                 attribution: Optional[Attribution] = None,
                 extracted: Optional[bool] = None,
                 evidence: Optional[List[EvidenceReference]] = [],
                 media: Optional[List[SourceReference]] = [],
                 identifiers: Optional[IdentifierList] = None,):
        super().__init__(id, lang, sources, analysis, notes, confidence, attribution)
        self.extracted = extracted
        self.evidence = evidence
        self.media = media
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
   
    @property
    def _as_dict_(self):
        with hub.use(serial_log):
            log.debug(f"Serializing 'Subject' with id: '{self.id}'")
            type_as_dict = super()._as_dict_  # Start with base class fields
            if type_as_dict is None: type_as_dict = {}
            if self.extracted:
                type_as_dict["extracted"] = self.extracted
            if self.evidence:
                type_as_dict["evidence"] = [evidence_ref for evidence_ref in self.evidence] if self.evidence else None
            if self.media:
                type_as_dict["media"] = [media for media in self.media] if self.media else None
            if self.identifiers:
                type_as_dict["identifiers"] = self.identifiers._as_dict_ if self.identifiers else None
            log.debug(f"'Subject' serialized with fields: '{type_as_dict.keys()}'") 
            if type_as_dict == {} or len(type_as_dict.keys()) == 0: log.warning("serializing and empty 'Subject' Object")
                           
        return type_as_dict if type_as_dict != {} else None
        
    
    @classmethod
    def _dict_from_json_(cls, data: dict, context = None) -> dict:
        subject_data = Conclusion._dict_from_json_(data,context)
        
        # Bool
        if (extracted := data.get("extracted")) is not None:
            # cast to bool in case JSON gives "true"/"false" as string
            if isinstance(extracted, str):
                subject_data["extracted"] = extracted.lower() == "true"
            else:
                subject_data["extracted"] = bool(extracted)

        # Lists
        if (evidence := data.get("evidence")) is not None:
            subject_data["evidence"] = [EvidenceReference._from_json_(e, context) for e in evidence]

        if (media := data.get("media")) is not None:
            subject_data["media"] = [SourceReference._from_json_(m, context) for m in media]

        # Identifiers
        if (identifiers := data.get("identifiers")) is not None:
            subject_data["identifiers"] = IdentifierList._from_json_(identifiers, context)

        # URI
        if (uri := data.get("uri")) is not None:
            subject_data["uri"] = URI(uri)

        #return cls(**conclusion)
        return subject_data
