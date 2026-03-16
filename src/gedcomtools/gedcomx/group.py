from enum import Enum
from typing import List, Optional
"""
======================================================================
 Project: Gedcom-X
 File:    group.py
 Author:  David J. Cartwright
 Purpose: 

 Created: 2025-08-25
 Updated:
   - 2025-09-01: Updating basic structure, identify TODO s 
   - 2025-09-09: added schema_class
   - 2025-09-17: cahnged '.identifiers' to IdentifierList

   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
from .attribution import Attribution
from .conclusion import ConfidenceLevel
from .document import Document
from .date import Date
from .evidence_reference import EvidenceReference
from .identifier import IdentifierList
from .note import Note
from .place_reference import PlaceReference
from .source_reference import SourceReference
from .resource import Resource
from .textvalue import TextValue
from .schemas import extensible
from .subject import Subject
"""
======================================================================
Logging
======================================================================
"""
#=====================================================================

class GroupRoleType(Enum):                              #TODO Impliment
    def __init__(self) -> None:
        super().__init__()

class GroupRole:                                        #TODO Impliment
    identifier = 'http://gedcomx.org/v1/GroupRole'
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self, person: Resource,type: Optional[Enum], date: Optional[Date],details: Optional[str]) -> None:
        pass

@extensible(toplevel=True)
class Group(Subject):                                   #TODO Impliment
    identifier = 'http://gedcomx.org/v1/Group'
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self,
                 id: str | None, lang: str | None,
                 sources: List[SourceReference] | None,
                 analysis: Document | Resource | None,
                 notes: List[Note] | None,
                 confidence: ConfidenceLevel | None,
                 attribution: Attribution | None,
                 extracted: bool | None,
                 evidence: List[EvidenceReference] | None,
                 media: List[SourceReference] | None,
                 identifiers: Optional[IdentifierList] | None,
                 names: List[TextValue],
                 date: Optional[Date],
                 place: Optional[PlaceReference],
                 roles: Optional[List[GroupRole]]) -> None:
        super().__init__(id, lang, sources, analysis, notes, confidence, attribution, extracted, evidence, media, identifiers)
        self.names = names if names else []
        self.date = date
        self.place = place
        self.roles = roles if roles else []