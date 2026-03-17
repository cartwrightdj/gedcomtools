"""
Tests for gedcomtools.gedcomx.gedcomx.GedcomX — collections, lookups, merge
"""
import pytest
from gedcomtools.gedcomx.gedcomx import GedcomX
from gedcomtools.gedcomx.person import Person, QuickPerson
from gedcomtools.gedcomx.relationship import Relationship, RelationshipType
from gedcomtools.gedcomx.agent import Agent
from gedcomtools.gedcomx.textvalue import TextValue
from gedcomtools.gedcomx.source_description import SourceDescription
from gedcomtools.gedcomx.place_description import PlaceDescription
from gedcomtools.gedcomx.event import Event, EventType
from gedcomtools.gedcomx.note import Note


class TestGedcomXConstruction:
    def test_empty(self):
        gx = GedcomX()
        assert len(gx.persons) == 0
        assert len(gx.relationships) == 0
        assert len(gx.agents) == 0
        assert len(gx.sourceDescriptions) == 0

    def test_with_id(self):
        gx = GedcomX(id="test-gx")
        assert gx.id == "test-gx"


class TestGedcomXPersons:
    def test_add_person(self):
        gx = GedcomX()
        p = Person(id="P1")
        gx.add_person(p)
        assert len(gx.persons) == 1

    def test_get_person_by_id(self):
        gx = GedcomX()
        p = Person(id="P1")
        gx.add_person(p)
        assert gx.get_person_by_id("P1") is p

    def test_get_person_by_id_missing(self):
        gx = GedcomX()
        assert gx.get_person_by_id("MISSING") is None

    def test_multiple_persons(self):
        gx = GedcomX()
        for i in range(5):
            gx.add_person(Person(id=f"P{i}"))
        assert len(gx.persons) == 5
        assert gx.get_person_by_id("P3") is not None


class TestGedcomXRelationships:
    def test_add_relationship(self):
        gx = GedcomX()
        p1 = Person(id="P1")
        p2 = Person(id="P2")
        gx.add_person(p1)
        gx.add_person(p2)
        r = Relationship(person1=p1, person2=p2, type=RelationshipType.Couple)
        gx.add_relationship(r)
        assert len(gx.relationships) == 1

    def test_add_parent_child_relationship(self):
        gx = GedcomX()
        parent = Person(id="PAR1")
        child = Person(id="CHI1")
        gx.add_person(parent)
        gx.add_person(child)
        r = Relationship(person1=parent, person2=child, type=RelationshipType.ParentChild)
        gx.add_relationship(r)
        assert len(gx.relationships) == 1


class TestGedcomXAgents:
    def test_add_agent(self):
        gx = GedcomX()
        a = Agent(id="A1", names=[TextValue(value="FamilySearch")])
        gx.add_agent(a)
        assert len(gx.agents) == 1

    def test_agents_by_id(self):
        gx = GedcomX()
        a = Agent(id="A1")
        gx.add_agent(a)
        assert gx.agents.by_id("A1") is a

    def test_agents_by_name(self):
        gx = GedcomX()
        a = Agent(id="A1", names=[TextValue(value="FamilySearch")])
        gx.add_agent(a)
        results = gx.agents.by_name("FamilySearch")
        assert len(results) >= 1


class TestGedcomXSourceDescriptions:
    def test_add_source_description(self):
        gx = GedcomX()
        sd = SourceDescription(id="S1")
        gx.add_source_description(sd)
        assert len(gx.sourceDescriptions) == 1

    def test_source_by_id(self):
        gx = GedcomX()
        sd = SourceDescription(id="S1")
        gx.add_source_description(sd)
        assert gx.source_by_id("S1") is sd


class TestGedcomXPlaces:
    def test_add_place(self):
        gx = GedcomX()
        place = PlaceDescription(names=[TextValue(value="Springfield")])
        gx.add_place_description(place)
        assert len(gx.places) >= 1

    def test_place_by_name(self):
        gx = GedcomX()
        place = PlaceDescription(names=[TextValue(value="Springfield")])
        gx.add_place_description(place)
        results = gx.places.by_name("Springfield")
        assert results is not None


class TestGedcomXExtend:
    def test_extend_merges_persons(self):
        gx1 = GedcomX()
        gx1.add_person(Person(id="P1"))
        gx2 = GedcomX()
        gx2.add_person(Person(id="P2"))
        gx1.extend(gx2)
        assert gx1.get_person_by_id("P1") is not None
        assert gx1.get_person_by_id("P2") is not None

    def test_extend_merges_agents(self):
        gx1 = GedcomX()
        gx1.add_agent(Agent(id="A1"))
        gx2 = GedcomX()
        gx2.add_agent(Agent(id="A2"))
        gx1.extend(gx2)
        assert gx1.agents.by_id("A1") is not None
        assert gx1.agents.by_id("A2") is not None

    def test_extend_merges_relationships(self):
        gx1 = GedcomX()
        p1 = Person(id="P10")
        p2 = Person(id="P11")
        gx1.add_person(p1)
        gx1.add_person(p2)

        gx2 = GedcomX()
        p3 = Person(id="P12")
        p4 = Person(id="P13")
        gx2.add_person(p3)
        gx2.add_person(p4)
        r = Relationship(person1=p3, person2=p4, type=RelationshipType.Couple)
        gx2.add_relationship(r)

        gx1.extend(gx2)
        assert len(gx1.relationships) >= 1

    def test_extend_merges_source_descriptions(self):
        gx1 = GedcomX()
        gx1.add_source_description(SourceDescription(id="S1"))

        gx2 = GedcomX()
        gx2.add_source_description(SourceDescription(id="S2"))

        gx1.extend(gx2)
        assert gx1.source_by_id("S1") is not None
        assert gx1.source_by_id("S2") is not None

    def test_extend_merges_events(self):
        gx1 = GedcomX()
        gx2 = GedcomX()
        gx2.add_event(Event(id="E1", type=EventType.Birth))

        gx1.extend(gx2)
        assert gx1.events.by_id("E1") is not None

    def test_extend_merges_places(self):
        gx1 = GedcomX()
        gx2 = GedcomX()
        place = PlaceDescription(id="PL1", names=[TextValue(value="London")])
        gx2.add_place_description(place)

        gx1.extend(gx2)
        assert gx1.places.by_id("PL1") is not None

    def test_extend_with_none_is_no_op(self):
        gx = GedcomX()
        gx.add_person(Person(id="P99"))
        gx.extend(None)  # should not raise
        assert len(gx.persons) == 1


class TestGedcomXContents:
    def test_contents_dict(self):
        gx = GedcomX()
        gx.add_person(Person(id="P1"))
        gx.add_person(Person(id="P2"))
        c = gx.contents
        assert isinstance(c, dict)
        assert c.get("persons") == 2


class TestGedcomXPolymorphicAdd:
    def test_add_person(self):
        gx = GedcomX()
        gx.add(Person(id="P1"))
        assert len(gx.persons) == 1

    def test_add_agent(self):
        gx = GedcomX()
        gx.add(Agent(id="A1"))
        assert len(gx.agents) == 1

    def test_add_source_description(self):
        gx = GedcomX()
        gx.add(SourceDescription(id="S1"))
        assert len(gx.sourceDescriptions) == 1
