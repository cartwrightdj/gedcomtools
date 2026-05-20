"""
Tests for gedcomtools.gedcomx.gedcomx.GedcomX — collections, lookups, merge

Updated: 2026-04-06 — add regression coverage for polymorphic
``GedcomX.add(Group(...))`` support.
Updated: 2026-04-12 — TypeCollection index-safety tests: replace(), reindex(),
_rebuild_indexes(), and append() partial-rollback correctness.
Updated: 2026-04-15 — release refresh for v0.8.0b3 docs/build packaging.
"""
import pytest
from gedcomtools.gedcomx.gedcomx import GedcomX, TypeCollection
from gedcomtools.gedcomx.person import Person, QuickPerson
from gedcomtools.gedcomx.relationship import Relationship, RelationshipType
from gedcomtools.gedcomx.agent import Agent
from gedcomtools.gedcomx.group import Group
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


class TestTypeCollectionIndexSafety:
    """Cover the index-consistency guarantees of TypeCollection."""

    def test_reindex_after_id_mutation(self) -> None:
        """by_id() reflects the new id after reindex()."""
        gx = GedcomX()
        p = Person(id="P1")
        gx.add_person(p)
        p.id = "P1_NEW"
        gx.persons.reindex(p)
        assert gx.persons.by_id("P1") is None
        assert gx.persons.by_id("P1_NEW") is p

    def test_reindex_after_name_mutation(self) -> None:
        """by_name() reflects the new name after reindex()."""
        gx = GedcomX()
        a = Agent(id="A1", names=[TextValue(value="Old Name")])
        gx.add_agent(a)
        a.names[0] = TextValue(value="New Name")
        gx.agents.reindex(a)
        assert gx.agents.by_name("Old Name") == []
        assert gx.agents.by_name("New Name") == [a]

    def test_reindex_item_not_in_collection_raises(self) -> None:
        gx = GedcomX()
        p = Person(id="P1")
        with pytest.raises(ValueError):
            gx.persons.reindex(p)

    def test_replace_swaps_item_and_indexes(self) -> None:
        """replace() swaps the item at the same position and updates indexes."""
        gx = GedcomX()
        p_old = Person(id="P1")
        p_new = Person(id="P2")
        gx.add_person(p_old)
        gx.persons.replace(p_old, p_new)
        assert len(gx.persons) == 1
        assert gx.persons[0] is p_new
        assert gx.persons.by_id("P1") is None
        assert gx.persons.by_id("P2") is p_new

    def test_replace_preserves_list_position(self) -> None:
        """replace() keeps the item at its original index."""
        gx = GedcomX()
        p0 = Person(id="P0")
        p1 = Person(id="P1")
        p2 = Person(id="P2")
        for p in (p0, p1, p2):
            gx.add_person(p)
        p1_new = Person(id="P1_NEW")
        gx.persons.replace(p1, p1_new)
        assert gx.persons[1] is p1_new

    def test_replace_old_not_in_collection_raises(self) -> None:
        gx = GedcomX()
        with pytest.raises(ValueError):
            gx.persons.replace(Person(id="GHOST"), Person(id="X"))

    def test_replace_wrong_type_raises(self) -> None:
        gx = GedcomX()
        p = Person(id="P1")
        gx.add_person(p)
        with pytest.raises(TypeError):
            gx.persons.replace(p, Agent(id="A1"))  # type: ignore[arg-type]

    def test_rebuild_indexes_repairs_stale_index(self) -> None:
        """_rebuild_indexes() heals indexes after out-of-band mutation."""
        gx = GedcomX()
        p = Person(id="P1")
        gx.add_person(p)
        p.id = "P1_DIRTY"          # mutate without reindex — stale state
        gx.persons._rebuild_indexes()
        assert gx.persons.by_id("P1") is None
        assert gx.persons.by_id("P1_DIRTY") is p

    def test_append_rollback_leaves_clean_indexes(self) -> None:
        """A failed append() leaves no zombie entries in the indexes."""
        coll: TypeCollection[Person] = TypeCollection(Person)
        p = Person(id="P1")

        # Patch _update_indexes to fail after writing the id index
        original = coll._update_indexes
        def partial_update(item):  # type: ignore[no-untyped-def]
            coll._id_index[getattr(item, "id")] = item  # write id index
            raise RuntimeError("simulated partial failure")
        coll._update_indexes = partial_update  # type: ignore[method-assign]

        with pytest.raises(RuntimeError):
            coll.append(p)

        # Restore and verify
        coll._update_indexes = original  # type: ignore[method-assign]
        assert p not in coll
        assert coll._id_index.get("P1") is None   # zombie entry must be gone
        assert len(coll) == 0


class TestTypeCollectionChangeId:
    def test_change_id_updates_index(self) -> None:
        coll: TypeCollection[Person] = TypeCollection(Person)
        p = Person(id="P1")
        coll.append(p)
        coll.change_id(p, "P2")
        assert coll.by_id("P1") is None
        assert coll.by_id("P2") is p
        assert p.id == "P2"

    def test_change_id_updates_auto_uri_fragment(self) -> None:
        coll: TypeCollection[Person] = TypeCollection(Person)
        p = Person(id="P1")
        coll.append(p)
        coll.change_id(p, "P2")
        assert getattr(p, "_uri").fragment == "P2"

    def test_change_id_collision_raises(self) -> None:
        coll: TypeCollection[Person] = TypeCollection(Person)
        p1 = Person(id="P1")
        p2 = Person(id="P2")
        coll.append(p1)
        coll.append(p2)
        with pytest.raises(ValueError, match="already used"):
            coll.change_id(p1, "P2")

    def test_change_id_same_id_is_noop(self) -> None:
        """Changing to the same id is allowed (no collision with self)."""
        coll: TypeCollection[Person] = TypeCollection(Person)
        p = Person(id="P1")
        coll.append(p)
        coll.change_id(p, "P1")
        assert coll.by_id("P1") is p

    def test_change_id_item_not_in_collection_raises(self) -> None:
        coll: TypeCollection[Person] = TypeCollection(Person)
        with pytest.raises(ValueError):
            coll.change_id(Person(id="GHOST"), "X")


class TestTypeCollectionChangeUri:
    def test_change_uri_string(self) -> None:
        from gedcomtools.gedcomx.uri import URI
        coll: TypeCollection[Person] = TypeCollection(Person)
        p = Person(id="P1")
        p.uri = URI(value="http://example.com/p1")
        coll.append(p)
        coll.change_uri(p, "http://example.com/p1-new")
        assert coll.by_uri("http://example.com/p1") is None
        assert coll.by_uri("http://example.com/p1-new") is p

    def test_change_uri_collision_raises(self) -> None:
        from gedcomtools.gedcomx.uri import URI
        coll: TypeCollection[Person] = TypeCollection(Person)
        p1 = Person(id="P1")
        p2 = Person(id="P2")
        p1.uri = URI(value="http://example.com/p1")
        p2.uri = URI(value="http://example.com/p2")
        coll.append(p1)
        coll.append(p2)
        with pytest.raises(ValueError, match="already used"):
            coll.change_uri(p1, "http://example.com/p2")

    def test_change_uri_clear(self) -> None:
        from gedcomtools.gedcomx.uri import URI
        coll: TypeCollection[Person] = TypeCollection(Person)
        p = Person(id="P1")
        p.uri = URI(value="http://example.com/p1")
        coll.append(p)
        coll.change_uri(p, None)
        assert coll.by_uri("http://example.com/p1") is None
        assert p.uri is None


class TestTypeCollectionChangeName:
    def test_change_name_updates_index(self) -> None:
        coll: TypeCollection[Agent] = TypeCollection(Agent)
        a = Agent(id="A1", names=[TextValue(value="Acme Corp")])
        coll.append(a)
        coll.change_name(a, "Acme Corp", "New Corp")
        assert coll.by_name("Acme Corp") == []
        assert coll.by_name("New Corp") == [a]

    def test_change_name_not_found_raises(self) -> None:
        coll: TypeCollection[Agent] = TypeCollection(Agent)
        a = Agent(id="A1", names=[TextValue(value="Acme")])
        coll.append(a)
        with pytest.raises(ValueError, match="not found"):
            coll.change_name(a, "Other", "Whatever")

    def test_change_name_no_collision_check(self) -> None:
        """Two agents may share a name — no error should be raised."""
        coll: TypeCollection[Agent] = TypeCollection(Agent)
        a1 = Agent(id="A1", names=[TextValue(value="Smith")])
        a2 = Agent(id="A2", names=[TextValue(value="Jones")])
        coll.append(a1)
        coll.append(a2)
        coll.change_name(a2, "Jones", "Smith")
        result = coll.by_name("Smith")
        assert result is not None and len(result) == 2


class TestGedcomXChangeMethods:
    def test_gx_change_id(self) -> None:
        gx = GedcomX()
        p = Person(id="P1")
        gx.add_person(p)
        gx.change_id(p, "P1_NEW")
        assert gx.persons.by_id("P1") is None
        assert gx.persons.by_id("P1_NEW") is p

    def test_gx_change_uri(self) -> None:
        from gedcomtools.gedcomx.uri import URI
        gx = GedcomX()
        p = Person(id="P1")
        p.uri = URI(value="http://example.com/p1")
        gx.add_person(p)
        gx.change_uri(p, "http://example.com/p1-updated")
        assert gx.persons.by_uri("http://example.com/p1") is None
        assert gx.persons.by_uri("http://example.com/p1-updated") is p

    def test_gx_change_name(self) -> None:
        gx = GedcomX()
        a = Agent(id="A1", names=[TextValue(value="Old Name")])
        gx.add_agent(a)
        gx.change_name(a, "Old Name", "New Name")
        assert gx.agents.by_name("Old Name") == []
        assert gx.agents.by_name("New Name") == [a]

    def test_gx_change_id_object_not_in_any_collection_raises(self) -> None:
        gx = GedcomX()
        with pytest.raises(ValueError, match="not found"):
            gx.change_id(Person(id="GHOST"), "X")

    def test_gx_change_id_finds_correct_collection(self) -> None:
        """change_id searches all collections, not just persons."""
        gx = GedcomX()
        a = Agent(id="A1")
        gx.add_agent(a)
        gx.change_id(a, "A1_NEW")
        assert gx.agents.by_id("A1") is None
        assert gx.agents.by_id("A1_NEW") is a


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

    def test_add_group(self):
        gx = GedcomX()
        gx.add(Group(id="G1", names=[TextValue(value="Research Group")]))
        assert len(gx.groups) == 1
        assert gx.groups.by_id("G1") is not None
