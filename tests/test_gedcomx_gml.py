"""Tests for gedcomx/gml.py — GedcomXGmlExporter."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from gedcomtools.gedcomx.gml import GedcomXGmlExporter, _year_from_date, _resolve_person_id
from gedcomtools.gedcomx.gedcomx import GedcomX
from gedcomtools.gedcomx.person import Person
from gedcomtools.gedcomx.relationship import Relationship, RelationshipType
from gedcomtools.gedcomx.fact import Fact, FactType
from gedcomtools.gedcomx.name import Name, NameForm
from gedcomtools.gedcomx.gender import Gender, GenderType
from gedcomtools.gedcomx.date import Date
from gedcomtools.gedcomx.resource import Resource
from gedcomtools.gedcomx.uri import URI


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_person(
    gx: GedcomX,
    pid: str,
    full_name: str,
    gender: str = "Male",
    birth_year: int | None = None,
    birth_place: str | None = None,
    death_year: int | None = None,
) -> Person:
    p = Person(id=pid)
    p.add_name(Name.simple(full_name))
    if gender == "Male":
        p.gender = Gender(type=GenderType.Male)
    elif gender == "Female":
        p.gender = Gender(type=GenderType.Female)

    if birth_year is not None:
        birth = Fact(
            type=FactType.Birth,
            date=Date(original=str(birth_year)),
        )
        if birth_place:
            from gedcomtools.gedcomx.place_reference import PlaceReference
            birth.place = PlaceReference(original=birth_place)
        p.add_fact(birth)

    if death_year is not None:
        p.add_fact(Fact(
            type=FactType.Death,
            date=Date(original=str(death_year)),
        ))

    gx.add_person(p)
    return p


def _couple(gx: GedcomX, p1: Person, p2: Person,
            marriage_year: int | None = None) -> Relationship:
    rel = Relationship(
        type=RelationshipType.Couple,
        person1=Resource(resource=URI(fragment=p1.id)),
        person2=Resource(resource=URI(fragment=p2.id)),
    )
    if marriage_year is not None:
        rel.add_fact(Fact(
            type=FactType.Marriage,
            date=Date(original=str(marriage_year)),
        ))
    gx.add_relationship(rel)
    return rel


def _parent_child(gx: GedcomX, parent: Person, child: Person) -> Relationship:
    rel = Relationship(
        type=RelationshipType.ParentChild,
        person1=Resource(resource=URI(fragment=parent.id)),
        person2=Resource(resource=URI(fragment=child.id)),
    )
    gx.add_relationship(rel)
    return rel


def _make_family_gx() -> GedcomX:
    """Alice + Bob married 1950; they have a child Carol."""
    gx = GedcomX()
    alice = _make_person(gx, "@I1@", "Alice Smith", "Female",
                         birth_year=1925, birth_place="London, England",
                         death_year=2000)
    bob = _make_person(gx, "@I2@", "Bob Jones", "Male",
                       birth_year=1923, death_year=1998)
    carol = _make_person(gx, "@I3@", "Carol Jones", "Female", birth_year=1952)
    _couple(gx, alice, bob, marriage_year=1950)
    _parent_child(gx, alice, carol)
    _parent_child(gx, bob, carol)
    return gx


# ---------------------------------------------------------------------------
# Unit helpers
# ---------------------------------------------------------------------------

class TestYearFromDate:
    def test_formal_positive(self):
        d = Date(formal="+1900")
        assert _year_from_date(d) == 1900

    def test_formal_full_date(self):
        d = Date(formal="+1945-06-25")
        assert _year_from_date(d) == 1945

    def test_formal_approximate(self):
        d = Date(formal="A+1880")
        assert _year_from_date(d) == 1880

    def test_original_fallback(self):
        d = Date(original="15 June 1902")
        assert _year_from_date(d) == 1902

    def test_none_input(self):
        assert _year_from_date(None) is None


class TestResolvePersonId:
    def test_person_object(self):
        p = Person(id="@I1@")
        p.add_name(Name.simple("Alice"))
        assert _resolve_person_id(p) == "@I1@"

    def test_resource_with_fragment(self):
        r = Resource(resource=URI(fragment="@I2@"))
        assert _resolve_person_id(r) == "@I2@"

    def test_resource_with_resource_id(self):
        r = Resource(resourceId="@I3@")
        assert _resolve_person_id(r) == "@I3@"

    def test_none(self):
        assert _resolve_person_id(None) is None


# ---------------------------------------------------------------------------
# Exporter — structure
# ---------------------------------------------------------------------------

class TestGmlStructure:
    def test_export_returns_string(self):
        gx = _make_family_gx()
        out = GedcomXGmlExporter().export(gx)
        assert isinstance(out, str)

    def test_starts_with_graph(self):
        out = GedcomXGmlExporter().export(_make_family_gx())
        assert out.startswith("graph [")

    def test_ends_with_close_bracket(self):
        out = GedcomXGmlExporter().export(_make_family_gx())
        assert out.strip().endswith("]")

    def test_directed_flag(self):
        out = GedcomXGmlExporter().export(_make_family_gx())
        assert "directed 1" in out

    def test_node_count(self):
        out = GedcomXGmlExporter().export(_make_family_gx())
        assert out.count("node [") == 3

    def test_edge_count(self):
        out = GedcomXGmlExporter().export(_make_family_gx())
        assert out.count("edge [") == 3  # 1 Couple + 2 ParentChild

    def test_node_has_id(self):
        out = GedcomXGmlExporter().export(_make_family_gx())
        assert re.search(r"id \d+", out)

    def test_node_has_label(self):
        out = GedcomXGmlExporter().export(_make_family_gx())
        assert 'label "Alice Smith"' in out
        assert 'label "Bob Jones"' in out

    def test_empty_gx_produces_valid_gml(self):
        out = GedcomXGmlExporter().export(GedcomX())
        assert "graph [" in out
        assert "node [" not in out
        assert "edge [" not in out

    def test_gedcomx_gml_method(self):
        """GedcomX.gml() convenience method returns the same output as the exporter."""
        gx = _make_family_gx()
        assert gx.gml() == GedcomXGmlExporter().export(gx)


# ---------------------------------------------------------------------------
# Exporter — node attributes
# ---------------------------------------------------------------------------

class TestNodeAttributes:
    def test_gender_male(self):
        out = GedcomXGmlExporter().export(_make_family_gx())
        assert 'gender "Male"' in out

    def test_gender_female(self):
        out = GedcomXGmlExporter().export(_make_family_gx())
        assert 'gender "Female"' in out

    def test_birth_year(self):
        out = GedcomXGmlExporter().export(_make_family_gx())
        assert 'birth_year "1925"' in out
        assert 'birth_year "1923"' in out

    def test_death_year(self):
        out = GedcomXGmlExporter().export(_make_family_gx())
        assert 'death_year "2000"' in out
        assert 'death_year "1998"' in out

    def test_birth_place(self):
        out = GedcomXGmlExporter().export(_make_family_gx())
        assert 'birth_place "London, England"' in out

    def test_no_birth_year_when_unknown(self):
        gx = GedcomX()
        p = Person(id="@I1@")
        p.add_name(Name.simple("Jane"))
        gx.add_person(p)
        out = GedcomXGmlExporter().export(gx)
        # Unknown year emits empty string so all nodes have the same column set
        assert 'birth_year ""' in out

    def test_living_flag_false(self):
        out = GedcomXGmlExporter().export(_make_family_gx())
        assert 'living "false"' in out

    def test_living_flag_true(self):
        gx = GedcomX()
        p = Person(id="@I1@", living=True)
        p.add_name(Name.simple("Young"))
        gx.add_person(p)
        out = GedcomXGmlExporter().export(gx)
        assert 'living "true"' in out


# ---------------------------------------------------------------------------
# Exporter — edge attributes
# ---------------------------------------------------------------------------

class TestEdgeAttributes:
    def test_couple_label(self):
        out = GedcomXGmlExporter().export(_make_family_gx())
        assert 'label "Couple"' in out

    def test_parent_child_label(self):
        out = GedcomXGmlExporter().export(_make_family_gx())
        assert 'label "ParentChild"' in out

    def test_marriage_year(self):
        out = GedcomXGmlExporter().export(_make_family_gx())
        assert 'marriage_year "1950"' in out

    def test_no_marriage_year_when_unknown(self):
        gx = GedcomX()
        p1 = _make_person(gx, "@I1@", "Alice")
        p2 = _make_person(gx, "@I2@", "Bob")
        _couple(gx, p1, p2)  # no marriage year
        out = GedcomXGmlExporter().export(gx)
        # Unknown year emits empty string so all edges have the same column set
        assert 'marriage_year ""' in out

    def test_divorce_year(self):
        gx = GedcomX()
        p1 = _make_person(gx, "@I1@", "Alice")
        p2 = _make_person(gx, "@I2@", "Bob")
        rel = _couple(gx, p1, p2)
        rel.add_fact(Fact(
            type=FactType.Divorce,
            date=Date(original="1960"),
        ))
        out = GedcomXGmlExporter().export(gx)
        assert 'divorce_year "1960"' in out

    def test_dangling_reference_skipped(self):
        gx = GedcomX()
        p1 = _make_person(gx, "@I1@", "Alice")
        # person2 references a nonexistent person
        rel = Relationship(
            type=RelationshipType.Couple,
            person1=Resource(resource=URI(fragment="@I1@")),
            person2=Resource(resource=URI(fragment="@MISSING@")),
        )
        gx.add_relationship(rel)
        out = GedcomXGmlExporter().export(gx)
        assert out.count("edge [") == 0

    def test_source_target_are_integers(self):
        out = GedcomXGmlExporter().export(_make_family_gx())
        sources = re.findall(r"source (\S+)", out)
        targets = re.findall(r"target (\S+)", out)
        for v in sources + targets:
            assert v.isdigit(), f"Expected integer, got {v!r}"

    def test_custom_attrs_are_strings_not_integers(self):
        """All custom attributes must be quoted strings — bare integers cause
        ClassCastException in Gephi's attribute list builder."""
        out = GedcomXGmlExporter().export(_make_family_gx())
        custom_keys = ("birth_year", "death_year", "living",
                       "marriage_year", "divorce_year")
        for line in out.splitlines():
            s = line.strip()
            for key in custom_keys:
                if s.startswith(key + " "):
                    val = s[len(key) + 1:]
                    assert val.startswith('"') and val.endswith('"'), (
                        f"{key} value {val!r} is not a quoted string"
                    )


# ---------------------------------------------------------------------------
# Exporter — string escaping
# ---------------------------------------------------------------------------

class TestGmlStringEscaping:
    def _person_with_name(self, name: str) -> GedcomX:
        gx = GedcomX()
        p = Person(id="@I1@")
        p.add_name(Name(nameForms=[NameForm(fullText=name)]))
        gx.add_person(p)
        return gx

    def test_double_quotes_escaped(self):
        # GML spec uses HTML entity &quot; — backslash escapes are NOT valid
        out = GedcomXGmlExporter().export(self._person_with_name('O\'Brien "The" Smith'))
        assert '&quot;The&quot;' in out

    def test_backslash_passthrough(self):
        # Backslash has no special meaning in GML — passed through as-is
        out = GedcomXGmlExporter().export(self._person_with_name("back\\slash"))
        assert "back\\slash" in out

    def test_smart_double_quotes_encoded(self):
        # Smart quotes are non-ASCII → encoded as numeric entities
        out = GedcomXGmlExporter().export(self._person_with_name("\u201cHello\u201d"))
        assert "&#8220;" in out or "&#8221;" in out

    def test_smart_single_quotes_encoded(self):
        # Smart apostrophe is non-ASCII → numeric entity
        out = GedcomXGmlExporter().export(self._person_with_name("O\u2019Brien"))
        assert "&#8217;" in out

    def test_low9_double_quote_encoded(self):
        out = GedcomXGmlExporter().export(self._person_with_name("\u201eTest\u201c"))
        assert "&#8222;" in out or "&#8220;" in out

    def test_angle_quotes_encoded(self):
        out = GedcomXGmlExporter().export(self._person_with_name("\u00abTest\u00bb"))
        assert "&#171;" in out or "&#187;" in out

    def test_ampersand_escaped(self):
        out = GedcomXGmlExporter().export(self._person_with_name("Smith & Jones"))
        assert "&amp;" in out

    def test_newline_encoded(self):
        out = GedcomXGmlExporter().export(self._person_with_name("Line1\nLine2"))
        assert "&#10;" in out
        assert "\n" not in out.split('label "')[1].split('"')[0]

    def test_tab_encoded(self):
        out = GedcomXGmlExporter().export(self._person_with_name("Col1\tCol2"))
        assert "&#9;" in out

    def test_carriage_return_encoded(self):
        out = GedcomXGmlExporter().export(self._person_with_name("A\rB"))
        assert "&#13;" in out

    def test_brackets_allowed_in_strings(self):
        # Per GML spec, [ ] have no special meaning inside quoted strings
        out = GedcomXGmlExporter().export(self._person_with_name("John [Sir] Smith"))
        assert 'John [Sir] Smith' in out

    def test_no_backslash_escapes_in_output(self):
        # Verify we never emit backslash-escape sequences (not valid GML)
        out = GedcomXGmlExporter().export(self._person_with_name('He said "hello"'))
        assert '\\"' not in out


# ---------------------------------------------------------------------------
# Exporter — write to file
# ---------------------------------------------------------------------------

class TestWriteToFile:
    def test_write_creates_file(self, tmp_path):
        dest = tmp_path / "family.gml"
        GedcomXGmlExporter().write(_make_family_gx(), dest)
        assert dest.exists()

    def test_write_content_correct(self, tmp_path):
        dest = tmp_path / "family.gml"
        GedcomXGmlExporter().write(_make_family_gx(), dest)
        content = dest.read_text(encoding="utf-8")
        assert "Alice Smith" in content
        assert "Couple" in content

    def test_write_missing_directory(self, tmp_path):
        dest = tmp_path / "nonexistent" / "family.gml"
        with pytest.raises(FileNotFoundError):
            GedcomXGmlExporter().write(_make_family_gx(), dest)

    def test_write_no_tmp_on_error(self, tmp_path):
        dest = tmp_path / "nonexistent" / "family.gml"
        try:
            GedcomXGmlExporter().write(_make_family_gx(), dest)
        except FileNotFoundError:
            pass
        assert not list(tmp_path.rglob("*.tmp"))


# ---------------------------------------------------------------------------
# Round-trip via test.py sample data (integration)
# ---------------------------------------------------------------------------

_SAMPLE_GED = (
    Path(__file__).parent.parent / ".sample_data" / "gedcom5" / ".djc.ged"
)


@pytest.mark.skipif(not _SAMPLE_GED.exists(), reason="sample data not present")
def test_gml_from_real_file(tmp_path):
    from gedcomtools.gedcom5.gedcom5 import Gedcom5
    g5 = Gedcom5(_SAMPLE_GED)
    gx = g5.to_gedcomx()
    dest = tmp_path / "real.gml"
    GedcomXGmlExporter().write(gx, dest)
    content = dest.read_text(encoding="utf-8")
    assert content.count("node [") == len(list(gx.persons))
    # Relationships with dangling person refs are skipped, so edge count ≤ rel count.
    edge_count = content.count("edge [")
    rel_count = len(list(gx.relationships))
    assert edge_count <= rel_count
    assert edge_count > 0
