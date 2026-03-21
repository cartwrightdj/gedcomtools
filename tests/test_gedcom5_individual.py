"""
Tests for IndividualRecord API (gedcom5.elements).

Exercises every key method on individuals parsed from 555SAMPLE.GED,
which has 3 individuals with known birth/death data.
"""
from __future__ import annotations

import pytest
from pathlib import Path
from gedcomtools.gedcom5.parser import Gedcom5x

SAMPLE = Path(__file__).parent.parent / ".sample_data" / "gedcom5" / "gedcom5_sample.ged"


@pytest.fixture(scope="module")
def individuals():
    p = Gedcom5x()
    p.parse_file(str(SAMPLE))
    return p.individuals


@pytest.fixture(scope="module")
def first(individuals):
    return individuals[0]


# ---------------------------------------------------------------------------
# Basic record identity
# ---------------------------------------------------------------------------

class TestTag:
    def test_tag_is_indi(self, first):
        assert first.get_tag() == "INDI"

    def test_all_individuals_have_indi_tag(self, individuals):
        for i in individuals:
            assert i.get_tag() == "INDI"


# ---------------------------------------------------------------------------
# Names
# ---------------------------------------------------------------------------

class TestNames:
    def test_get_name_returns_tuple(self, first):
        name = first.get_name()
        assert isinstance(name, tuple)
        assert len(name) == 2

    def test_get_name_given_and_surname(self, first):
        given, surname = first.get_name()
        assert isinstance(given, str)
        assert isinstance(surname, str)
        assert len(given) > 0
        assert len(surname) > 0

    def test_get_all_names_is_list(self, first):
        names = first.get_all_names()
        assert isinstance(names, list)
        assert len(names) >= 1

    def test_all_individuals_have_names(self, individuals):
        for i in individuals:
            given, surname = i.get_name()
            assert given or surname


# ---------------------------------------------------------------------------
# Gender
# ---------------------------------------------------------------------------

class TestGender:
    def test_gender_is_string(self, first):
        g = first.get_gender()
        assert g in ("M", "F", "U", None)

    def test_first_individual_is_male(self, first):
        assert first.get_gender() == "M"


# ---------------------------------------------------------------------------
# Birth data
# ---------------------------------------------------------------------------

class TestBirth:
    def test_birth_data_not_none(self, first):
        assert first.get_birth_data() is not None

    def test_birth_year_is_int(self, first):
        year = first.get_birth_year()
        assert isinstance(year, int)

    def test_birth_year_value(self, first):
        assert first.get_birth_year() == 1822

    def test_birth_year_match_correct_year(self, first):
        assert first.birth_year_match(1822)

    def test_birth_year_match_wrong_year(self, first):
        assert not first.birth_year_match(1900)

    def test_birth_range_match_inclusive(self, first):
        assert first.birth_range_match(1800, 1900)

    def test_birth_range_match_outside(self, first):
        assert not first.birth_range_match(1900, 2000)


# ---------------------------------------------------------------------------
# Death data
# ---------------------------------------------------------------------------

class TestDeath:
    def test_death_data_not_none(self, first):
        assert first.get_death_data() is not None

    def test_death_year_is_int(self, first):
        year = first.get_death_year()
        assert isinstance(year, int)

    def test_death_year_value(self, first):
        assert first.get_death_year() == 1905

    def test_death_year_match(self, first):
        assert first.death_year_match(1905)

    def test_death_range_match(self, first):
        assert first.death_range_match(1900, 1910)

    def test_is_deceased(self, first):
        assert first.is_deceased()


# ---------------------------------------------------------------------------
# Other record flags
# ---------------------------------------------------------------------------

class TestFlags:
    def test_is_child_returns_bool(self, first):
        result = first.is_child()
        assert isinstance(result, bool)

    def test_is_private_returns_bool(self, first):
        result = first.is_private()
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Optional fields — just confirm they don't raise
# ---------------------------------------------------------------------------

class TestOptionalFields:
    def test_burial_data_does_not_raise(self, first):
        first.get_burial_data()

    def test_census_data_does_not_raise(self, first):
        first.get_census_data()

    def test_last_change_date_does_not_raise(self, first):
        first.get_last_change_date()

    def test_occupation_does_not_raise(self, first):
        first.get_occupation()

    def test_describe_does_not_raise(self, first):
        first.describe()
