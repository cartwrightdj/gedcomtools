from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, List, Optional, Union

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
    Collection = "http://gedcomx.org/Collection"
    PhysicalArtifact = "http://gedcomx.org/PhysicalArtifact"
    DigitalArtifact = "http://gedcomx.org/DigitalArtifact"
    Record = "http://gedcomx.org/Record"
    Person = "http://gedcomx.org/Person"

    @property
    def description(self) -> str:
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

    id: str = Field(default_factory=make_uid)
    resourceType: Optional[ResourceType] = None
    citations: List[SourceCitation] = Field(default_factory=list)
    mediaType: Optional[str] = None
    about: Optional[URI] = None
    mediator: Optional[Union[Resource, Agent]] = None
    publisher: Optional[Union[Resource, Agent]] = None
    authors: List[Resource] = Field(default_factory=list)
    sources: List[SourceReference] = Field(default_factory=list)
    analysis: Optional[Any] = None          # Resource | Document
    componentOf: Optional[SourceReference] = None
    titles: List[TextValue] = Field(default_factory=list)
    notes: List[Note] = Field(default_factory=list)
    attribution: Optional[Attribution] = None
    rights: List[Resource] = Field(default_factory=list)
    coverage: List[Coverage] = Field(default_factory=list)
    descriptions: List[TextValue] = Field(default_factory=list)
    identifiers: IdentifierList = Field(default_factory=IdentifierList)
    created: Optional[Date] = None
    modified: Optional[Date] = None
    published: Optional[Date] = None
    repository: Optional[Union[Resource, Agent]] = None

    def model_post_init(self, __context: object) -> None:
        self._uri = URI(fragment=self.id)

    def add_description(self, description_to_add: TextValue) -> None:
        if description_to_add and isinstance(description_to_add, TextValue):
            for current in self.descriptions:
                if description_to_add == current:
                    return
            self.descriptions.append(description_to_add)

    def add_identifier(self, identifier_to_add: Identifier) -> None:
        if identifier_to_add and isinstance(identifier_to_add, Identifier):
            self.identifiers.append(identifier_to_add)

    def add_note(self, note_to_add: Note) -> None:
        if note_to_add is None or note_to_add.text is None or note_to_add.text == "":
            return
        if not isinstance(note_to_add, Note):
            return
        for existing in self.notes:
            if note_to_add == existing:
                return
        self.notes.append(note_to_add)

    def add_source_reference(self, source_to_add: SourceReference) -> None:
        if source_to_add and isinstance(source_to_add, SourceReference):
            for current in self.sources:
                if current == source_to_add:
                    return
            self.sources.append(source_to_add)

    def add_title(self, title_to_add: Union[TextValue, str]) -> None:
        if isinstance(title_to_add, str):
            title_to_add = TextValue(value=title_to_add)
        if title_to_add and isinstance(title_to_add, TextValue):
            for current in self.titles:
                if title_to_add == current:
                    return
            self.titles.append(title_to_add)
        else:
            raise ValueError(f"Cannot add title of type {type(title_to_add)}")
