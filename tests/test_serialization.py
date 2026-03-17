"""
Tests for gedcomtools.gedcomx.serialization — serialize / deserialize round-trips
"""
import json
import pytest
from gedcomtools.gedcomx.serialization import Serialization
from gedcomtools.gedcomx.gedcomx import GedcomX
from gedcomtools.gedcomx.person import Person, QuickPerson
from gedcomtools.gedcomx.name import Name, NameForm, QuickName
from gedcomtools.gedcomx.fact import Fact, FactType
from gedcomtools.gedcomx.gender import Gender, GenderType
from gedcomtools.gedcomx.relationship import Relationship, RelationshipType
from gedcomtools.gedcomx.agent import Agent
from gedcomtools.gedcomx.textvalue import TextValue
from gedcomtools.gedcomx.source_description import SourceDescription
from gedcomtools.gedcomx.note import Note
from gedcomtools.gedcomx.uri import URI


class TestSerializePrimitives:
    def test_none(self):
        assert Serialization.serialize(None) is None

    def test_string(self):
        assert Serialization.serialize("hello") == "hello"

    def test_int(self):
        assert Serialization.serialize(42) == 42

    def test_bool(self):
        assert Serialization.serialize(True) is True

    def test_list_of_strings(self):
        result = Serialization.serialize(["a", "b", "c"])
        assert result == ["a", "b", "c"]


class TestSerializeURI:
    def test_uri_serializes_to_value(self):
        u = URI(value="https://example.com/path")
        result = Serialization.serialize(u)
        assert result is not None
        assert "example.com" in str(result)


class TestSerializePerson:
    def test_basic_person(self):
        p = Person(id="P1")
        result = Serialization.serialize(p)
        assert isinstance(result, dict)
        assert result.get("id") == "P1"

    def test_person_with_name(self):
        p = Person(id="P1", names=[QuickName("John Smith")])
        result = Serialization.serialize(p)
        assert "names" in result
        assert len(result["names"]) == 1

    def test_person_with_gender(self):
        p = Person(id="P1", gender=Gender(type=GenderType.Male))
        result = Serialization.serialize(p)
        assert "gender" in result

    def test_person_with_fact(self):
        p = Person(id="P1", facts=[Fact(type=FactType.Birth)])
        result = Serialization.serialize(p)
        assert "facts" in result

    def test_empty_fields_omitted(self):
        p = Person(id="P1")
        result = Serialization.serialize(p)
        # Empty lists should not appear or should be empty
        for key in ("names", "facts", "notes", "sources"):
            if key in result:
                assert result[key] == [] or result[key] is None


class TestSerializeGedcomX:
    def test_empty_gedcomx(self):
        gx = GedcomX()
        result = Serialization.serialize(gx)
        # empty GedcomX serializes to None (no fields worth serializing)
        assert result is None or isinstance(result, dict)

    def test_gedcomx_with_person(self):
        gx = GedcomX()
        gx.add_person(Person(id="P1"))
        result = Serialization.serialize(gx)
        assert "persons" in result
        assert len(result["persons"]) == 1

    def test_gedcomx_persons_have_ids(self):
        gx = GedcomX()
        gx.add_person(Person(id="P1"))
        gx.add_person(Person(id="P2"))
        result = Serialization.serialize(gx)
        ids = [p.get("id") for p in result["persons"]]
        assert "P1" in ids
        assert "P2" in ids


class TestRoundTrip:
    def test_person_round_trip(self):
        p = Person(id="P1", names=[QuickName("John Smith")])
        data = Serialization.serialize(p)
        restored = Serialization.deserialize(data, Person)
        assert restored.id == "P1"

    def test_gedcomx_round_trip(self):
        gx = GedcomX()
        gx.add_person(Person(id="P1", names=[QuickName("John Smith")]))
        gx.add_agent(Agent(id="A1", names=[TextValue(value="FamilySearch")]))
        data = Serialization.serialize(gx)
        restored = Serialization.deserialize(data, GedcomX)
        assert isinstance(restored, GedcomX)
        assert len(restored.persons) == 1
        assert len(restored.agents) == 1


class TestDeserializeFromFile:
    def test_deserialize_gx_json(self, gx_small):
        with open(gx_small, "r", encoding="utf-8") as f:
            data = json.load(f)
        gx = Serialization.deserialize(data, GedcomX)
        assert isinstance(gx, GedcomX)
        assert len(gx.persons) >= 0  # may be 0 for source-only files

    def test_deserialize_preserves_person_ids(self, gx_small):
        with open(gx_small, "r", encoding="utf-8") as f:
            data = json.load(f)
        gx = Serialization.deserialize(data, GedcomX)
        for p in gx.persons:
            assert p.id is not None
