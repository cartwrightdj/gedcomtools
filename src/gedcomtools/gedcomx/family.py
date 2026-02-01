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
from enum import Enum
"""
======================================================================
GEDCOM Module Types
======================================================================
"""
from ..gedcom.elements import Element
from .gedcomx import GedcomX, Person, Relationship, RelationshipType
from .fact import Fact, FactType
from .note import Note
from .source_reference import SourceReference
from .textvalue import TextValue

class EvenFactTypes(Enum):
    Marriage = 0x01

class FamilyParser:
    def __init__(self,gx: GedcomX) -> None:
        self.gedcomx: GedcomX = gx
        self.parent1: Person = None
        self.parent2: Person = None
        self.children: list[Person] = []
        self.last_event_fact = None
        self.couple: Relationship = Relationship(type=RelationshipType.Couple)
        self.couple_added: bool = False
        self.marr_fact: Fact = None

    def reset(self):
        self.parent1: Person = None
        self.parent2: Person = None
        self.children: list[Person] = []
        self.couple: Relationship = Relationship(type=RelationshipType.Couple)
        self.couple_added: bool = False
        self.marr_fact = Fact(type=FactType.Marriage)
        self.marr_date:str = ''

    def marr(self):
        self.parent1.facts

    def add_source_reference(self, source_ref:SourceReference):
        self.marr_fact.add_source_reference(source_ref)
    
    def add_note(self, note: Note):
        self.marr_fact.add_note(note)

        
    def set_marr_date(self,record: Element):
        self.marr_date = record.value
    
    def set_marr_plac(self,record: Element):
        from .place_reference import PlaceReference, PlaceDescription
        if self.gedcomx.places.byName(record.value):
            self.marr_fact.place = PlaceReference(original=record.value, description=self.gedcomx.places.byName(record.value)[0])
        else:
            place_des = PlaceDescription(names=[TextValue(value=record.value)])
            self.gedcomx.add_place_description(place_des)
            self.marr_fact.place = PlaceReference(original=record.value, description=place_des)
            
    
    def set_husband(self, husband:Person):
        if husband is not None:
            if self.parent1 is not None: raise ValueError
            self.couple.person1 = husband
            self.couple.person1.add_fact(self.marr_fact)
            if not self.couple_added:
                self.gedcomx.add_relationship(self.couple)
                
                self.couple_added = True
            self.parent1 = husband
    
    def set_wife(self, wife:Person):
        if wife is not None:
            if self.parent2 is not None: raise ValueError
            self.couple.person2 = wife
            self.couple.person2.add_fact(self.marr_fact)
            if not self.couple_added:
                self.gedcomx.add_relationship(self.couple)
                
                self.couple_added = True
            self.parent2 = wife
            
