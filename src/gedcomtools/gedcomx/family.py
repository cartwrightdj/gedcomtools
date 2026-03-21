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
"""
======================================================================
GEDCOM Module Types
======================================================================
"""
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

    def reset(self):
        """Reset all family members and the couple relationship for the next FAM record."""
        self.parent1: Optional[Person] = None
        self.parent2: Optional[Person] = None
        self.children: list[Person] = []
        self.couple: Relationship = Relationship(type=RelationshipType.Couple)
        self.couple_added: bool = False
        self.marr_fact = Fact(type=FactType.Marriage)
        self.marr_date:str = ''

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
        from .place_reference import PlaceReference, PlaceDescription
        existing_places = self.gedcomx.places.by_name(record.value)
        if existing_places:
            self.marr_fact.place = PlaceReference(original=record.value, description=existing_places[0])
        else:
            place_des = PlaceDescription(names=[TextValue(value=record.value)])
            self.gedcomx.add_place_description(place_des)
            self.marr_fact.place = PlaceReference(original=record.value, description=place_des)
            
    def set_husband(self, husband: Optional[Person]):
        """Assign the husband (person1) of the couple relationship and register it in the genealogy."""
        if husband is not None:
            if self.parent1 is not None: raise ValueError
            self.couple.person1 = husband
            self.couple.person1.add_fact(self.marr_fact)
            if not self.couple_added:
                self.gedcomx.add_relationship(self.couple)
                
                self.couple_added = True
            self.parent1 = husband
    
    def set_wife(self, wife: Optional[Person]):
        """Assign the wife (person2) of the couple relationship and register it in the genealogy."""
        if wife is not None:
            if self.parent2 is not None: raise ValueError
            self.couple.person2 = wife
            self.couple.person2.add_fact(self.marr_fact)
            if not self.couple_added:
                self.gedcomx.add_relationship(self.couple)
                
                self.couple_added = True
            self.parent2 = wife
    
    def add_child(self, child: Optional[Person]):
        """Create ParentChild relationships between the child and each known parent."""
        if child is not None:
            if self.parent1 is not None:
                p1child = Relationship(person1=self.parent1,person2=child,type=RelationshipType.ParentChild)
                self.gedcomx.add_relationship(p1child)
            if self.parent2 is not None:
                p2child = Relationship(person1=self.parent2,person2=child,type=RelationshipType.ParentChild)
                self.gedcomx.add_relationship(p2child)

            
