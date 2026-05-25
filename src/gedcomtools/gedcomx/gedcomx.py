"""Core GedcomX container types, collections, validation, and serialization entry points."""

from typing import Any, Dict, List, Optional, Union, Generic, TypeVar, Iterable

import orjson

# ======================================================================
#  Project: gedcomtools
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
#           2026-04-03 — added conversion_warnings property exposing
#                         _import_unhandled_tags for callers to detect data loss
#                       — TypeCollection.append(): rollback guard wraps
#                         _update_indexes so _items stays consistent on error
#           2026-04-06 — add_group() and GedcomX.add(Group(...)) support so
#                         Group is handled consistently with other top-level
#                         collections
#           2026-04-07 — added to_gedcom7() conversion helper (GedcomX → GEDCOM 7)
#           2026-04-12 — TypeCollection: fixed append() rollback to also call
#                         _remove_from_indexes so partial index writes don't leave
#                         zombie entries when _update_indexes raises mid-way
#                       — TypeCollection: added replace(old, new) for atomic item
#                         swap with transactional index restore on failure
#                       — TypeCollection: added reindex(item) for safe in-place
#                         mutation of id/uri/names; uses object-identity scan to
#                         remove stale entries before re-adding current values
#                       — TypeCollection: added _rebuild_indexes() for full O(n)
#                         recovery after out-of-band mutations
#           2026-04-15 — release refresh for v0.8.2b4 docs/build packaging
#                       — TypeCollection: added class-level docstring documenting
#                         the mutation contract and safe update patterns
#                       — TypeCollection: added change_id/change_uri/change_name
#                         for surgical index-safe property updates with collision
#                         detection; GedcomX wraps all three with auto-collection
#                         discovery via _find_collection()
#                       — enriched docstrings on all new TypeCollection and GedcomX
#                         mutation helpers; documents edge cases, examples, and
#                         what the methods do NOT do (cross-ref updates)
#           2026-04-12 — added _deser_skipped counter; from_dict() now records
#                         per-collection skip counts; conversion_warnings merges
#                         both GEDCOM tag losses and deserialization skip counts
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



T = TypeVar("T")

class TypeCollection(Generic[T]):
    """A typed, indexable, iterable container with small indexes on id/name/uri.

    The class name stays 'Collection'; the element type is carried in `item_type`.

    **Mutation contract**: the three indexed properties — ``id``, ``uri``, and
    ``names`` — must not be changed on an item that is already in the collection
    without calling :meth:`reindex` afterwards.  Direct in-place mutations (e.g.
    ``gx.persons[0].id = "new_id"``) silently stale the indexes, causing
    :meth:`by_id`, :meth:`by_uri`, and :meth:`by_name` to return wrong results.

    Safe patterns for updating indexed properties::

        # Swap the whole item (atomic, transactional)
        gx.persons.replace(old_person, new_person)

        # Mutate in place then reindex
        p = gx.persons.by_id("P1")
        p.id = "P1_NEW"
        gx.persons.reindex(p)

        # Full rebuild after bulk out-of-band mutations
        gx.persons._rebuild_indexes()
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

    def by_name(self, sname: str | None) -> list[T]:
        """Return items whose name matches sname (stripped), or [] if not found."""
        if not sname:
            return []
        d = self._name_index.get(sname.strip())
        return list(d.values()) if d else []

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
        try:
            self._update_indexes(item)
        except Exception:
            self._items.pop()
            self._remove_from_indexes(item)  # clean up any partial index writes
            raise

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

    def replace(self, old_item: T, new_item: T) -> None:
        """Atomically replace *old_item* with *new_item*, updating all indexes.

        The list position of the item is preserved.  If reindexing *new_item*
        fails the old item's indexes are restored and the exception is re-raised,
        leaving the collection unchanged.

        Args:
            old_item: Item currently in the collection.
            new_item: Replacement item; must be an instance of ``item_type``.

        Raises:
            ValueError: If *old_item* is not present.
            TypeError: If *new_item* is the wrong type.
        """
        if old_item not in self._items:
            raise ValueError("old_item not found in the collection.")
        if not isinstance(new_item, self.item_type):
            raise TypeError(
                f"Expected {self.item_type.__name__}, got {type(new_item).__name__}"
            )
        if getattr(new_item, "_uri", None) is None:
            setattr(new_item, "_uri", URI(fragment=getattr(new_item, "id", None)))

        idx = self._items.index(old_item)
        self._remove_from_indexes(old_item)
        try:
            self._update_indexes(new_item)
        except Exception:
            self._update_indexes(old_item)  # restore old indexes
            raise
        self._items[idx] = new_item

    def reindex(self, item: T) -> None:
        """Re-read *item*'s indexed properties and refresh all secondary indexes.

        Call this after mutating an item's ``id``, ``uri``, or ``names`` in
        place so that :meth:`by_id`, :meth:`by_uri`, and :meth:`by_name` return
        correct results.

        Uses object identity to locate and remove stale index entries, so it
        works correctly even when the indexed properties have already changed.

        Args:
            item: An item already present in the collection.

        Raises:
            ValueError: If *item* is not in the collection.
        """
        if item not in self._items:
            raise ValueError("Item not found in the collection.")
        # Remove stale entries by object identity, not by current property
        # values — those may already hold the post-mutation values.
        self._id_index = {k: v for k, v in self._id_index.items() if v is not item}
        self._uri_index = {k: v for k, v in self._uri_index.items() if v is not item}
        item_py_id = id(item)
        for d in self._name_index.values():
            d.pop(item_py_id, None)
        # Prune empty sub-dicts
        self._name_index = {k: d for k, d in self._name_index.items() if d}
        self._update_indexes(item)

    def change_id(self, item: T, new_id: Any) -> None:
        """Change *item*'s ``id`` and keep the id index consistent.

        This is the safe way to rename an item's identifier after it has been
        added to the collection.  Directly assigning ``item.id = new_id``
        would leave the old key in ``_id_index`` and the new key absent,
        causing :meth:`by_id` to return stale or wrong results.

        Only the id-index entry is touched; the uri and name indexes are not
        scanned.  If the item's ``_uri`` was auto-generated from its original
        id (i.e. ``_uri.fragment == old_id``), it is also updated to match the
        new id so ZIP document-reference URIs stay in sync.

        Assigning the same id the item already holds is a no-op (no error).

        This method does **not** update cross-references elsewhere in the
        document (e.g. ``Relationship.person1.resourceId``).  If those need
        updating, do so separately.

        ``item`` must already be present in the collection. ``new_id`` may be
        any hashable value; ``None`` clears the id and removes it from the
        index. Raises ``ValueError`` if the item is missing or the replacement
        id belongs to a different item.
        """
        if item not in self._items:
            raise ValueError("Item not found in the collection.")
        existing = self._id_index.get(new_id)
        if existing is not None and existing is not item:
            raise ValueError(
                f"Id {new_id!r} is already used by another item in this collection."
            )
        old_id = getattr(item, "id", None)
        if old_id is not None:
            self._id_index.pop(old_id, None)
        item.id = new_id
        if new_id is not None:
            self._id_index[new_id] = item
        # Keep the auto-generated document-fragment URI in sync with the new id.
        cur_uri = getattr(item, "_uri", None)
        if cur_uri is not None and getattr(cur_uri, "fragment", None) == old_id:
            item._uri = URI(fragment=new_id)

    def change_uri(self, item: T, new_uri: Union["URI", str, None]) -> None:
        """Change *item*'s ``uri`` and keep the uri index consistent.

        The safe counterpart to directly assigning ``item.uri = …`` on an
        item that is already in the collection.  Direct assignment would leave
        the old URI key in ``_uri_index`` and the new key absent.

        *new_uri* is accepted in three forms:

        * A :class:`~gedcomtools.gedcomx.uri.URI` instance — used as-is.
        * A plain ``str`` — wrapped in ``URI(value=new_uri)`` automatically.
        * ``None`` — clears ``item.uri`` and removes the old entry from the
          index.

        Only the uri-index entry is touched; id and name indexes are not
        scanned.

        ``item`` must already be present in the collection. Raises
        ``ValueError`` if the item is missing or the replacement URI string is
        already held by a different item.
        """
        if item not in self._items:
            raise ValueError("Item not found in the collection.")
        # Normalise to a string key and a URI object for assignment.
        if new_uri is None:
            new_key: Optional[str] = None
            new_uri_obj = None
        elif isinstance(new_uri, str):
            new_key = new_uri or None
            new_uri_obj = URI(value=new_uri) if new_uri else None
        else:
            new_key = getattr(new_uri, "value", None) or None
            new_uri_obj = new_uri
        if new_key is not None:
            existing = self._uri_index.get(new_key)
            if existing is not None and existing is not item:
                raise ValueError(
                    f"URI {new_key!r} is already used by another item in this collection."
                )
        old_u = getattr(item, "uri", None)
        old_key = getattr(old_u, "value", None) if old_u is not None else None
        if old_key:
            self._uri_index.pop(old_key, None)
        item.uri = new_uri_obj
        if new_key:
            self._uri_index[new_key] = item

    def change_name(self, item: T, old_name: str, new_name: str) -> None:
        """Replace one name value on *item* and keep the name index consistent.

        Finds the first entry in ``item.names`` whose ``.value`` equals
        *old_name*, updates it to *new_name*, and adjusts ``_name_index``
        accordingly — without touching the id or uri indexes.

        Unlike :meth:`change_id` and :meth:`change_uri`, no collision check
        is performed: multiple items in the same collection may legitimately
        share a display name (e.g. two agents both called "Smith & Co").
        :meth:`by_name` returns a *list* precisely to handle this case.

        Only the first matching name entry is replaced.  If an item has
        multiple names with the same value and you need to replace all of
        them, call this method once per occurrence.

        ``item`` must already be present in the collection. ``old_name`` is an
        exact match with no normalization. Passing an empty ``new_name``
        removes the old index entry without adding a replacement. Raises
        ``ValueError`` if the item is missing, has no names, or ``old_name``
        is not found.
        """
        if item not in self._items:
            raise ValueError("Item not found in the collection.")
        names = getattr(item, "names", None)
        if not names:
            raise ValueError("Item has no 'names' attribute.")
        item_py_id = id(item)
        for nm in names:
            nv = nm.value if isinstance(nm, TextValue) else getattr(nm, "value", None)
            if nv == old_name:
                # Remove old entry from the name index.
                d = self._name_index.get(old_name)
                if d:
                    d.pop(item_py_id, None)
                    if not d:
                        self._name_index.pop(old_name, None)
                nm.value = new_name
                if new_name:
                    self._name_index.setdefault(new_name, {})[item_py_id] = item
                return
        raise ValueError(f"Name {old_name!r} not found on item.")

    def _rebuild_indexes(self) -> None:
        """Rebuild all secondary indexes from scratch.

        Use this to recover from a known-corrupt index state or after
        bulk mutations that bypassed the normal :meth:`append`/:meth:`remove`
        path.  O(n) over the collection size.
        """
        self._id_index.clear()
        self._name_index.clear()
        self._uri_index.clear()
        for item in self._items:
            self._update_indexes(item)

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
        self._deser_skipped: Dict[str, int] = {}

        #self.default_id_generator = make_uid

    @property
    def conversion_warnings(self) -> Dict[str, int]:
        """Data-loss warnings accumulated during import or deserialization.

        Two sources contribute to this dict:

        * **GEDCOM converter** — tags encountered during GEDCOM 5/7 → GedcomX
          conversion that had no handler.  Keys are uppercase GEDCOM tag names
          (e.g. ``"OBJE"``, ``"CONC"``); values are occurrence counts.
        * **JSON deserialization** — records skipped by :meth:`from_dict`
          because ``model_validate`` raised.  Keys are lowercase collection
          names (e.g. ``"persons"``, ``"relationships"``); values are skip
          counts.

        Returns an empty dict when import was clean or this object was not
        produced by a converter or :meth:`from_dict`.
        """
        result = dict(self._import_unhandled_tags)
        result.update(self._deser_skipped)
        return result

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
                PlaceDescription, Event, Relationship, or Group instance.

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
            elif isinstance(gedcomx_type_object,Group):
                self.add_group(gedcomx_type_object)
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

    def add_group(self, group: Group):
        """Add a Group to the genealogy, skipping duplicates by id.

        Args:
            group: The Group to add.

        Returns:
            False if a group with this id already exists (duplicate skipped);
            None (implicit return) if the group was successfully added.

        Raises:
            ValueError: If the argument is not a Group.
        """
        if isinstance(group, Group) and group is not None:
            if group.id is not None and self.groups.by_id(group.id) is not None:
                return False
            self.groups.append(group)
            return None
        raise ValueError(
            f"group must be a Group instance, got {type(group).__name__}"
        )

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

    # ------------------------------------------------------------------
    # Safe id / uri / name mutation helpers
    # ------------------------------------------------------------------

    def _collections(self):
        """Yield every top-level :class:`TypeCollection` on this document.

        Used internally by :meth:`_find_collection` to locate an item without
        requiring the caller to know which collection it belongs to.

        Yields:
            Each of the eight top-level collections in a consistent order:
            persons, relationships, agents, events, documents, places,
            sourceDescriptions, groups.
        """
        yield from (
            self.persons, self.relationships, self.agents, self.events,
            self.documents, self.places, self.sourceDescriptions, self.groups,
        )

    def _find_collection(self, obj) -> Optional[TypeCollection]:
        """Return the :class:`TypeCollection` that owns *obj*, or ``None``.

        Searches all eight top-level collections by object identity (``is``),
        so the lookup is unaffected by stale or missing index entries.

        Args:
            obj: Any object to search for.

        Returns:
            The owning :class:`TypeCollection`, or ``None`` if *obj* is not
            a member of any collection on this document.
        """
        for coll in self._collections():
            if obj in coll:
                return coll
        return None

    def change_id(self, obj, new_id) -> None:
        """Change *obj*'s ``id`` and keep the owning collection's index consistent.

        Convenience wrapper around :meth:`TypeCollection.change_id` that
        locates the right collection automatically via
        :meth:`_find_collection`, so the caller does not need to know or
        remember which collection the object belongs to.

        The auto-generated ``_uri.fragment`` is updated to match the new id
        if it was derived from the original id (ZIP document-reference URIs
        stay in sync automatically).

        This method does **not** update cross-references elsewhere in the
        document (e.g. ``Relationship.person1.resourceId``).  Those must be
        updated separately if needed.

        ``obj`` must already be in one of the document's top-level
        collections. ``new_id`` may be ``None`` to clear the id. Raises
        ``ValueError`` if the object is not found or the replacement id belongs
        to a different item in the same collection.
        """
        coll = self._find_collection(obj)
        if coll is None:
            raise ValueError("Object not found in any top-level collection.")
        coll.change_id(obj, new_id)

    def change_uri(self, obj, new_uri) -> None:
        """Change *obj*'s ``uri`` and keep the owning collection's index consistent.

        Convenience wrapper around :meth:`TypeCollection.change_uri` that
        locates the right collection automatically.  Accepts the new URI as a
        :class:`~gedcomtools.gedcomx.uri.URI` object, a plain string, or
        ``None`` to clear.

        ``obj`` must already be in one of the document's top-level
        collections. ``new_uri`` may be a ``URI`` instance, a plain string, or
        ``None``. Raises ``ValueError`` if the object is not found or the
        replacement URI is already held by a different item in the same
        collection.
        """
        coll = self._find_collection(obj)
        if coll is None:
            raise ValueError("Object not found in any top-level collection.")
        coll.change_uri(obj, new_uri)

    def change_name(self, obj, old_name: str, new_name: str) -> None:
        """Replace one name value on *obj* and keep the owning collection's index consistent.

        Convenience wrapper around :meth:`TypeCollection.change_name` that
        locates the right collection automatically.  Replaces the first entry
        in ``obj.names`` whose value equals *old_name*.

        No collision check is performed — multiple items may legitimately
        share a display name.  See :meth:`TypeCollection.change_name` for
        full behaviour details.

        ``obj`` must already be in one of the document's top-level
        collections. Raises ``ValueError`` if the object is not found or
        ``old_name`` is not present among the object's names.
        """
        coll = self._find_collection(obj)
        if coll is None:
            raise ValueError("Object not found in any top-level collection.")
        coll.change_name(obj, old_name, new_name)

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
        def _skip(collection_key: str, exc: Exception) -> None:
            log.warning("Skipping invalid {} record: {}", collection_key, exc)
            gx._deser_skipped[collection_key] = gx._deser_skipped.get(collection_key, 0) + 1

        if ad := data.get("attribution"):
            try:
                gx.attribution = Attribution.model_validate(ad)
            except Exception as e:
                log.warning("Skipping invalid attribution: {}", e)
        for gd in data.get("groups", []):
            try:
                gx.groups.append(item=Group.model_validate(gd))
            except Exception as e:
                _skip("groups", e)
        for pd in data.get("persons", []):
            try:
                gx.add_person(Person.model_validate(pd))
            except Exception as e:
                _skip("persons", e)
        for ad in data.get("agents", []):
            try:
                gx.add_agent(Agent.model_validate(ad))
            except Exception as e:
                _skip("agents", e)
        from .relationship import Relationship  # pylint: disable=redefined-outer-name
        for rd in data.get("relationships", []):
            try:
                gx.add_relationship(Relationship.model_validate(rd))
            except Exception as e:
                _skip("relationships", e)
        for sd in data.get("sourceDescriptions", []):
            try:
                gx.add_source_description(SourceDescription.model_validate(sd))
            except Exception as e:
                _skip("sourceDescriptions", e)
        from .event import Event  # pylint: disable=redefined-outer-name
        for ed in data.get("events", []):
            try:
                gx.add_event(Event.model_validate(ed))
            except Exception as e:
                _skip("events", e)
        from .document import Document  # pylint: disable=redefined-outer-name
        for dd in data.get("documents", []):
            try:
                gx.add_document(Document.model_validate(dd))
            except Exception as e:
                _skip("documents", e)
        from .place_description import PlaceDescription  # pylint: disable=redefined-outer-name
        for pld in data.get("places", []):
            try:
                gx.add_place_description(PlaceDescription.model_validate(pld))
            except Exception as e:
                _skip("places", e)
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

    def to_gedcom7(self):
        """Convert this GedcomX document to a
        :class:`~gedcomtools.gedcom7.gedcom7.Gedcom7` object.

        Returns:
            A :class:`~gedcomtools.gedcom7.gedcom7.Gedcom7` instance whose
            :attr:`records` hold the converted GEDCOM 7 structure tree.

        Example::

            gx = GedcomX.from_dict(data)
            g7 = gx.to_gedcom7()
            g7.write("output.ged")
        """
        from ..gedcom7.gedcom7 import Gedcom7
        return Gedcom7.from_gedcomx(self)

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
