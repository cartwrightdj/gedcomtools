from __future__ import annotations
import warnings

from enum import Enum
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
if TYPE_CHECKING:
    from .document import Document


"""
======================================================================
 Project: Gedcom-X
 File:    SourceDescription.py
 Author:  David J. Cartwright
 Purpose: 

 Created: 2025-07-25
 Updated:
   - 2025-08-31: _as_dict_ refactored to ignore empty fields, changed id creation to make_uid()
    - 2025-09-01: filename PEP8 standard, imports changed accordingly
    - 2025-09-09: added schema_class
 
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
from .agent import Agent
from .attribution import Attribution
from .coverage import Coverage
from .date import Date
from .identifier import Identifier, IdentifierList
from .identifier import make_uid
from ..logging_hub import hub, logging
from .note import Note
from .resource import Resource
from .schemas import extensible
from .source_citation import SourceCitation
from .source_reference import SourceReference
from .textvalue import TextValue
from .uri import URI
"""
======================================================================
Logging
======================================================================
"""
log = logging.getLogger("gedcomx")
serial_log = "gedcomx.serialization"
deserial_log = "gedcomx.deserialization"
#=====================================================================


class ResourceType(Enum):
    Collection = "http://gedcomx.org/Collection"
    PhysicalArtifact = "http://gedcomx.org/PhysicalArtifact"
    DigitalArtifact = "http://gedcomx.org/DigitalArtifact"
    Record = "http://gedcomx.org/Record"
    Person = "http://gedcomx.org/Person"    
    
    @property
    def description(self):
        descriptions = {
            ResourceType.Collection: "A collection of genealogical resources. A collection may contain physical artifacts (such as a collection of books in a library), records (such as the 1940 U.S. Census), or digital artifacts (such as an online genealogical application).",
            ResourceType.PhysicalArtifact: "A physical artifact, such as a book.",
            ResourceType.DigitalArtifact: "A digital artifact, such as a digital image of a birth certificate or other record.",
            ResourceType.Record: "A historical record, such as a census record or a vital record."
        }
        return descriptions.get(self, "No description available.")

@extensible(toplevel=True)    
class SourceDescription:
    """Description of a genealogical information source.

    See: http://gedcomx.org/v1/SourceDescription

    Args:
        id (str | None): Unique identifier for this `SourceDescription`.
        resourceType (ResourceType | None): Type/category of the resource being
            described (e.g., digital artifact, physical artifact).
        citations (list[SourceCitation] | None): Citations that reference or
            justify this source description.
        mediaType (str | None): IANA media (MIME) type of the resource
            (e.g., ``"application/pdf"``).
        about (URI | None): Canonical URI that the description is about.
        mediator (Resource | None): The mediator resource (if any) involved in
            providing access to the source.
        publisher (Resource | Agent | None): Publisher of the resource.
        authors (list[Resource] | None): Authors/creators of the resource.
        sources (list[SourceReference] | None): Other sources this description
            derives from or references.
        analysis (Resource | None): Analysis document associated with the
            resource (often a `Document`; kept generic to avoid circular imports).
        componentOf (SourceReference | None): Reference to a parent/containing
            source (this is a component/child of that source).
        titles (list[TextValue] | None): One or more titles for the resource.
        notes (list[Note] | None): Human-authored notes about the resource.
        attribution (Attribution | None): Attribution metadata for who supplied
            or curated this description.
        rights (list[Resource] | None): Rights statements or licenses.
        coverage (list[Coverage] | None): Spatial/temporal coverage of the
            source’s content.
        descriptions (list[TextValue] | None): Short textual summaries or
            descriptions.
        identifiers (IdentifierList | None): Alternative identifiers for the
            resource (DOI, ARK, call numbers, etc.).
        created (Date | None): Creation date of the resource.
        modified (Date | None): Last modified date of the resource.
        published (Date | None): Publication/release date of the resource.
        repository (Agent | None): Repository or agency that holds the resource.
        max_note_count (int): Maximum number of notes to retain/emit. Defaults to 20.

    Raises:
        ValueError: If `id` is not a valid UUID.

    Attributes:
        identifier (str): Gedcom-X specification identifier for this type.
    """

    identifier = "http://gedcomx.org/v1/SourceDescription"
    version = 'http://gedcomx.org/conceptual-model/v1'
    
    def __init__(self, id: Optional[str] = None,
                 resourceType: Optional[ResourceType] = None,
                 citations: Optional[List[SourceCitation]] = [],
                 mediaType: Optional[str] = None,
                 about: Optional[URI] = None,
                 mediator: Optional[Union[Resource,Agent]] = None,
                 publisher: Optional[Union[Resource,Agent]] = None,
                 authors: Optional[List[Resource]] = None,
                 sources: Optional[List[SourceReference]] = None,
                 analysis: Optional[Union[Resource,Document]] = None,  
                 componentOf: Optional[SourceReference] = None,
                 titles: Optional[List[TextValue]] = None,
                 notes: Optional[List[Note]] = None,
                 attribution: Optional[Attribution] = None,
                 rights: Optional[List[Resource]] = [],
                 coverage: Optional[List[Coverage]] = None,
                 descriptions: Optional[List[TextValue]] = None,
                 identifiers: Optional[IdentifierList] = None,
                 created: Optional[Date] = None,
                 modified: Optional[Date] = None,
                 published: Optional[Date] = None,
                 repository: Optional[Union[Resource,Agent]] = None,
                 ):
        
        
        self.id = id if id else make_uid()
        self.resourceType = resourceType
        self.citations = citations or []
        self.mediaType = mediaType
        self.about = about
        self.mediator = mediator
        self._publisher = publisher 
        self.authors = authors or []
        self.sources = sources or []
        self.analysis = analysis
        self.componentOf = componentOf
        self.titles = titles or []
        self.notes = notes or []
        self.attribution = attribution
        self.rights = rights or []
        self.coverage = coverage or []
        self.descriptions = descriptions or []
        self.identifiers = identifiers or IdentifierList()
        self.created = created
        self.modified = modified
        self.published = published
        self.repository = repository
  
        self._uri = URI(fragment=id) if id else None #TODO Should i take care of this in the collections?
 
    
    @property
    def publisher(self) -> Union[Resource, Agent, None]:
        return self._publisher
    
    @publisher.setter
    def publisher(self,
                  value: Union[Resource, Agent]):
        if value is None:
            self._publisher = None
        elif isinstance(value,Resource):
            self._publisher = value
        elif isinstance(value,Agent):
            self._publisher = value
        else:
            raise ValueError(f"'publisher' must be of type 'URI' or 'Agent', type: {type(value)} was provided")
    
    def add_description(self, desccription_to_add: TextValue):
        if desccription_to_add and isinstance(desccription_to_add,TextValue):
            for current_description in self.descriptions:
                if desccription_to_add == current_description:
                    return
            self.descriptions.append(desccription_to_add)

    def add_identifier(self, identifier_to_add: Identifier):
        if identifier_to_add and isinstance(identifier_to_add,Identifier):
            self.identifiers.append(identifier_to_add)
    
    def add_note(self,note_to_add: Note):
        if note_to_add is not None and note_to_add.text is not None and note_to_add.text != '':
            if note_to_add and isinstance(note_to_add,Note):
                for existing in self.notes:
                    if note_to_add == existing:
                        return False
                self.notes.append(note_to_add)
            return      
    
    def add_source_reference(self, source_to_add: SourceReference):
        if source_to_add and isinstance(object,SourceReference):
            for current_source in self.sources:
                if current_source == source_to_add:
                    return
            self.sources.append(source_to_add)

    def add_title(self, title_to_add: TextValue):
        if isinstance(title_to_add,str): title_to_add = TextValue(value=title_to_add)
        if title_to_add and isinstance(title_to_add, TextValue):
            for current_title in self.titles:
                if title_to_add == current_title:
                    return False
            self.titles.append(title_to_add)
        else:
            raise ValueError(f"Cannot add title of type {type(title_to_add)}")
            
    @property
    def to_dict(self) -> Dict[str, Any] | None:
        from .serialization import Serialization
        return Serialization.serialize(self)
        with hub.use(serial_log):
            log.debug(f"Serializing 'SourceDescription' with id: {self.id}")
            type_as_dict = {}

            if self.id:
                type_as_dict['id'] = self.id
            if self.about:
                type_as_dict['about'] = self.about.to_dict
            if self.resourceType:
                if isinstance(self.resourceType,str):
                    log.warning(f"'SourceDescription.resourceType' should not be a string {self.resourceType}")
                    type_as_dict['resourceType'] = self.resourceType
                else:
                    type_as_dict['resourceType'] = self.resourceType.value 
            if self.citations:
                type_as_dict['citations'] = [c.to_dict for c in self.citations if c]
            if self.mediaType:
                type_as_dict['mediaType'] = self.mediaType
            
            if self.mediator:
                type_as_dict['mediator'] = self.mediator.to_dict
            if self.publisher:
                type_as_dict['publisher'] = self.publisher.to_dict #TODO Resource this
            if self.authors:
                type_as_dict['authors'] = [a.to_dict for a in self.authors if a]
            if self.sources:
                type_as_dict['sources'] = [s.to_dict for s in self.sources if s]
            
            
            if self.analysis:
                type_as_dict['analysis'] = self.analysis.to_dict
            if self.componentOf:
                type_as_dict['componentOf'] = self.componentOf.to_dict 
            if self.titles:
                type_as_dict['titles'] = [t.to_dict for t in self.titles if t]
            if self.notes:
                type_as_dict['notes'] = [n.to_dict for n in self.notes if n]
            if self.attribution:
                type_as_dict['attribution'] = self.attribution.to_dict
            if self.rights:
                type_as_dict['rights'] = [r.to_dict for r in self.rights if r]
            
            if self.coverage:
                type_as_dict['coverage'] = [c.to_dict for c in self.coverage if c]
            
            if self.descriptions:
                if not (isinstance(self.descriptions, list) and all(isinstance(x, TextValue) for x in self.descriptions)):
                    assert False
                type_as_dict['descriptions'] = [d.to_dict for d in self.descriptions if d]
                
            if self.identifiers:
                type_as_dict['identifiers'] = self.identifiers.to_dict
            
            if self.created is not None:
                type_as_dict['created'] = self.created
            if self.modified is not None:
                type_as_dict['modified'] = self.modified
            if self.published is not None:
                type_as_dict['published'] = self.published
            
            if self.repository:
                type_as_dict['repository'] = self.repository.to_dict #TODO Resource this       

            log.debug(f"'SourceDescription' serialized with fields: '{type_as_dict.keys()}'") 
            if type_as_dict == {}: log.warning("serializing and empty 'SourceDescription'")
        return type_as_dict if type_as_dict != {} else None
                    
  