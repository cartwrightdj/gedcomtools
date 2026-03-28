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
from .note import Note
from .source_reference import SourceReference
from .textvalue import TextValue

class FamilyParser:
    def __init__(self,gx: GedcomX) -> None:
        self.gedcomx: GedcomX = gx
        self.parent1: Optional[Person] = None
        self.parent2: Optional[Person] = None
        self.children: list[Person] = []
        self.last_event_fact = None
        self.couple: Relationship = Relationship(type=RelationshipType.Couple)
        self.couple_added: bool = False
        self.marr_fact: Fact = Fact(type=FactType.Marriage)
        self.marr_date: str = ''

    def reset(self):
        """Finalize the current family then reset for the next FAM record."""
        self.finalize()
        self.parent1 = None
        self.parent2 = None
        self.children = []
        self.couple = Relationship(type=RelationshipType.Couple)
        self.couple_added = False
        self.marr_fact = Fact(type=FactType.Marriage)
        self.marr_date = ''

    def add_source_reference(self, source_ref: SourceReference):
        """Add a SourceReference to the marriage fact."""
        self.marr_fact.add_source_reference(source_ref)

    def add_note(self, note: Note):
        """Add a Note to the marriage fact."""
        self.marr_fact.add_note(note)

    def set_marr_date(self, record: Element):
        """Set the marriage date from a GEDCOM DATE element."""
        self.marr_date = record.value

    def set_marr_plac(self, record: Element):
        """Set the marriage place from a GEDCOM PLAC element, creating a PlaceDescription if needed."""
        from .place_reference import PlaceReference
        from .place_description import PlaceDescription
        existing_places = self.gedcomx.places.by_name(record.value)
        if existing_places:
            self.marr_fact.place = PlaceReference(original=record.value, descriptionRef=existing_places[0])
        else:
            place_des = PlaceDescription(names=[TextValue(value=record.value)])
            self.gedcomx.add_place_description(place_des)
            self.marr_fact.place = PlaceReference(original=record.value, descriptionRef=place_des)

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
            self.couple.person1.add_fact(self.marr_fact)
            self.couple.person2.add_fact(self.marr_fact)
            self.gedcomx.add_relationship(self.couple)
            self.couple_added = True

    def add_child(self, child: Optional[Person]):
        """Create ParentChild relationships between the child and each known parent."""
        if child is not None:
            if self.parent1 is not None:
                p1child = Relationship(person1=self.parent1,person2=child,type=RelationshipType.ParentChild)
                self.gedcomx.add_relationship(p1child)
            if self.parent2 is not None:
                p2child = Relationship(person1=self.parent2,person2=child,type=RelationshipType.ParentChild)
                self.gedcomx.add_relationship(p2child)
