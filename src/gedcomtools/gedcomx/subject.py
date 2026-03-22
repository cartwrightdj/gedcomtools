from __future__ import annotations

from typing import List, Optional

from pydantic import Field

from .conclusion import Conclusion
from .evidence_reference import EvidenceReference
from .identifier import Identifier, IdentifierList
from .source_reference import SourceReference
from ..glog import get_logger

log = get_logger(__name__)


class Subject(Conclusion):
    identifier = "http://gedcomx.org/v1/Subject"
    version = "http://gedcomx.org/conceptual-model/v1"

    extracted: Optional[bool] = None
    evidence: List[EvidenceReference] = Field(default_factory=list)
    media: List[SourceReference] = Field(default_factory=list)
    identifiers: IdentifierList = Field(default_factory=IdentifierList)

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_instance
        # extracted must be bool if set
        if self.extracted is not None and not isinstance(self.extracted, bool):
            result.error("extracted", f"Expected bool, got {type(self.extracted).__name__}")
        # identifiers must be IdentifierList
        check_instance(result, "identifiers", self.identifiers, IdentifierList)
        # evidence items
        for i, ev in enumerate(self.evidence):
            check_instance(result, f"evidence[{i}]", ev, EvidenceReference)
        # media items
        for i, m in enumerate(self.media):
            check_instance(result, f"media[{i}]", m, SourceReference)

    def add_identifier(self, identifier_to_add: Identifier) -> None:
        if not isinstance(identifier_to_add, Identifier):
            raise ValueError("add_identifier requires an Identifier instance")
        if not self.identifiers.contains(identifier_to_add):
            self.identifiers.append(identifier_to_add)
