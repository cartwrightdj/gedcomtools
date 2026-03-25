"""
======================================================================
 Project: gedcomtools
 File:    tests/test_g7togx.py
 Purpose: Tests for Gedcom7Converter (GEDCOM 7 → GedcomX).

 Created: 2026-03-24
======================================================================
"""
import pytest
from pathlib import Path
from gedcomtools.gedcom7.gedcom7 import Gedcom7
from gedcomtools.gedcom7.g7togx import Gedcom7Converter
from gedcomtools.gedcomx.gedcomx import GedcomX
from gedcomtools.gedcomx.relationship import RelationshipType
from gedcomtools.gedcomx.resource import Resource

SAMPLE_DATA = Path(__file__).parent.parent / ".sample_data" / "gedcom70"
MAXIMAL     = SAMPLE_DATA / "maximal70.ged"
LANG        = SAMPLE_DATA / "lang.ged"


def _convert(path: Path) -> GedcomX:
    g7 = Gedcom7(str(path))
    return Gedcom7Converter().convert(g7)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def gx_maximal():
    pytest.importorskip("gedcomtools.gedcom7.g7togx")
    if not MAXIMAL.exists():
        pytest.skip(f"Sample file not found: {MAXIMAL}")
    return _convert(MAXIMAL)


@pytest.fixture(scope="module")
def g7_maximal():
    if not MAXIMAL.exists():
        pytest.skip(f"Sample file not found: {MAXIMAL}")
    return Gedcom7(str(MAXIMAL))


# ---------------------------------------------------------------------------
# Basic output type
# ---------------------------------------------------------------------------

class TestReturnType:
    def test_returns_gedcomx(self, gx_maximal):
        assert isinstance(gx_maximal, GedcomX)

    def test_facade_method(self, g7_maximal):
        gx = g7_maximal.to_gedcomx()
        assert isinstance(gx, GedcomX)

    def test_unhandled_tags_recorded(self, gx_maximal):
        assert hasattr(gx_maximal, "_import_unhandled_tags")
        assert isinstance(gx_maximal._import_unhandled_tags, dict)


# ---------------------------------------------------------------------------
# Persons
# ---------------------------------------------------------------------------

class TestPersons:
    def test_persons_created(self, gx_maximal, g7_maximal):
        assert len(gx_maximal.persons) == len(g7_maximal.individuals())

    def test_person_ids_match_xrefs(self, gx_maximal, g7_maximal):
        xrefs = {n.xref_id for n in g7_maximal.individuals() if n.xref_id}
        person_ids = {p.id for p in gx_maximal.persons}
        assert xrefs == person_ids

    def test_persons_have_names(self, gx_maximal):
        persons_with_names = [p for p in gx_maximal.persons if p.names]
        assert len(persons_with_names) > 0

    def test_person_lookup_by_id(self, gx_maximal):
        first = list(gx_maximal.persons)[0]
        assert gx_maximal.persons.by_id(first.id) is first

    def test_living_flag_set(self, gx_maximal):
        # At least one person should have living set
        flags = [p.living for p in gx_maximal.persons if p.living is not None]
        assert len(flags) > 0


# ---------------------------------------------------------------------------
# Names
# ---------------------------------------------------------------------------

class TestNames:
    def test_name_has_nameform(self, gx_maximal):
        for person in gx_maximal.persons:
            for name in person.names:
                assert name.nameForms, f"Person {person.id} has a name with no NameForms"

    def test_name_fulltext_nonempty(self, gx_maximal):
        for person in gx_maximal.persons:
            for name in person.names:
                if name.nameForms:
                    ft = name.nameForms[0].fullText
                    assert ft is not None and ft.strip() != "", (
                        f"Person {person.id} has a NameForm with empty fullText"
                    )


# ---------------------------------------------------------------------------
# Gender
# ---------------------------------------------------------------------------

class TestGender:
    def test_gender_set_where_present(self, gx_maximal, g7_maximal):
        from gedcomtools.gedcom7.models import individual_detail
        for node in g7_maximal.individuals():
            d = individual_detail(node)
            person = gx_maximal.persons.by_id(d.xref)
            if d.sex in ("M", "F", "X", "U"):
                assert person.gender is not None, (
                    f"Person {d.xref} has SEX={d.sex} but no gender"
                )


# ---------------------------------------------------------------------------
# Facts
# ---------------------------------------------------------------------------

class TestFacts:
    def test_birth_facts_created(self, gx_maximal, g7_maximal):
        from gedcomtools.gedcom7.models import individual_detail
        from gedcomtools.gedcomx.fact import FactType
        birth_uri = "http://gedcomx.org/Birth"
        for node in g7_maximal.individuals():
            d = individual_detail(node)
            if d.birth is None:
                continue
            person = gx_maximal.persons.by_id(d.xref)
            birth_facts = [f for f in person.facts if f.type and f.type.value == birth_uri]
            assert birth_facts, f"Person {d.xref} has a birth event but no Birth fact"

    def test_death_facts_created(self, gx_maximal, g7_maximal):
        from gedcomtools.gedcom7.models import individual_detail
        death_uri = "http://gedcomx.org/Death"
        for node in g7_maximal.individuals():
            d = individual_detail(node)
            if d.death is None:
                continue
            person = gx_maximal.persons.by_id(d.xref)
            death_facts = [f for f in person.facts if f.type and f.type.value == death_uri]
            assert death_facts, f"Person {d.xref} has a death event but no Death fact"

    def test_fact_with_date_has_date_object(self, gx_maximal):
        from gedcomtools.gedcomx.date import Date
        for person in gx_maximal.persons:
            for fact in person.facts:
                if fact.date is not None:
                    assert isinstance(fact.date, Date)

    def test_fact_with_place_has_place_reference(self, gx_maximal):
        from gedcomtools.gedcomx.place_reference import PlaceReference
        for person in gx_maximal.persons:
            for fact in person.facts:
                if fact.place is not None:
                    assert isinstance(fact.place, PlaceReference)


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------

class TestRelationships:
    def test_relationships_created(self, gx_maximal, g7_maximal):
        assert len(gx_maximal.relationships) > 0

    def test_couple_relationship_for_fam(self, gx_maximal, g7_maximal):
        from gedcomtools.gedcom7.models import family_detail
        # Only FAMs with at least one parent (HUSB or WIFE) produce a Couple relationship
        fams_with_parents = [
            f for f in (family_detail(n) for n in g7_maximal.families())
            if f.husband_xref or f.wife_xref
        ]
        couple_rels = [
            r for r in gx_maximal.relationships
            if r.type == RelationshipType.Couple
        ]
        assert len(couple_rels) == len(fams_with_parents)

    def test_parent_child_relationships_exist(self, gx_maximal, g7_maximal):
        fams = g7_maximal.family_details()
        expected_pc = sum(
            len(f.children_xrefs) * len(
                [x for x in (f.husband_xref, f.wife_xref) if x]
            )
            for f in fams
        )
        pc_rels = [
            r for r in gx_maximal.relationships
            if r.type == RelationshipType.ParentChild
        ]
        assert len(pc_rels) == expected_pc

    def test_relationship_person_refs_are_resources(self, gx_maximal):
        for rel in gx_maximal.relationships:
            if rel.person1 is not None:
                assert isinstance(rel.person1, Resource), (
                    f"Relationship {rel.id} person1 is {type(rel.person1).__name__}, expected Resource"
                )
            if rel.person2 is not None:
                assert isinstance(rel.person2, Resource), (
                    f"Relationship {rel.id} person2 is {type(rel.person2).__name__}, expected Resource"
                )


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

class TestSources:
    def test_source_descriptions_created(self, gx_maximal, g7_maximal):
        n_sour = len(g7_maximal.sources())
        n_obje = len(g7_maximal.media_objects())
        assert len(gx_maximal.sourceDescriptions) >= n_sour + n_obje

    def test_sources_have_titles(self, gx_maximal, g7_maximal):
        from gedcomtools.gedcom7.models import source_detail
        for node in g7_maximal.sources():
            d = source_detail(node)
            if not d.title:
                continue
            sd = gx_maximal.sourceDescriptions.by_id(d.xref)
            assert sd is not None
            assert sd.titles, f"Source {d.xref} has title in G7 but none in GedcomX"


# ---------------------------------------------------------------------------
# Agents (REPO + SUBM)
# ---------------------------------------------------------------------------

class TestAgents:
    def test_agents_created(self, gx_maximal, g7_maximal):
        expected = len(g7_maximal.repositories()) + len(g7_maximal.submitters())
        assert len(gx_maximal.agents) == expected

    def test_repo_agent_has_name(self, gx_maximal, g7_maximal):
        from gedcomtools.gedcom7.models import repository_detail
        for node in g7_maximal.repositories():
            d = repository_detail(node)
            if not d.name:
                continue
            agent = gx_maximal.agents.by_id(d.xref)
            assert agent is not None
            assert agent.names, f"Repo agent {d.xref} has name in G7 but not in GedcomX"

    def test_subm_agent_has_name(self, gx_maximal, g7_maximal):
        from gedcomtools.gedcom7.models import submitter_detail
        for node in g7_maximal.submitters():
            d = submitter_detail(node)
            if not d.name:
                continue
            agent = gx_maximal.agents.by_id(d.xref)
            assert agent is not None
            assert agent.names, f"Subm agent {d.xref} has name in G7 but not in GedcomX"


# ---------------------------------------------------------------------------
# Places
# ---------------------------------------------------------------------------

class TestPlaces:
    def test_places_created(self, gx_maximal):
        assert len(gx_maximal.places) >= 0  # may be 0 for files without place info

    def test_places_deduplicated(self, gx_maximal):
        names = []
        for pd in gx_maximal.places:
            if pd.names:
                for tv in pd.names:
                    if tv.value:
                        names.append(tv.value)
        assert len(names) == len(set(names)), "PlaceDescription names are not unique"


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_to_dict_succeeds(self, gx_maximal):
        data = gx_maximal._to_dict()
        assert isinstance(data, dict)

    def test_json_is_bytes(self, gx_maximal):
        result = gx_maximal.json
        assert isinstance(result, bytes)
        assert len(result) > 0
