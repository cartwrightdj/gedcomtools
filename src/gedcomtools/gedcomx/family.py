"""
======================================================================
 Project: Gedcom-X
 File:    family.py
 Author:  David J. Cartwright
 Purpose: parse FAM Elements, creating, relationships, fact, and events.

 Created: 2025-10-25
 Updated:

======================================================================
"""
# GEDCOM Module Types
from typing import Optional
from ..gedcom5.elements import Element
from .gedcomx import GedcomX, Person, Relationship, RelationshipType
from .fact import Fact, FactType
from .date import Date
from .note import Note
from .source_reference import SourceReference
from .textvalue import TextValue
from .event import Event

_PEDI_FACT_MAP: dict[str, FactType] = {
    "BIRTH": FactType.BiologicalParent,
    "ADOPTED": FactType.AdoptiveParent,
    "FOSTER": FactType.FosterParent,
}


class FamilyParser:
    """Stateful parser that accumulates FAM record fields and commits couple and parent-child relationships to a GedcomX object."""

    def __init__(self, gx: GedcomX, pedigree: Optional[dict[tuple[str, str], str]] = None) -> None:
        self.gedcomx: GedcomX = gx
        self.parent1: Optional[Person] = None
        self.parent2: Optional[Person] = None
        self.children: list[Person] = []
        self.last_event_fact = None
        self.family_xref: Optional[str] = None
        self.pedigree = pedigree if pedigree is not None else {}
        self.couple: Relationship = Relationship(type=RelationshipType.Couple)
        self.couple_added: bool = False
        self.marr_fact: Fact = Fact(type=FactType.Marriage)
        self.marr_date: str = ''
        self.anul_fact: Fact = Fact(type=FactType.Annulment)
        self.anul_date: str = ''
        self.anul_seen: bool = False
        self.family_facts: list[Fact] = []
        self.last_event_fact: Fact = self.marr_fact

    def reset(self, family_xref: Optional[str] = None):
        """Finalize the current family then reset for the next FAM record."""
        self.finalize()
        self.family_xref = family_xref
        self.parent1 = None
        self.parent2 = None
        self.children = []
        self.couple = Relationship(type=RelationshipType.Couple)
        self.couple_added = False
        self.marr_fact = Fact(type=FactType.Marriage)
        self.marr_date = ''
        self.anul_fact = Fact(type=FactType.Annulment)
        self.anul_date = ''
        self.anul_seen = False
        self.family_facts = []
        self.last_event_fact = self.marr_fact

    def marriage(self) -> Fact:
        """Mark the marriage fact as the active family event fact."""
        self.last_event_fact = self.marr_fact
        return self.marr_fact

    def anul_marriage(self) -> Fact:
        """Mark the annulment fact as the active family event fact."""
        self.anul_seen = True
        self.last_event_fact = self.anul_fact
        return self.anul_fact

    def family_fact(self, fact_type: FactType, value: Optional[str] = None) -> Fact:
        """Create and activate a typed family/couple fact."""
        fact = Fact(type=fact_type, value=value or None)
        self.family_facts.append(fact)
        self.last_event_fact = fact
        return fact

    def add_source_reference(self, source_ref: SourceReference):
        """Add a SourceReference to the active family event fact."""
        self.last_event_fact.add_source_reference(source_ref)

    def add_note(self, note: Note):
        """Add a Note to the active family event fact."""
        self.last_event_fact.add_note(note)

    def set_marr_date(self, record: Element):
        """Set the marriage date from a GEDCOM DATE element."""
        self.marr_date = record.value
        if record.value:
            self.marr_fact.date = Date(original=record.value)

    def set_event_date(self, record: Element):
        """Set the date on the active family event fact."""
        if self.last_event_fact is self.anul_fact:
            self.anul_date = record.value
        else:
            self.marr_date = record.value
        if record.value:
            self.last_event_fact.date = Date(original=record.value)

    def set_marr_plac(self, record: Element):
        """Set the marriage place from a GEDCOM PLAC element, creating a PlaceDescription if needed."""
        return self.set_event_plac(record)

    def set_event_plac(self, record: Element):
        """Set the place on the active family event fact, creating a PlaceDescription if needed."""
        from .place_reference import PlaceReference
        from .place_description import PlaceDescription
        existing_places = self.gedcomx.places.by_name(record.value)
        if existing_places:
            self.last_event_fact.place = PlaceReference(original=record.value, descriptionRef=existing_places[0])  # type: ignore[call-arg]
        else:
            place_des = PlaceDescription(names=[TextValue(value=record.value)])
            self.gedcomx.add_place_description(place_des)
            self.last_event_fact.place = PlaceReference(original=record.value, descriptionRef=place_des)  # type: ignore[call-arg]
        return self.last_event_fact.place

    def set_husband(self, husband: Optional[Person]):
        """Assign the husband (person1) of the couple relationship."""
        if husband is not None:
            if self.parent1 is not None:
                raise ValueError("set_husband called twice: person1 is already set on this couple relationship")
            self.couple.person1 = husband
            self.parent1 = husband

    def set_wife(self, wife: Optional[Person]):
        """Assign the wife (person2) of the couple relationship."""
        if wife is not None:
            if self.parent2 is not None:
                raise ValueError("set_wife called twice: person2 is already set on this couple relationship")
            self.couple.person2 = wife
            self.parent2 = wife

    def finalize(self) -> None:
        """Commit the couple relationship to the GedcomX graph.

        Only called when the FAM record is fully parsed.  A couple relationship
        requires both persons; if only one is present the family had no partner
        recorded and we skip the couple (parent-child relationships were already
        created directly in add_child).  Marriage facts are attached to persons
        only when the couple is complete.
        """
        if self.couple_added:
            return
        if self.couple.person1 is not None and self.couple.person2 is not None:
            self.couple.person1.add_fact(self.marr_fact)  # type: ignore[union-attr]
            self.couple.person2.add_fact(self.marr_fact)  # type: ignore[union-attr]
            if self.anul_seen:
                self.couple.person1.add_fact(self.anul_fact)  # type: ignore[union-attr]
                self.couple.person2.add_fact(self.anul_fact)  # type: ignore[union-attr]
            for fact in self.family_facts:
                self.couple.person1.add_fact(fact)  # type: ignore[union-attr]
                self.couple.person2.add_fact(fact.model_copy(deep=True))  # type: ignore[union-attr]
            self.gedcomx.add_relationship(self.couple)
            self.couple_added = True

    def add_child(self, child: Optional[Person]):
        """Create ParentChild relationships between the child and each known parent."""
        if child is not None:
            if self.parent1 is not None:
                p1child = Relationship(person1=self.parent1,person2=child,type=RelationshipType.ParentChild)
                self._apply_pedigree_fact(p1child, child)
                self.gedcomx.add_relationship(p1child)
            if self.parent2 is not None:
                p2child = Relationship(person1=self.parent2,person2=child,type=RelationshipType.ParentChild)
                self._apply_pedigree_fact(p2child, child)
                self.gedcomx.add_relationship(p2child)

    def _apply_pedigree_fact(self, relationship: Relationship, child: Person) -> None:
        """Attach a PEDI-derived relationship fact when one was recorded on FAMC."""
        if self.family_xref is None or child.id is None:
            return
        pedi = self.pedigree.get((self.family_xref, child.id))
        if not pedi:
            return
        fact_type = _PEDI_FACT_MAP.get(pedi)
        if fact_type is not None:
            relationship.add_fact(Fact(type=fact_type))
        elif pedi == "SEALING":
            relationship.add_note(Note(text="Pedigree: SEALING"))

    def add_event(self, event: Event):
        """Return the family event placeholder until full event wiring is implemented."""
        return event
        # TODO, create base event, as Persons are Added, add them to event
