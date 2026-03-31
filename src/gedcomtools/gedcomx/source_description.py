"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/source_description.py
 Author:  David J. Cartwright
 Purpose: GedcomX SourceDescription model: ResourceType enum and full source metadata

 Created: 2025-08-25
 Updated:
======================================================================
"""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, ClassVar, List, Optional, Union

from pydantic import Field, PrivateAttr

from .agent import Agent
from .attribution import Attribution
from .coverage import Coverage
from .date import Date
from .gx_base import GedcomXModel
from .identifier import Identifier, IdentifierList, make_uid
from .note import Note
from .resource import Resource
from .source_citation import SourceCitation
from .source_reference import SourceReference
from .textvalue import TextValue
from .uri import URI

if TYPE_CHECKING:
    from .document import Document


class ResourceType(Enum):
    """Enumeration of known GedcomX resource types for SourceDescription.resourceType."""

    Collection = "http://gedcomx.org/Collection"
    PhysicalArtifact = "http://gedcomx.org/PhysicalArtifact"
    DigitalArtifact = "http://gedcomx.org/DigitalArtifact"
    Record = "http://gedcomx.org/Record"
    Person = "http://gedcomx.org/Person"

    @property
    def description(self) -> str:
        """Return a human-readable description of this resource type."""
        descriptions = {
            ResourceType.Collection: "A collection of genealogical resources.",
            ResourceType.PhysicalArtifact: "A physical artifact, such as a book.",
            ResourceType.DigitalArtifact: "A digital artifact, such as a digital image.",
            ResourceType.Record: "A historical record.",
        }
        return descriptions.get(self, "No description available.")


class SourceDescription(GedcomXModel):
    """Description of a genealogical information source."""

    identifier: ClassVar[str] = "http://gedcomx.org/v1/SourceDescription"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    _uri: Optional[URI] = PrivateAttr(default=None)
    _place_holder: bool = PrivateAttr(default=False)

    id: str = Field(default_factory=make_uid)
    resourceType: Optional[ResourceType] = None
    citations: List[SourceCitation] = Field(default_factory=list)
    mediaType: Optional[str] = None
    about: Optional[URI] = None
    mediator: Optional[Union[Resource, Agent]] = None
    publisher: Optional[Union[Resource, Agent]] = None
    authors: List[Resource] = Field(default_factory=list)
    sources: List[SourceReference] = Field(default_factory=list)
    analysis: Optional[Union[Resource, "Document"]] = None
    componentOf: Optional[SourceReference] = None
    titles: List[TextValue] = Field(default_factory=list)
    notes: List[Note] = Field(default_factory=list)
    attribution: Optional[Attribution] = None
    rights: List[Resource] = Field(default_factory=list)
    coverage: List[Coverage] = Field(default_factory=list)
    descriptions: List[TextValue] = Field(default_factory=list)
    identifiers: IdentifierList = Field(default_factory=IdentifierList)
    created: Optional[Union[Date, str]] = None
    modified: Optional[Union[Date, str]] = None
    published: Optional[Union[Date, str]] = None
    repository: Optional[Union[Resource, Agent]] = None

    def model_post_init(self, __context: object) -> None:
        """Populate derived state after model initialization."""
        self._uri = URI(fragment=self.id)

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_instance, check_mime
        if self.resourceType is not None and not isinstance(self.resourceType, ResourceType):
            result.error("resourceType", f"Expected ResourceType, got {type(self.resourceType).__name__}: {self.resourceType!r}")
        if self.mediaType is not None:
            check_mime(result, "mediaType", self.mediaType)
        check_instance(result, "about", self.about, URI)
        for i, c in enumerate(self.citations):
            check_instance(result, f"citations[{i}]", c, SourceCitation)
        check_instance(result, "mediator", self.mediator, Resource, Agent)
        check_instance(result, "publisher", self.publisher, Resource, Agent)
        check_instance(result, "repository", self.repository, Resource, Agent)
        for i, a in enumerate(self.authors):
            check_instance(result, f"authors[{i}]", a, Resource)
        check_instance(result, "attribution", self.attribution, Attribution)
        if self.analysis is not None:
            check_instance(result, "analysis", self.analysis, Resource, Document)

    def add_description(self, description_to_add: TextValue) -> None:
        """Add a TextValue description, skipping duplicates."""
        if description_to_add and isinstance(description_to_add, TextValue):
            for current in self.descriptions:
                if description_to_add == current:
                    return
            self.descriptions.append(description_to_add)

    def add_identifier(self, identifier_to_add: Identifier) -> None:
        """Append an Identifier to this source description's identifier list."""
        if identifier_to_add and isinstance(identifier_to_add, Identifier):
            self.identifiers.append(identifier_to_add)

    def add_note(self, note_to_add: Note) -> None:
        """Add a non-empty Note to this source description, skipping blanks and duplicates."""
        if note_to_add is None or note_to_add.text is None or note_to_add.text == "":
            return
        if not isinstance(note_to_add, Note):
            return
        for existing in self.notes:
            if note_to_add == existing:
                return
        self.notes.append(note_to_add)

    def add_source_reference(self, source_to_add: SourceReference) -> None:
        """Add a SourceReference to this source description, skipping duplicates."""
        if source_to_add and isinstance(source_to_add, SourceReference):
            for current in self.sources:
                if current == source_to_add:
                    return
            self.sources.append(source_to_add)

    def add_title(self, title_to_add: Union[TextValue, str]) -> None:
        """Add a title (string or TextValue) to this source description, skipping duplicates."""
        if isinstance(title_to_add, str):
            title_to_add = TextValue(value=title_to_add)
        if title_to_add and isinstance(title_to_add, TextValue):
            for current in self.titles:
                if title_to_add == current:
                    return
            self.titles.append(title_to_add)
        else:
            raise ValueError(f"Cannot add title of type {type(title_to_add)}")

class ObjectParsingContainer:
    """Thin wrapper used during GEDCOM parsing to associate OBJE sub-records."""

    def __init__(self, source: SourceDescription) -> None:
        self.sourceDescription = source

    def add_title(self, title_to_add: Union[TextValue, str]) -> None:
        self.sourceDescription.add_title(title_to_add)

# SourceDescription's "Document" forward ref and SourceReference's "SourceDescription"
# forward ref are resolved from document.py after Document is fully defined.
