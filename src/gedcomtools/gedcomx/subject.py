from __future__ import annotations

from typing import List, Optional

from pydantic import Field

from .attribution import Attribution
from .conclusion import ConfidenceLevel, Conclusion
from .evidence_reference import EvidenceReference
from .identifier import Identifier, IdentifierList
from .note import Note
from .resource import Resource
from .source_reference import SourceReference
from .uri import URI
from ..glog import get_logger

log = get_logger(__name__)


class Subject(Conclusion):
    identifier = "http://gedcomx.org/v1/Subject"
    version = "http://gedcomx.org/conceptual-model/v1"

    extracted: Optional[bool] = None
    evidence: List[EvidenceReference] = Field(default_factory=list)
    media: List[SourceReference] = Field(default_factory=list)
    identifiers: IdentifierList = Field(default_factory=IdentifierList)

    def add_identifier(self, identifier_to_add: Identifier) -> None:
        if not isinstance(identifier_to_add, Identifier):
            raise ValueError("add_identifier requires an Identifier instance")
        if not self.identifiers.contains(identifier_to_add):
            self.identifiers.append(identifier_to_add)
