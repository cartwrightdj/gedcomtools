"""
Tests for gedcomtools.gedcomx.serialization — serialize / deserialize round-trips

Updates:
  2026-03-29 — added TestFromDictRootFields: round-trip tests for attribution
               and groups, which were silently dropped by from_dict() (bug #2)
             — added TestSerializeDictNullPruning: verifies None and empty-list
               values are pruned from dict serialization output (bug #4)
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
        result = gx._to_dict()
        # empty GedcomX serializes to None (no fields worth serializing)
        assert result is None or isinstance(result, dict)

    def test_gedcomx_with_person(self):
        gx = GedcomX()
        gx.add_person(Person(id="P1"))
        result = gx._to_dict()
        assert "persons" in result
        assert len(result["persons"]) == 1

    def test_gedcomx_persons_have_ids(self):
        gx = GedcomX()
        gx.add_person(Person(id="P1"))
        gx.add_person(Person(id="P2"))
        result = gx._to_dict()
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
        data = gx._to_dict()
        restored = Serialization.deserialize(data, GedcomX)
        assert isinstance(restored, GedcomX)
        assert len(restored.persons) == 1
        assert len(restored.agents) == 1


class TestFromDictRootFields:
    """Bug #2 regression: from_dict() was silently dropping attribution and groups."""

    def test_attribution_survives_round_trip(self):
        from gedcomtools.gedcomx.attribution import Attribution
        gx = GedcomX(id="G1")
        gx.attribution = Attribution(changeMessage="test export")
        data = gx._to_dict()
        assert "attribution" in data
        restored = GedcomX.from_dict(data)
        assert restored.attribution is not None
        assert restored.attribution.changeMessage == "test export"

    def test_groups_survive_round_trip(self):
        from gedcomtools.gedcomx.group import Group
        from gedcomtools.gedcomx.textvalue import TextValue as TV
        gx = GedcomX(id="G1")
        gx.groups.append(item=Group(id="GRP1", names=[TV(value="Test Group")]))
        data = gx._to_dict()
        assert "groups" in data
        restored = GedcomX.from_dict(data)
        assert len(restored.groups) == 1
        assert restored.groups.by_id("GRP1") is not None

    def test_id_and_description_still_restored(self):
        gx = GedcomX(id="G1", description="#SD1")
        data = gx._to_dict()
        restored = GedcomX.from_dict(data)
        assert restored.id == "G1"
        assert restored.description == "#SD1"


class TestSerializeDictNullPruning:
    """Bug #4 regression: serialize(dict) was emitting 'key': null for empty lists."""

    def test_empty_list_value_pruned(self):
        result = Serialization.serialize({"names": [], "id": "P1"})
        assert "names" not in result
        assert result["id"] == "P1"

    def test_none_value_pruned(self):
        result = Serialization.serialize({"a": None, "b": "keep"})
        assert "a" not in result
        assert result["b"] == "keep"

    def test_empty_dict_returns_none(self):
        assert Serialization.serialize({"a": None}) is None

    def test_nested_none_pruned(self):
        result = Serialization.serialize({"outer": {"inner": None, "keep": "yes"}})
        assert "inner" not in result["outer"]
        assert result["outer"]["keep"] == "yes"


