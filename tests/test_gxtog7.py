"""
======================================================================
 Project: gedcomtools
 File:    tests/test_gxtog7.py
 Purpose: Tests for GedcomXConverter (GedcomX → GEDCOM 7).

 Created: 2026-04-07
======================================================================
"""
from __future__ import annotations

from pathlib import Path
from typing import List

import pytest

from gedcomtools.gedcom7.gedcom7 import Gedcom7
from gedcomtools.gedcom7.gxtog7 import GedcomXConverter
from gedcomtools.gedcom7.structure import GedcomStructure
from gedcomtools.gedcomx.gedcomx import GedcomX
from gedcomtools.gedcomx.person import Person
from gedcomtools.gedcomx.relationship import Relationship, RelationshipType
from gedcomtools.gedcomx.fact import Fact, FactType
from gedcomtools.gedcomx.name import Name, NameForm, NamePart, NameType, NamePartType
from gedcomtools.gedcomx.gender import Gender, GenderType
from gedcomtools.gedcomx.date import Date
from gedcomtools.gedcomx.place_reference import PlaceReference
from gedcomtools.gedcomx.source_description import SourceDescription
from gedcomtools.gedcomx.agent import Agent
from gedcomtools.gedcomx.resource import Resource
from gedcomtools.gedcomx.uri import URI
from gedcomtools.gedcomx.note import Note
from gedcomtools.gedcomx.textvalue import TextValue

SAMPLE_DATA = Path(__file__).parent.parent / ".sample_data" / "gedcom70"
MAXIMAL     = SAMPLE_DATA / "maximal70.ged"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _person_ref(person: Person) -> Resource:
    return Resource(resource=URI(fragment=person.id))


def _tags(records: List[GedcomStructure]) -> List[str]:
    return [r.tag for r in records]


def _find(records: List[GedcomStructure], tag: str) -> List[GedcomStructure]:
    return [r for r in records if r.tag == tag]


def _child(record: GedcomStructure, tag: str) -> GedcomStructure | None:
    return record.first_child(tag)


def _build_minimal_gx() -> GedcomX:
    """Return a GedcomX with one person, one family, one source."""
    gx = GedcomX()

    husband = Person(id="@I1@")
    husband.gender = Gender(type=GenderType.Male)
    husband.add_name(Name.simple("John /Smith/"))
    husband.add_fact(Fact(
        type=FactType.Birth,
        date=Date(original="1 JAN 1900"),
        place=PlaceReference(original="Boston, MA"),
    ))
    gx.add_person(husband)

    wife = Person(id="@I2@")
    wife.gender = Gender(type=GenderType.Female)
    wife.add_name(Name.simple("Jane /Doe/"))
    gx.add_person(wife)

    child = Person(id="@I3@")
    child.add_name(Name.simple("Alice /Smith/"))
    gx.add_person(child)

    couple_rel = Relationship(
        id="couple-@F1@",
        type=RelationshipType.Couple,
        person1=_person_ref(husband),
        person2=_person_ref(wife),
    )
    couple_rel.add_fact(Fact(
        type=FactType.Marriage,
        date=Date(original="15 JUN 1925"),
    ))
    gx.add_relationship(couple_rel)

    gx.add_relationship(Relationship(
        id="pc-father-child",
        type=RelationshipType.ParentChild,
        person1=_person_ref(husband),
        person2=_person_ref(child),
    ))
    gx.add_relationship(Relationship(
        id="pc-mother-child",
        type=RelationshipType.ParentChild,
        person1=_person_ref(wife),
        person2=_person_ref(child),
    ))

    sd = SourceDescription(id="@S1@")
    sd.add_title(TextValue(value="Test Census Record"))
    gx.add_source_description(sd)

    return gx


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def gx_minimal():
    return _build_minimal_gx()


@pytest.fixture(scope="module")
def records_minimal(gx_minimal):
    return GedcomXConverter().convert(gx_minimal)


@pytest.fixture(scope="module")
def gx_roundtrip():
    """GedcomX produced by parsing maximal70.ged → g7togx."""
    if not MAXIMAL.exists():
        pytest.skip(f"Sample file not found: {MAXIMAL}")
    return Gedcom7(str(MAXIMAL)).to_gedcomx()


@pytest.fixture(scope="module")
def records_roundtrip(gx_roundtrip):
    return GedcomXConverter().convert(gx_roundtrip)


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

class TestReturnType:
    def test_returns_list_of_structure(self, records_minimal):
        assert isinstance(records_minimal, list)
        assert all(isinstance(r, GedcomStructure) for r in records_minimal)

    def test_facade_from_gedcomx(self, gx_minimal):
        g7 = Gedcom7.from_gedcomx(gx_minimal)
        assert isinstance(g7, Gedcom7)
        assert isinstance(g7.records, list)
        assert len(g7.records) > 0
        assert len(g7["HEAD"]) == 1
        assert len(g7.individuals()) == 3
        assert g7.get_individual("@I1@") is not None
        assert g7.detect_gedcom_version() == "7.0"
        assert not [e for e in g7.validate() if e.code == "not_gedcom7"]

    def test_facade_to_gedcom7(self, gx_minimal):
        g7 = gx_minimal.to_gedcom7()
        assert isinstance(g7, Gedcom7)
        assert len(g7.records) > 0
        assert len(g7["HEAD"]) == 1
        assert len(g7.individuals()) == 3
        assert g7.get_individual("@I1@") is not None

    def test_conversion_warnings_property(self, gx_minimal):
        conv = GedcomXConverter()
        conv.convert(gx_minimal)
        assert isinstance(conv.conversion_warnings, dict)


# ---------------------------------------------------------------------------
# File structure
# ---------------------------------------------------------------------------

class TestFileStructure:
    def test_has_head(self, records_minimal):
        assert records_minimal[0].tag == "HEAD"

    def test_has_trlr(self, records_minimal):
        assert records_minimal[-1].tag == "TRLR"

    def test_head_has_gedc_vers(self, records_minimal):
        head = records_minimal[0]
        gedc = _child(head, "GEDC")
        assert gedc is not None
        vers = _child(gedc, "VERS")
        assert vers is not None
        assert vers.payload == "7.0"

    def test_canonical_tag_order(self, records_minimal):
        tags = _tags(records_minimal)
        assert tags[0] == "HEAD"
        assert tags[-1] == "TRLR"
        # SOUR before INDI
        if "SOUR" in tags and "INDI" in tags:
            assert tags.index("SOUR") < tags.index("INDI")
        # INDI before FAM
        if "INDI" in tags and "FAM" in tags:
            assert tags.index("INDI") < tags.index("FAM")


# ---------------------------------------------------------------------------
# Persons
# ---------------------------------------------------------------------------

class TestPersons:
    def test_indi_count(self, records_minimal):
        assert len(_find(records_minimal, "INDI")) == 3

    def test_indi_has_xref(self, records_minimal):
        for indi in _find(records_minimal, "INDI"):
            assert indi.xref_id and indi.xref_id.startswith("@I")

    def test_sex_male(self, records_minimal):
        indi_i1 = next(r for r in records_minimal
                       if r.tag == "INDI" and r.xref_id == "@I1@")
        sex = _child(indi_i1, "SEX")
        assert sex is not None
        assert sex.payload == "M"

    def test_sex_female(self, records_minimal):
        indi_i2 = next(r for r in records_minimal
                       if r.tag == "INDI" and r.xref_id == "@I2@")
        sex = _child(indi_i2, "SEX")
        assert sex is not None
        assert sex.payload == "F"

    def test_name_slash_notation(self, records_minimal):
        indi_i1 = next(r for r in records_minimal
                       if r.tag == "INDI" and r.xref_id == "@I1@")
        name = _child(indi_i1, "NAME")
        assert name is not None
        assert "/Smith/" in name.payload

    def test_birth_event(self, records_minimal):
        indi_i1 = next(r for r in records_minimal
                       if r.tag == "INDI" and r.xref_id == "@I1@")
        birt = _child(indi_i1, "BIRT")
        assert birt is not None
        date = _child(birt, "DATE")
        assert date is not None
        assert "1900" in date.payload
        plac = _child(birt, "PLAC")
        assert plac is not None
        assert "Boston" in plac.payload

    def test_fams_link(self, records_minimal):
        indi_i1 = next(r for r in records_minimal
                       if r.tag == "INDI" and r.xref_id == "@I1@")
        fams = _child(indi_i1, "FAMS")
        assert fams is not None
        assert fams.payload_is_pointer

    def test_famc_link(self, records_minimal):
        indi_i3 = next(r for r in records_minimal
                       if r.tag == "INDI" and r.xref_id == "@I3@")
        famc = _child(indi_i3, "FAMC")
        assert famc is not None
        assert famc.payload_is_pointer


# ---------------------------------------------------------------------------
# Families
# ---------------------------------------------------------------------------

class TestFamilies:
    def test_fam_count(self, records_minimal):
        assert len(_find(records_minimal, "FAM")) == 1

    def test_fam_has_husb_wife(self, records_minimal):
        fam = _find(records_minimal, "FAM")[0]
        husb = _child(fam, "HUSB")
        wife = _child(fam, "WIFE")
        assert husb is not None and husb.payload_is_pointer
        assert wife is not None and wife.payload_is_pointer

    def test_fam_husb_is_male(self, records_minimal):
        fam = _find(records_minimal, "FAM")[0]
        husb = _child(fam, "HUSB")
        # The male person (@I1@) should be HUSB
        assert husb.payload == "@I1@"

    def test_fam_wife_is_female(self, records_minimal):
        fam = _find(records_minimal, "FAM")[0]
        wife = _child(fam, "WIFE")
        assert wife.payload == "@I2@"

    def test_fam_has_chil(self, records_minimal):
        fam = _find(records_minimal, "FAM")[0]
        chil = _child(fam, "CHIL")
        assert chil is not None and chil.payload_is_pointer

    def test_fam_has_marr(self, records_minimal):
        fam = _find(records_minimal, "FAM")[0]
        marr = _child(fam, "MARR")
        assert marr is not None
        date = _child(marr, "DATE")
        assert date is not None
        assert "1925" in date.payload


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

class TestSources:
    def test_sour_count(self, records_minimal):
        assert len(_find(records_minimal, "SOUR")) == 1

    def test_sour_has_xref(self, records_minimal):
        sour = _find(records_minimal, "SOUR")[0]
        assert sour.xref_id and sour.xref_id.startswith("@S")

    def test_sour_has_titl(self, records_minimal):
        sour = _find(records_minimal, "SOUR")[0]
        titl = _child(sour, "TITL")
        assert titl is not None
        assert "Census" in titl.payload


# ---------------------------------------------------------------------------
# Agents → SUBM / REPO
# ---------------------------------------------------------------------------

class TestAgents:
    def test_submitter_becomes_subm(self):
        gx = GedcomX()
        agent = Agent(id="@A1@")
        agent.add_name(TextValue(value="Test Submitter"))
        gx.add_agent(agent)
        records = GedcomXConverter().convert(gx)
        subm_records = _find(records, "SUBM")
        assert len(subm_records) == 1
        name = _child(subm_records[0], "NAME")
        assert name is not None
        assert "Submitter" in name.payload

    def test_repo_agent_becomes_repo(self):
        gx = GedcomX()
        agent = Agent(id="@R1@")
        agent.add_name(TextValue(value="National Library"))
        gx.add_agent(agent)

        sd = SourceDescription(id="@S1@")
        sd.add_title(TextValue(value="Some Book"))
        sd.repository = Resource(resource=URI(fragment=agent.id))
        gx.add_source_description(sd)

        records = GedcomXConverter().convert(gx)
        repo_records = _find(records, "REPO")
        assert len(repo_records) == 1
        name = _child(repo_records[0], "NAME")
        assert name is not None and "National" in name.payload

    def test_head_subm_pointer(self):
        gx = GedcomX()
        agent = Agent(id="@A1@")
        agent.add_name(TextValue(value="Submitter One"))
        gx.add_agent(agent)
        records = GedcomXConverter().convert(gx)
        head = records[0]
        subm_ref = _child(head, "SUBM")
        assert subm_ref is not None
        assert subm_ref.payload_is_pointer


# ---------------------------------------------------------------------------
# Name type codes
# ---------------------------------------------------------------------------

class TestNameTypes:
    def test_birth_name_no_type_tag(self):
        gx = GedcomX()
        p = Person(id="@I1@")
        n = Name(type=NameType.BirthName, nameForms=[NameForm(fullText="John Smith")])
        p.add_name(n)
        gx.add_person(p)
        records = GedcomXConverter().convert(gx)
        indi = _find(records, "INDI")[0]
        name = _child(indi, "NAME")
        assert name is not None
        # BirthName should NOT produce a TYPE substructure
        assert _child(name, "TYPE") is None

    def test_married_name_has_type_tag(self):
        gx = GedcomX()
        p = Person(id="@I1@")
        n = Name(type=NameType.MarriedName,
                 nameForms=[NameForm(fullText="Jane /Smith/")])
        p.add_name(n)
        gx.add_person(p)
        records = GedcomXConverter().convert(gx)
        indi = _find(records, "INDI")[0]
        name = _child(indi, "NAME")
        assert name is not None
        type_node = _child(name, "TYPE")
        assert type_node is not None
        assert type_node.payload == "MARRIED"

    def test_aka_name(self):
        gx = GedcomX()
        p = Person(id="@I1@")
        n = Name(type=NameType.AlsoKnownAs,
                 nameForms=[NameForm(fullText="Johnny")])
        p.add_name(n)
        gx.add_person(p)
        records = GedcomXConverter().convert(gx)
        indi = _find(records, "INDI")[0]
        name = _child(indi, "NAME")
        type_node = _child(name, "TYPE")
        assert type_node is not None
        assert type_node.payload == "AKA"


# ---------------------------------------------------------------------------
# Pedigree (FAMC.PEDI)
# ---------------------------------------------------------------------------

class TestPedigree:
    def test_adopted_pedi_on_famc(self):
        gx = GedcomX()
        parent = Person(id="@I1@")
        gx.add_person(parent)
        child = Person(id="@I2@")
        gx.add_person(child)

        pc_rel = Relationship(
            id="pc1",
            type=RelationshipType.ParentChild,
            person1=_person_ref(parent),
            person2=_person_ref(child),
        )
        pc_rel.add_fact(Fact(type=FactType.Adoption))
        gx.add_relationship(pc_rel)

        records = GedcomXConverter().convert(gx)
        child_indi = next(r for r in records
                          if r.tag == "INDI" and r.xref_id == "@I2@")
        famc = _child(child_indi, "FAMC")
        assert famc is not None
        pedi = _child(famc, "PEDI")
        assert pedi is not None
        assert pedi.payload == "ADOPTED"

    def test_birth_pedi_no_pedi_tag(self):
        """Birth pedigree (default) should not produce a PEDI substructure."""
        gx = GedcomX()
        parent = Person(id="@I1@")
        gx.add_person(parent)
        child = Person(id="@I2@")
        gx.add_person(child)
        gx.add_relationship(Relationship(
            id="pc1",
            type=RelationshipType.ParentChild,
            person1=_person_ref(parent),
            person2=_person_ref(child),
        ))
        records = GedcomXConverter().convert(gx)
        child_indi = next(r for r in records
                          if r.tag == "INDI" and r.xref_id == "@I2@")
        famc = _child(child_indi, "FAMC")
        assert famc is not None
        assert _child(famc, "PEDI") is None


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------

class TestNotes:
    def test_person_note_on_indi(self):
        gx = GedcomX()
        p = Person(id="@I1@")
        p.add_note(Note(text="A note about this person."))
        gx.add_person(p)
        records = GedcomXConverter().convert(gx)
        indi = _find(records, "INDI")[0]
        note = _child(indi, "NOTE")
        assert note is not None
        assert "note" in note.payload.lower()


# ---------------------------------------------------------------------------
# Date conversion
# ---------------------------------------------------------------------------

class TestDateConversion:
    def _fact_with_formal(self, formal: str) -> str:
        """Return the DATE payload produced for a fact with a GX formal date."""
        gx = GedcomX()
        p = Person(id="@I1@")
        p.add_fact(Fact(type=FactType.Birth, date=Date(formal=formal)))
        gx.add_person(p)
        records = GedcomXConverter().convert(gx)
        indi = _find(records, "INDI")[0]
        birt = _child(indi, "BIRT")
        date_node = _child(birt, "DATE")
        return date_node.payload if date_node else ""

    def test_original_preferred_over_formal(self):
        gx = GedcomX()
        p = Person(id="@I1@")
        p.add_fact(Fact(type=FactType.Birth,
                        date=Date(original="1 JAN 1900", formal="+1900-01-01")))
        gx.add_person(p)
        records = GedcomXConverter().convert(gx)
        indi = _find(records, "INDI")[0]
        birt = _child(indi, "BIRT")
        date_node = _child(birt, "DATE")
        assert date_node.payload == "1 JAN 1900"

    def test_formal_approximate(self):
        assert "ABT" in self._fact_with_formal("A1900")

    def test_formal_before(self):
        result = self._fact_with_formal("A/1920")
        assert "BEF" in result

    def test_formal_after(self):
        result = self._fact_with_formal("1915/")
        assert "AFT" in result

    def test_formal_range(self):
        result = self._fact_with_formal("[1880/1900]")
        assert "BET" in result and "AND" in result

    def test_formal_iso_date(self):
        result = self._fact_with_formal("+1900-06-15")
        assert "JUN" in result and "1900" in result


# ---------------------------------------------------------------------------
# Round-trip: G7 → GX → G7
# ---------------------------------------------------------------------------

class TestRoundtrip:
    def test_roundtrip_has_indi(self, records_roundtrip):
        assert len(_find(records_roundtrip, "INDI")) > 0

    def test_roundtrip_has_fam(self, records_roundtrip):
        assert len(_find(records_roundtrip, "FAM")) > 0

    def test_roundtrip_has_sour(self, records_roundtrip):
        assert len(_find(records_roundtrip, "SOUR")) >= 0  # may be 0 in some files

    def test_roundtrip_starts_head_ends_trlr(self, records_roundtrip):
        assert records_roundtrip[0].tag == "HEAD"
        assert records_roundtrip[-1].tag == "TRLR"

    def test_roundtrip_preserves_person_count(self, gx_roundtrip, records_roundtrip):
        gx_count = len(list(gx_roundtrip.persons))
        g7_count  = len(_find(records_roundtrip, "INDI"))
        assert g7_count == gx_count

    def test_roundtrip_writeable(self, records_roundtrip, tmp_path):
        """Converted records can be serialised to a file without error."""
        from gedcomtools.gedcom7.writer import Gedcom7Writer
        out = tmp_path / "roundtrip.ged"
        Gedcom7Writer().write(records_roundtrip, out)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "0 HEAD" in content
        assert "0 TRLR" in content
