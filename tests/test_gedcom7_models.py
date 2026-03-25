"""Tests for gedcom7/models.py — IndividualDetail, FamilyDetail, etc."""
from __future__ import annotations

import pytest

from gedcomtools.gedcom7 import Gedcom7
from gedcomtools.gedcom7.models import (
    EventDetail,
    FamilyDetail,
    IndividualDetail,
    MediaDetail,
    NameDetail,
    RepositoryDetail,
    SharedNoteDetail,
    SourceCitation,
    SourceDetail,
    SubmitterDetail,
    family_detail,
    individual_detail,
    media_detail,
    repository_detail,
    shared_note_detail,
    source_detail,
    submitter_detail,
)
from gedcomtools.gedcom7.structure import GedcomStructure


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse(text: str) -> Gedcom7:
    g = Gedcom7()
    g.parse_string(text)
    return g


def _indi(text: str) -> IndividualDetail:
    g = _parse(text)
    return individual_detail(g["INDI"][0])


def _fam(text: str) -> FamilyDetail:
    g = _parse(text)
    return family_detail(g["FAM"][0])


# ---------------------------------------------------------------------------
# EventDetail.year  (bug fix: dual-year notation, INT dates, qualifiers)
# ---------------------------------------------------------------------------

class TestEventDetailYear:
    def test_plain_year(self):
        e = EventDetail(date="1 JAN 2000")
        assert e.year == 2000

    def test_qualifier_year(self):
        assert EventDetail(date="ABT 1850").year == 1850
        assert EventDetail(date="BEF 1900").year == 1900
        assert EventDetail(date="AFT 1750").year == 1750

    def test_dual_year(self):
        # Dual-year notation (Julian calendar): should return the primary year
        assert EventDetail(date="1800/01").year == 1800

    def test_three_digit_year(self):
        assert EventDetail(date="900").year == 900

    def test_range_year_from(self):
        # FROM…TO range: should return the first year found
        e = EventDetail(date="FROM 1900 TO 1910")
        assert e.year == 1900

    def test_int_date_year(self):
        e = EventDetail(date="INT about this time (1850)")
        assert e.year == 1850

    def test_none_when_no_date(self):
        assert EventDetail(date=None).year is None

    def test_none_when_no_digits(self):
        assert EventDetail(date="Unknown").year is None

    def test_bet_and_year(self):
        e = EventDetail(date="BET 1900 AND 1910")
        assert e.year == 1900


# ---------------------------------------------------------------------------
# EventDetail.qualifier
# ---------------------------------------------------------------------------

class TestEventDetailQualifier:
    def test_abt(self):
        assert EventDetail(date="ABT 1850").qualifier == "ABT"

    def test_bef(self):
        assert EventDetail(date="BEF 1900").qualifier == "BEF"

    def test_no_qualifier(self):
        assert EventDetail(date="1 JAN 1900").qualifier is None

    def test_none_date(self):
        assert EventDetail(date=None).qualifier is None


# ---------------------------------------------------------------------------
# EventDetail.age_years
# ---------------------------------------------------------------------------

class TestEventDetailAgeYears:
    def test_years_only(self):
        assert EventDetail(age="45y").age_years == 45

    def test_years_months(self):
        assert EventDetail(age="45y 3m").age_years == 45

    def test_no_years(self):
        assert EventDetail(age="3m 10d").age_years is None

    def test_none_age(self):
        assert EventDetail(age=None).age_years is None


# ---------------------------------------------------------------------------
# IndividualDetail — basic fields
# ---------------------------------------------------------------------------

_BASIC_INDI = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME Alice /Smith/
2 GIVN Alice
2 SURN Smith
1 SEX F
1 BIRT
2 DATE 1 JAN 1900
2 PLAC Springfield
1 DEAT
2 DATE 15 MAR 1975
0 TRLR
"""


class TestIndividualDetailBasic:
    def test_xref(self):
        assert _indi(_BASIC_INDI).xref == "@I1@"

    def test_sex(self):
        assert _indi(_BASIC_INDI).sex == "F"

    def test_full_name(self):
        detail = _indi(_BASIC_INDI)
        assert detail.full_name == "Alice Smith"

    def test_given_surname(self):
        detail = _indi(_BASIC_INDI)
        assert detail.name.given == "Alice"
        assert detail.name.surname == "Smith"

    def test_birth_year(self):
        assert _indi(_BASIC_INDI).birth_year == 1900

    def test_death_year(self):
        assert _indi(_BASIC_INDI).death_year == 1975

    def test_is_living_false(self):
        assert not _indi(_BASIC_INDI).is_living

    def test_age_at_death(self):
        assert _indi(_BASIC_INDI).age_at_death == 75

    def test_birth_place(self):
        assert _indi(_BASIC_INDI).birth.place == "Springfield"


class TestIndividualDetailNoNames:
    def test_full_name_fallback(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 SEX M
0 TRLR
"""
        detail = _indi(text)
        assert detail.full_name == "Unknown"
        assert detail.name is None

    def test_is_living_true(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME Bob /Jones/
0 TRLR
"""
        detail = _indi(text)
        assert detail.is_living is True


# ---------------------------------------------------------------------------
# IndividualDetail — optional fields
# ---------------------------------------------------------------------------

class TestIndividualDetailOptional:
    _TEXT = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME Alice /Smith/
1 OCCU Carpenter
1 TITL Dr.
1 RELI Catholic
1 NATI Irish
1 RESN CONFIDENTIAL
1 UID abc-123
0 TRLR
"""

    def test_occupation(self):
        assert _indi(self._TEXT).occupation == "Carpenter"

    def test_title(self):
        assert _indi(self._TEXT).title == "Dr."

    def test_religion(self):
        assert _indi(self._TEXT).religion == "Catholic"

    def test_nationality(self):
        assert _indi(self._TEXT).nationality == "Irish"

    def test_restriction(self):
        assert _indi(self._TEXT).restriction == "CONFIDENTIAL"

    def test_uid(self):
        assert _indi(self._TEXT).uid == "abc-123"


# ---------------------------------------------------------------------------
# IndividualDetail — multiple events / residences
# ---------------------------------------------------------------------------

class TestIndividualDetailEvents:
    _TEXT = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME Alice /Smith/
1 RESI
2 DATE FROM 1920 TO 1930
2 PLAC Chicago
1 RESI
2 DATE FROM 1930 TO 1940
2 PLAC New York
1 EVEN
2 TYPE Military service
2 DATE 1918
0 TRLR
"""

    def test_residences_count(self):
        assert len(_indi(self._TEXT).residences) == 2

    def test_residence_places(self):
        detail = _indi(self._TEXT)
        places = [r.place for r in detail.residences]
        assert "Chicago" in places
        assert "New York" in places

    def test_generic_events(self):
        detail = _indi(self._TEXT)
        assert len(detail.events) == 1
        assert detail.events[0].event_type == "Military service"


# ---------------------------------------------------------------------------
# IndividualDetail — source citations
# ---------------------------------------------------------------------------

class TestIndividualDetailSources:
    _TEXT = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @S1@ SOUR
1 TITL Census 1900
0 @I1@ INDI
1 NAME Alice /Smith/
1 SOUR @S1@
2 PAGE p. 42
2 QUAY 2
0 TRLR
"""

    def test_source_citation_xref(self):
        detail = _indi(self._TEXT)
        assert len(detail.source_citations) == 1
        assert detail.source_citations[0].xref == "@S1@"

    def test_source_citation_page(self):
        assert _indi(self._TEXT).source_citations[0].page == "p. 42"

    def test_source_citation_quay(self):
        assert _indi(self._TEXT).source_citations[0].quality == "2"


# ---------------------------------------------------------------------------
# IndividualDetail — notes
# ---------------------------------------------------------------------------

class TestIndividualDetailNotes:
    _TEXT = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @N1@ SNOTE This is a shared note.
0 @I1@ INDI
1 NAME Alice /Smith/
1 NOTE An inline note.
1 SNOTE @N1@
0 TRLR
"""

    def test_inline_notes(self):
        detail = _indi(self._TEXT)
        assert "An inline note." in detail.note_texts

    def test_shared_note_refs(self):
        detail = _indi(self._TEXT)
        assert "@N1@" in detail.shared_note_refs


# ---------------------------------------------------------------------------
# IndividualDetail — family links
# ---------------------------------------------------------------------------

class TestIndividualDetailFamilyLinks:
    _TEXT = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME Alice /Smith/
1 FAMS @F1@
1 FAMC @F2@
0 @F1@ FAM
1 WIFE @I1@
0 @F2@ FAM
1 CHIL @I1@
0 TRLR
"""

    def test_families_as_spouse(self):
        detail = _indi(self._TEXT)
        assert "@F1@" in detail.families_as_spouse

    def test_families_as_child(self):
        detail = _indi(self._TEXT)
        assert "@F2@" in [lnk.xref for lnk in detail.families_as_child]


# ---------------------------------------------------------------------------
# NameDetail.display
# ---------------------------------------------------------------------------

class TestNameDetailDisplay:
    def test_slash_removed(self):
        nd = NameDetail(full="John /Doe/")
        assert nd.display == "John Doe"

    def test_patronymic_slash(self):
        nd = NameDetail(full="Lt. /de Allen/ jr.")
        assert nd.display == "Lt. de Allen jr."

    def test_no_slashes(self):
        nd = NameDetail(full="John Doe")
        assert nd.display == "John Doe"


# ---------------------------------------------------------------------------
# NameDetail.translations
# ---------------------------------------------------------------------------

class TestNameDetailTranslations:
    _TEXT = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME Johann /Müller/
2 GIVN Johann
2 SURN Müller
2 TRAN John /Miller/
3 LANG en
3 GIVN John
3 SURN Miller
0 TRLR
"""

    def test_translation_count(self):
        detail = _indi(self._TEXT)
        assert len(detail.name.translations) == 1

    def test_translation_lang(self):
        detail = _indi(self._TEXT)
        assert detail.name.translations[0].lang == "en"

    def test_translation_full(self):
        detail = _indi(self._TEXT)
        assert detail.name.translations[0].full == "John /Miller/"

    def test_translation_given_surname(self):
        detail = _indi(self._TEXT)
        tran = detail.name.translations[0]
        assert tran.given == "John"
        assert tran.surname == "Miller"


# ---------------------------------------------------------------------------
# EventDetail.place_translations
# ---------------------------------------------------------------------------

class TestEventDetailPlaceTranslations:
    _TEXT = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME Alice /Smith/
1 BIRT
2 DATE 1 JAN 1900
2 PLAC Springfield
3 TRAN Springfeld
4 LANG de
3 TRAN Springfeldois
4 LANG fr
0 TRLR
"""

    def test_translations_count(self):
        detail = _indi(self._TEXT)
        assert len(detail.birth.place_translations) == 2

    def test_german_translation(self):
        detail = _indi(self._TEXT)
        assert detail.birth.place_translations["de"] == "Springfeld"

    def test_french_translation(self):
        detail = _indi(self._TEXT)
        assert detail.birth.place_translations["fr"] == "Springfeldois"

    def test_no_translations_empty_dict(self):
        text = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 BIRT
2 DATE 1 JAN 1900
2 PLAC Springfield
0 TRLR
"""
        detail = _indi(text)
        assert detail.birth.place_translations == {}


# ---------------------------------------------------------------------------
# FamilyDetail
# ---------------------------------------------------------------------------

class TestFamilyDetail:
    _TEXT = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME Alice /Smith/
1 FAMS @F1@
0 @I2@ INDI
1 NAME Bob /Jones/
1 FAMS @F1@
0 @I3@ INDI
1 NAME Charlie /Jones/
1 FAMC @F1@
0 @F1@ FAM
1 WIFE @I1@
1 HUSB @I2@
1 CHIL @I3@
1 MARR
2 DATE 15 JUN 1920
2 PLAC Chicago
0 TRLR
"""

    def test_xref(self):
        assert _fam(self._TEXT).xref == "@F1@"

    def test_husband_wife(self):
        detail = _fam(self._TEXT)
        assert detail.husband_xref == "@I2@"
        assert detail.wife_xref == "@I1@"

    def test_children(self):
        detail = _fam(self._TEXT)
        assert "@I3@" in detail.children_xrefs

    def test_num_children(self):
        assert _fam(self._TEXT).num_children == 1

    def test_marriage_year(self):
        assert _fam(self._TEXT).marriage_year == 1920

    def test_marriage_place(self):
        assert _fam(self._TEXT).marriage.place == "Chicago"

    def test_no_divorce(self):
        detail = _fam(self._TEXT)
        assert detail.divorce is None
        assert detail.divorce_year is None


# ---------------------------------------------------------------------------
# SourceDetail
# ---------------------------------------------------------------------------

class TestSourceDetail:
    _TEXT = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @R1@ REPO
1 NAME City Library
0 @S1@ SOUR
1 TITL Census 1900
1 AUTH John Archivist
1 PUBL Government Press, 1901
1 ABBR CENS1900
1 REPO @R1@
2 CALN box 12
0 @I1@ INDI
1 SOUR @S1@
0 TRLR
"""

    def test_title(self):
        g = _parse(self._TEXT)
        detail = source_detail(g["SOUR"][0])
        assert detail.title == "Census 1900"

    def test_author(self):
        g = _parse(self._TEXT)
        assert source_detail(g["SOUR"][0]).author == "John Archivist"

    def test_publication(self):
        g = _parse(self._TEXT)
        assert source_detail(g["SOUR"][0]).publication == "Government Press, 1901"

    def test_abbreviation(self):
        g = _parse(self._TEXT)
        assert source_detail(g["SOUR"][0]).abbreviation == "CENS1900"

    def test_repository_refs(self):
        g = _parse(self._TEXT)
        detail = source_detail(g["SOUR"][0])
        assert "@R1@" in detail.repository_refs


# ---------------------------------------------------------------------------
# RepositoryDetail
# ---------------------------------------------------------------------------

class TestRepositoryDetail:
    _TEXT = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @R1@ REPO
1 NAME City Library
1 ADDR 123 Main St
1 PHON 555-1234
1 EMAIL library@example.com
1 WWW https://example.com
0 @S1@ SOUR
1 TITL A Source
1 REPO @R1@
0 @I1@ INDI
1 SOUR @S1@
0 TRLR
"""

    def test_name(self):
        g = _parse(self._TEXT)
        assert repository_detail(g["REPO"][0]).name == "City Library"

    def test_address(self):
        g = _parse(self._TEXT)
        assert repository_detail(g["REPO"][0]).address == "123 Main St"

    def test_phone(self):
        g = _parse(self._TEXT)
        assert repository_detail(g["REPO"][0]).phone == "555-1234"

    def test_email(self):
        g = _parse(self._TEXT)
        assert repository_detail(g["REPO"][0]).email == "library@example.com"

    def test_website(self):
        g = _parse(self._TEXT)
        assert repository_detail(g["REPO"][0]).website == "https://example.com"


# ---------------------------------------------------------------------------
# SharedNoteDetail
# ---------------------------------------------------------------------------

class TestSharedNoteDetail:
    _TEXT = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @N1@ SNOTE This is a shared note.
1 CONT Second paragraph.
1 MIME text/plain
1 LANG en
0 @I1@ INDI
1 SNOTE @N1@
0 TRLR
"""

    def test_text(self):
        g = _parse(self._TEXT)
        detail = shared_note_detail(g["SNOTE"][0])
        assert "This is a shared note." in detail.text
        assert "Second paragraph." in detail.text

    def test_mime(self):
        g = _parse(self._TEXT)
        assert shared_note_detail(g["SNOTE"][0]).mime == "text/plain"

    def test_language(self):
        g = _parse(self._TEXT)
        assert shared_note_detail(g["SNOTE"][0]).language == "en"


# ---------------------------------------------------------------------------
# SubmitterDetail
# ---------------------------------------------------------------------------

class TestSubmitterDetail:
    _TEXT = """\
0 HEAD
1 GEDC
2 VERS 7.0
1 SUBM @SM1@
0 @SM1@ SUBM
1 NAME Jane Researcher
1 EMAIL jane@example.com
1 LANG en
0 TRLR
"""

    def test_name(self):
        g = _parse(self._TEXT)
        assert submitter_detail(g["SUBM"][0]).name == "Jane Researcher"

    def test_email(self):
        g = _parse(self._TEXT)
        assert submitter_detail(g["SUBM"][0]).email == "jane@example.com"

    def test_language(self):
        g = _parse(self._TEXT)
        assert submitter_detail(g["SUBM"][0]).language == "en"


# ---------------------------------------------------------------------------
# IndividualDetail.last_changed
# ---------------------------------------------------------------------------

class TestLastChanged:
    _TEXT = """\
0 HEAD
1 GEDC
2 VERS 7.0
0 @I1@ INDI
1 NAME Alice /Smith/
1 CHAN
2 DATE 1 JAN 2020
0 TRLR
"""

    def test_last_changed(self):
        assert _indi(self._TEXT).last_changed == "1 JAN 2020"
