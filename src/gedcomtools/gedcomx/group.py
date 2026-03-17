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
from .conclusion import Conclusion, ConfidenceLevel
from .document import Document
from .date import Date
from .evidence_reference import EvidenceReference
from .identifier import IdentifierList
from .note import Note
from .place_reference import PlaceReference
from .source_reference import SourceReference
from .resource import Resource
from .textvalue import TextValue
from .extensible_enum import ExtensibleEnum
from .schemas import extensible
from .subject import Subject
"""
======================================================================
Logging
======================================================================
"""
#=====================================================================

class GroupRoleType(ExtensibleEnum):
    pass


@extensible()
class GroupRole(Conclusion):
    identifier = 'http://gedcomx.org/v1/GroupRole'
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self,
                 id: Optional[str] = None,
                 lang: Optional[str] = None,
                 sources: Optional[List[SourceReference]] = None,
                 analysis: Optional[Resource] = None,
                 notes: Optional[List[Note]] = None,
                 confidence: Optional[ConfidenceLevel] = None,
                 attribution: Optional[Attribution] = None,
                 person: Optional[Resource] = None,
                 type: Optional[GroupRoleType] = None,
                 date: Optional[Date] = None,
                 details: Optional[str] = None) -> None:
        super().__init__(id, lang, sources, analysis, notes, confidence, attribution)
        self.person = person
        self.type = type
        self.date = date
        self.details = details


@extensible(toplevel=True)
class Group(Subject):
    identifier = 'http://gedcomx.org/v1/Group'
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self,
                 id: Optional[str] = None,
                 lang: Optional[str] = None,
                 sources: Optional[List[SourceReference]] = None,
                 analysis: Optional[Document | Resource] = None,
                 notes: Optional[List[Note]] = None,
                 confidence: Optional[ConfidenceLevel] = None,
                 attribution: Optional[Attribution] = None,
                 extracted: Optional[bool] = None,
                 evidence: Optional[List[EvidenceReference]] = None,
                 media: Optional[List[SourceReference]] = None,
                 identifiers: Optional[IdentifierList] = None,
                 names: Optional[List[TextValue]] = None,
                 date: Optional[Date] = None,
                 place: Optional[PlaceReference] = None,
                 roles: Optional[List[GroupRole]] = None) -> None:
        super().__init__(id, lang, sources, analysis, notes, confidence, attribution, extracted, evidence, media, identifiers)
        self.names = names if names else []
        self.date = date
        self.place = place
        self.roles = roles if roles else []