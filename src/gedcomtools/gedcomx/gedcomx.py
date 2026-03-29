"""Core GedcomX container types, collections, validation, and serialization entry points."""

from typing import Any, Dict, List, Optional, Union, Generic, TypeVar, Iterable

import orjson

# ======================================================================
#  Project: Gedcom-X
#  File:    GedcomX.py
#  Author:  David J. Cartwright
#  Purpose: Object for working with Gedcom-X Data
#  Created: 2025-07-25
#  Updated: 2026-03-24 — removed _serializer/_as_dict; json property now
#                         delegates to _to_dict() via Serialization.serialize
#           2026-03-29 — validate(): fixed cross-ref check to extract person id
#                         from Resource.resource.fragment (URI form), not only
#                         resourceId; fixes silent pass for dangling refs
#                       — from_dict(): now restores attribution and groups;
#                         previously both were silently dropped on deserialization
#                       — TypeCollection.append(): no longer stamps type path onto
#                         _uri; uses URI(fragment=id) only so resource refs serialize
#                         as #id (same-document); explicit path URIs are preserved
# ======================================================================
# GEDCOM Module Types
from .agent import Agent
from .attribution import Attribution
from .document import Document
from .event import Event
from .group import Group
from .identifier import make_uid
from ..glog import get_logger
from .person import Person
from .place_description import PlaceDescription
from .relationship import Relationship, RelationshipType  # re-exported: family.py imports from here  # pylint: disable=unused-import
from .resource import Resource
from .source_description import SourceDescription
from .textvalue import TextValue
from .uri import URI
from .validation import ValidationResult
#=====================================================================

log = get_logger(__name__)
serial_log = "gedcomx.serialization"
deserial_log = "gedcomx.serialization"



T = TypeVar("T")

class TypeCollection(Generic[T]):
    """
    A typed, indexable, iterable container with small indexes on id/name/uri.
    The class name stays 'Collection'; the element type is carried in `item_type`.
    """
    def __init__(self, item_type: type[T]):
        self.item_type: type[T] = item_type
        self._items: list[T] = []
        self._id_index: dict[Any, T] = {}
        self._name_index: dict[str, dict[int, T]] = {}  # object id → item
        self._uri_index: dict[str, T] = {}
        self._uri = URI(path=f"/{item_type.__name__}s/")

    # --- core container protocol ---
    def __iter__(self):
        """Iterate over items in insertion order."""
        return iter(self._items)

    def __len__(self) -> int:
        """Return the number of items in the collection."""
        return len(self._items)

    def __getitem__(self, index: Union[int, slice]) -> Union[T, List[T]]:
        """Return the item or slice of items at the given index."""
        return self._items[index]

    def __contains__(self, item: object) -> bool:
        """Return True if the item is present in the collection."""
        return item in self._items

    def __repr__(self) -> str:
        return f"Collection<{self.item_type.__name__}>({len(self)} items)"

    def __delitem__(self, index: Union[int, slice]) -> None:
        """
        Delete item(s) at the given index or slice, updating all secondary indexes.
        Supports negative indices and slices like a normal list.
        """
        if isinstance(index, slice):
            items_to_remove = self._items[index]
            del self._items[index]
            for item in items_to_remove:
                self._remove_from_indexes(item)
        else:
            item = self._items[index]
            del self._items[index]
            self._remove_from_indexes(item)

    def pop(self, index: int = -1) -> T:
        """
        Pop and return an item at the given index (default: last),
        updating all secondary indexes.
        """
        # Let list semantics raise IndexError if empty/out of range
        item = self._items.pop(index)
        self._remove_from_indexes(item)
        return item

    # --- indexing helpers ---
    def _update_indexes(self, item: T) -> None:
        if hasattr(item, "id") and getattr(item, "id") is not None:
            self._id_index[getattr(item, "id")] = item

        u = getattr(item, "uri", None)
        if u is not None and getattr(u, "value", None):
            self._uri_index[u.value] = item

        names = getattr(item, "names", None)
        if names:
            for nm in names:
                name_value = nm.value if isinstance(nm, TextValue) else getattr(nm, "value", None)
                if isinstance(name_value, str) and name_value:
                    self._name_index.setdefault(name_value, {})[id(item)] = item

    def _remove_from_indexes(self, item: T) -> None:
        if hasattr(item, "id"):
            self._id_index.pop(getattr(item, "id"), None)

        u = getattr(item, "uri", None)
        if u is not None and getattr(u, "value", None):
            self._uri_index.pop(u.value, None)

        names = getattr(item, "names", None)
        if names:
            for nm in names:
                name_value = nm.value if isinstance(nm, TextValue) else getattr(nm, "value", None)
                if isinstance(name_value, str):
                    d = self._name_index.get(name_value)
                    if d:
                        d.pop(id(item), None)
                        if not d:
                            self._name_index.pop(name_value, None)

    # --- lookups ---
    def by_id(self, id_: Any) -> T | None:
        """Return the item with the given id, or None if not found."""
        return self._id_index.get(id_)

    def by_uri(self, uri: Union[URI, str]) -> T | None:
        """Return the item whose URI matches, or None if not found."""
        key = (uri.value or "") if isinstance(uri, URI) else str(uri)
        return self._uri_index.get(key) if key else None

    def by_name(self, sname: str | None) -> list[T] | None:
        """Return items whose name matches sname (stripped), or None if not found."""
        if not sname:
            return None
        d = self._name_index.get(sname.strip())
        return list(d.values()) if d else None

    # --- mutation ---
    def append(self, item: T) -> None:
        """Append an item to the collection and update all secondary indexes.

        Args:
            item: The item to add; must be an instance of ``item_type``.

        Raises:
            TypeError: If ``item`` is not an instance of ``item_type``.
        """
        if not isinstance(item, self.item_type):
            raise TypeError(f"Expected {self.item_type.__name__}, got {type(item).__name__} {item}")

        # ensure item has a _uri; only set it if absent — never overwrite an
        # explicitly assigned path-based URI (e.g. /persons/#P1 for zip layout)
        if getattr(item, "_uri", None) is None:
            setattr(item, "_uri", URI(fragment=getattr(item, "id", None)))

        self._items.append(item)
        self._update_indexes(item)

    def extend(self, items: Iterable[T]) -> None:
        """Append each item from an iterable to the collection."""
        for it in items:
            self.append(it)

    def remove(self, item: T) -> None:
        """Remove an item from the collection and update all secondary indexes.

        Raises:
            ValueError: If the item is not present in the collection.
        """
        if item not in self._items:
            raise ValueError("Item not found in the collection.")
        self._items.remove(item)
        self._remove_from_indexes(item)

    # --- convenience / serialization ---
    def __call__(self, **kwargs) -> list[T]:
        """Return a list of items whose attributes match all given keyword arguments."""
        out: list[T] = []
        for item in self._items:
            for k, v in kwargs.items():
                if not hasattr(item, k) or getattr(item, k) != v:
                    break
            else:
                out.append(item)
        return out



class GedcomX:
    """
    Main GedcomX Object representing a Genealogy. Stores collections of Top Level Gedcom-X Types.
    complies with GEDCOM X Conceptual Model V1 (http://gedcomx.org/conceptual-model/v1)

    Parameters
    ----------
    id : str
        Unique identifier for this Genealogy.
    attribution : Attribution Object
        Attribution information for the Genealogy
    filepath : str
        Not Implemented.
    description : str
        Description of the Genealogy: ex. 'My Family Tree'

    Raises
    ------
    ValueError
        If `id` is not a valid UUID.
    """
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self, id: Optional[str] = None,  # pylint: disable=redefined-builtin
                 attribution: Optional[Attribution] = None,
                 _filepath: Optional[str] = None,
                 description: Optional[str] = None,
                 persons: Optional[TypeCollection[Person]] = None,
                 relationships: Optional[TypeCollection[Relationship]] = None,
                 sourceDescriptions: Optional[TypeCollection[SourceDescription]] = None,
                 agents:  Optional[TypeCollection[Agent]] = None,
                 places: Optional[TypeCollection[PlaceDescription]] = None,
                 events: Optional[TypeCollection[Event]] = None,
                 documents: Optional[TypeCollection[Document]] = None) -> None:

        self.id = id
        self.attribution = attribution if attribution else None
        self._filepath = None

        self.description = description
        self.sourceDescriptions = TypeCollection(SourceDescription)
        if sourceDescriptions:
            self.sourceDescriptions.extend(sourceDescriptions)
        self.persons = TypeCollection(Person)
        if persons:
            self.persons.extend(persons)
        self.relationships = TypeCollection(Relationship)
        if relationships:
            self.relationships.extend(relationships)
        self.agents = TypeCollection(Agent)
        if agents:
            self.agents.extend(agents)
        self.events = TypeCollection(Event)
        if events:
            self.events.extend(events)
        self.documents = TypeCollection(Document)
        if documents:
            self.documents.extend(documents)
        self.places = TypeCollection(PlaceDescription)
        if places:
            self.places.extend(places)
        self.groups = TypeCollection(Group)

        self.__relationship_table = {}
        self._import_unhandled_tags = {}

        #self.default_id_generator = make_uid

    @property
    def contents(self):
        """Return a dict with item counts for each top-level collection."""
        return {
            "source_descriptions": len(self.sourceDescriptions),
            "persons": len(self.persons),
            "relationships": len(self.relationships),
            "agents": len(self.agents),
            "events": len(self.events),
            "documents": len(self.documents),
            "places": len(self.places),
            "groups": len(self.groups),
        }

    def add(self, gedcomx_type_object):
        """Dispatch a GedcomX top-level object to its appropriate ``add_*`` method.

        Args:
            gedcomx_type_object: A Document, Person, SourceDescription, Agent,
                PlaceDescription, Event, or Relationship instance.

        Raises:
            ValueError: If the object type is not a recognised top-level type.
        """
        if gedcomx_type_object:
            if isinstance(gedcomx_type_object,Document):
                self.add_document(gedcomx_type_object)
            elif isinstance(gedcomx_type_object,Person):
                self.add_person(gedcomx_type_object)
            elif isinstance(gedcomx_type_object,SourceDescription):
                self.add_source_description(gedcomx_type_object)
            elif isinstance(gedcomx_type_object,Agent):
                self.add_agent(gedcomx_type_object)
            elif isinstance(gedcomx_type_object,PlaceDescription):
                self.add_place_description(gedcomx_type_object)
            elif isinstance(gedcomx_type_object,Event):
                self.add_event(gedcomx_type_object)
            elif isinstance(gedcomx_type_object,Relationship):
                self.add_relationship(gedcomx_type_object)
            else:
                raise ValueError(f"I do not know how to add an Object of type {type(gedcomx_type_object)}")
        else:
            log.warning("Tried to add a None type to the GedcomX")

    def add_source_description(self, sourceDescription: SourceDescription):
        """Add a SourceDescription to the genealogy.

        Args:
            sourceDescription: The SourceDescription to add; must have an id.

        Raises:
            ValueError: If the argument is not a SourceDescription or has no id.
        """
        if sourceDescription and isinstance(sourceDescription,SourceDescription):
            if sourceDescription.id is None:
                raise ValueError("SourceDescription must have an id before being added")
            self.sourceDescriptions.append(item=sourceDescription)
        else:
            raise ValueError(f"When adding a SourceDescription, value must be of type SourceDescription, type {type(sourceDescription)} was provided")

    def add_document(self,document: Document):
        """Add a Document object to the Genealogy

        Args:
            document: Document Object

        Returns:
            None

        Raises:
            ValueError: If ``document`` is not of type Document.
        """
        if document and isinstance(document,Document):
            self.documents.append(item=document)
        else:
            raise ValueError(f"document must be a 'Document'' Object not type: {type(document)}")

    def add_person(self,person: Person):
        """Add a Person object to the Genealogy

        Args:
            person: Person Object

        Returns:
            None

        Raises:
            ValueError: If `person` is not of type Person.
        """
        if person and isinstance(person,Person):
            self.persons.append(item=person)
        else:
            raise ValueError(f'person must be a Person Object not type: {type(person)}')

    def add_relationship(self, relationship: Relationship):
        """Add a Relationship to the genealogy.

        Also registers any embedded Person objects and updates the internal
        relationship table so each person can quickly retrieve its relationships.

        Args:
            relationship: The Relationship to add.

        Raises:
            ValueError: If the argument is not a valid Relationship.
        """
        if relationship and isinstance(relationship,Relationship):
            if isinstance(relationship.person1,Resource) and isinstance(relationship.person2,Resource):
                self.relationships.append(relationship)
                return
            if isinstance(relationship.person1,Person) and isinstance(relationship.person2,Person):

                if relationship.person1:
                    if relationship.person1.id is None:
                        relationship.person1.id = make_uid()
                    if not self.persons.by_id(relationship.person1.id):
                        self.persons.append(relationship.person1)
                    if relationship.person1.id not in self.__relationship_table:
                        self.__relationship_table[relationship.person1.id] = []
                    self.__relationship_table[relationship.person1.id].append(relationship)
                    relationship.person1._add_relationship(relationship)
                else:
                    pass

                if relationship.person2:
                    if relationship.person2.id is None:
                        relationship.person2.id = make_uid()
                    if not self.persons.by_id(relationship.person2.id):
                        self.persons.append(relationship.person2)
                    if relationship.person2.id not in self.__relationship_table:
                        self.__relationship_table[relationship.person2.id] = []
                    self.__relationship_table[relationship.person2.id].append(relationship)
                    relationship.person2._add_relationship(relationship)
                else:
                    pass

                self.relationships.append(relationship)
            else:
                # person1/person2 may be dicts (e.g. after JSON round-trip) or
                # other valid types — store the relationship as-is.
                self.relationships.append(relationship)
        else:
            raise ValueError(
                f"relationship must be a Relationship instance, got {type(relationship).__name__}"
            )

    def add_place_description(self, placeDescription: PlaceDescription):
        """Add a PlaceDescription to the genealogy."""
        if placeDescription and isinstance(placeDescription,PlaceDescription):
            if placeDescription.id is None:
                log.warning("PlaceDescription has no id")
            self.places.append(placeDescription)

    def add_agent(self, agent: Agent):
        """Add an Agent to the genealogy, skipping duplicates by id.

        Args:
            agent: The Agent to add.

        Returns:
            False if an agent with this id already exists (duplicate skipped);
            None (implicit return) if the agent was successfully added.

        Raises:
            ValueError: If the argument is not an Agent.
        """
        if isinstance(agent,Agent) and agent is not None:
            if self.agents.by_id(agent.id) is not None:
                #log.debug("Skipped duplicate agent id={}", agent.id)
                return False
            self.agents.append(agent)
            #log.debug("Added agent id={}", agent.id)
            return None
        raise ValueError(
            f"agent must be an Agent instance, got {type(agent).__name__}"
        )

    def add_event(self, event_to_add: Event):
        """Add an Event to this GedcomX genealogy.

        Automatically assigns a uid if the event has no id.
        Duplicate events (by equality) are silently ignored.

        Args:
            event_to_add: The Event object to add.

        Raises:
            ValueError: If event_to_add is None or not an Event instance.
        """
        if event_to_add and isinstance(event_to_add, Event):
            if event_to_add.id is None:
                event_to_add.id = make_uid()
            for current_event in self.events:
                if event_to_add == current_event:
                    log.debug("Skipping duplicate event: {}", event_to_add.id)
                    return
            self.events.append(event_to_add)
        else:
            raise ValueError(f"event_to_add must be an Event instance, got {type(event_to_add).__name__}")

    def extend(self, gedcomx: 'GedcomX'):
        """Merge all top-level objects from another GedcomX instance into this one."""
        if gedcomx is not None:
            if self.id is None and gedcomx.id is not None:
                self.id = gedcomx.id
            if self.description is None and gedcomx.description is not None:
                self.description = gedcomx.description
            if self.attribution is None and gedcomx.attribution is not None:
                self.attribution = gedcomx.attribution
            for group in gedcomx.groups:
                if group.id is None or self.groups.by_id(group.id) is None:
                    self.groups.append(group)
            for person in gedcomx.persons:
                self.add_person(person)
            for agent in gedcomx.agents:
                self.add_agent(agent)
            for rel in gedcomx.relationships:
                self.add_relationship(rel)
            for sd in gedcomx.sourceDescriptions:
                self.add_source_description(sd)
            for event in gedcomx.events:
                self.add_event(event)
            for doc in gedcomx.documents:
                self.add_document(doc)
            for place in gedcomx.places:
                self.add_place_description(place)

    def get_person_by_id(self, obj_id: str):
        """Return the Person with the given id, or None if not found."""
        return self.persons.by_id(obj_id)

    def source_by_id(self, obj_id: str):
        """Return the SourceDescription with the given id, or None if not found."""
        return self.sourceDescriptions.by_id(obj_id)

    def validate(self) -> ValidationResult:
        """Validate this GedcomX document.

        Recursively validates every object in every collection, then performs
        cross-collection checks (e.g. relationship person references resolve).

        Returns:
            ValidationResult with accumulated errors and warnings.
        """
        result = ValidationResult()
        visited: set = set()
        collections = [
            ("persons", self.persons),
            ("relationships", self.relationships),
            ("agents", self.agents),
            ("sourceDescriptions", self.sourceDescriptions),
            ("places", self.places),
            ("events", self.events),
            ("documents", self.documents),
            ("groups", self.groups),
        ]
        for cname, coll in collections:
            for i, obj in enumerate(coll):
                result.merge(obj.validate(visited), prefix=f"{cname}[{i}]")

        # Cross-collection: relationship persons must exist
        person_ids = {p.id for p in self.persons}
        for i, rel in enumerate(self.relationships):
            for pnum, pfield in (("person1", rel.person1), ("person2", rel.person2)):
                if pfield is None:
                    continue
                if isinstance(pfield, Person):
                    ref_id = pfield.id
                elif isinstance(pfield, Resource):
                    ref_id = pfield.resourceId or (pfield.resource.fragment if pfield.resource else None)
                else:
                    ref_id = getattr(pfield, "id", None)
                if ref_id and ref_id not in person_ids:
                    result.error(
                        f"relationships[{i}].{pnum}",
                        f"Referenced person id {ref_id!r} not found in persons collection",
                    )

        return result

    @property
    def id_index(self) -> Dict[Any,Union[SourceDescription,Person,Relationship,Agent,Event,Document,PlaceDescription,Group]]:
        """Return a combined id→object mapping across all top-level collections."""
        combined = {**self.sourceDescriptions._id_index,
                    **self.persons._id_index,
                    **self.relationships._id_index,
                    **self.agents._id_index,
                    **self.events._id_index,
                    **self.documents._id_index,
                    **self.places._id_index,
                    **self.groups._id_index
        }
        #for i in combined.keys():
        #    combined[i] = str(type(combined[i]).__name__)
        return combined

    @classmethod
    def from_dict(cls, data: dict) -> "GedcomX":
        """Deserialize a GedcomX instance from a JSON-compatible dict."""
        gx = cls(
            id=data.get("id"),
            description=data.get("description"),
        )
        if ad := data.get("attribution"):
            try:
                gx.attribution = Attribution.model_validate(ad)
            except Exception as e:
                log.warning("Skipping invalid attribution: {}", e)
        for gd in data.get("groups", []):
            try:
                gx.groups.append(item=Group.model_validate(gd))
            except Exception as e:
                log.warning("Skipping invalid group record: {}", e)
        for pd in data.get("persons", []):
            try:
                gx.add_person(Person.model_validate(pd))
            except Exception as e:
                log.warning("Skipping invalid person record: {}", e)
        for ad in data.get("agents", []):
            try:
                gx.add_agent(Agent.model_validate(ad))
            except Exception as e:
                log.warning("Skipping invalid agent record: {}", e)
        from .relationship import Relationship  # pylint: disable=redefined-outer-name
        for rd in data.get("relationships", []):
            try:
                gx.add_relationship(Relationship.model_validate(rd))
            except Exception as e:
                log.warning("Skipping invalid relationship record: {}", e)
        for sd in data.get("sourceDescriptions", []):
            try:
                gx.add_source_description(SourceDescription.model_validate(sd))
            except Exception as e:
                log.warning("Skipping invalid sourceDescription record: {}", e)
        from .event import Event  # pylint: disable=redefined-outer-name
        for ed in data.get("events", []):
            try:
                gx.add_event(Event.model_validate(ed))
            except Exception as e:
                log.warning("Skipping invalid event record: {}", e)
        from .document import Document  # pylint: disable=redefined-outer-name
        for dd in data.get("documents", []):
            try:
                gx.add_document(Document.model_validate(dd))
            except Exception as e:
                log.warning("Skipping invalid document record: {}", e)
        from .place_description import PlaceDescription  # pylint: disable=redefined-outer-name
        for pld in data.get("places", []):
            try:
                gx.add_place_description(PlaceDescription.model_validate(pld))
            except Exception as e:
                log.warning("Skipping invalid place record: {}", e)
        return gx

    def _to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict via ``Serialization.serialize``.

        Resource references are emitted as ``{"resource": "#id"}`` pointers
        rather than inlined objects.
        """
        from .serialization import Serialization
        result: dict[str, Any] = {}
        if self.id:
            result["id"] = self.id
        if self.description:
            result["description"] = self.description
        if self.attribution:
            attr = Serialization.serialize(self.attribution)
            if attr:
                result["attribution"] = attr
        for name, col in (
            ("persons",            self.persons),
            ("relationships",      self.relationships),
            ("sourceDescriptions", self.sourceDescriptions),
            ("agents",             self.agents),
            ("events",             self.events),
            ("documents",          self.documents),
            ("places",             self.places),
            ("groups",             self.groups),
        ):
            if col:
                items = [s for item in col if (s := Serialization.serialize(item)) is not None]
                if items:
                    result[name] = items
        return result

    def gml(self) -> str:
        """Return the GedcomX graph as a GML string.

        Persons become nodes; Couple and ParentChild relationships become
        directed edges.  See :class:`~gedcomtools.gedcomx.gml.GedcomXGmlExporter`
        for the full attribute list.

        Returns:
            GML content as a :class:`str`.
        """
        from .gml import GedcomXGmlExporter
        return GedcomXGmlExporter().export(self)

    @property
    def json(self) -> bytes:
        """Return the GedcomX document as indented UTF-8 JSON bytes.

        Uses ``Serialization.serialize`` so resource references are emitted
        as ``{"resource": "#id"}`` pointers rather than inlined objects.
        """
        return orjson.dumps(self._to_dict(), option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE)

    def _resolve(self, resource_reference: Union[URI, Resource]):
        """Resolve a Resource or URI reference to the matching top-level object, or None."""
        #TODO indept URI search, URI index in collections
        if resource_reference:
            if isinstance(resource_reference, Resource):
                _res = resource_reference.resource
                ref_id = _res.fragment if _res else None
                ref = self.id_index.get(ref_id, None)
            elif isinstance(resource_reference, URI):
                ref_id = resource_reference.fragment
                ref = self.id_index.get(ref_id, None)
            else:
                raise TypeError()

            if ref is None:
                log.warning("Could not resolve id='{}' from {}", ref_id, type(resource_reference).__name__)
            else:
                log.debug("Resolved id='{}' to {}", ref_id, type(ref).__name__)
            return ref
        log.debug("_resolve: reference was None")
        return None
