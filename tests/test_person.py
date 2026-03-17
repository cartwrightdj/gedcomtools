"""
Tests for gedcomtools.gedcomx.person.Person and QuickPerson
"""
import pytest
from gedcomtools.gedcomx.person import Person, QuickPerson
from gedcomtools.gedcomx.fact import Fact, FactType
from gedcomtools.gedcomx.name import Name, NameForm, NameType, QuickName
from gedcomtools.gedcomx.gender import Gender, GenderType


class TestPersonConstruction:
    def test_no_args(self):
        p = Person()
        assert p.id is not None  # Person auto-generates an id
        assert p.names == []
        assert p.facts == []

    def test_with_id(self):
        p = Person(id="P1")
        assert p.id == "P1"

    def test_mutable_defaults_independent(self):
        """Regression: mutable default args must not be shared across instances."""
        p1 = Person()
        p2 = Person()
        p1.names.append(QuickName("John Smith"))
        assert len(p2.names) == 0

    def test_names_list_independent(self):
        p1 = Person()
        p2 = Person()
        p1.facts.append(Fact(type=FactType.Birth))
        assert len(p2.facts) == 0


class TestPersonAddFact:
    def test_add_fact_returns_true(self):
        p = Person()
        f = Fact(type=FactType.Birth)
        assert p.add_fact(f) is True

    def test_add_fact_appended(self):
        p = Person()
        f = Fact(type=FactType.Birth)
        p.add_fact(f)
        assert f in p.facts

    def test_add_duplicate_fact_returns_false(self):
        p = Person()
        f = Fact(type=FactType.Birth)
        p.add_fact(f)
        assert p.add_fact(f) is False

    def test_add_duplicate_fact_not_doubled(self):
        p = Person()
        f = Fact(type=FactType.Birth)
        p.add_fact(f)
        p.add_fact(f)
        assert p.facts.count(f) == 1

    def test_add_none_returns_false(self):
        p = Person()
        assert p.add_fact(None) is False

    def test_add_wrong_type_returns_false(self):
        p = Person()
        assert p.add_fact("not a fact") is False


class TestPersonAddName:
    def test_add_name_returns_true(self):
        p = Person()
        n = QuickName("John Smith")
        assert p.add_name(n) is True

    def test_add_name_appended(self):
        p = Person()
        n = QuickName("John Smith")
        p.add_name(n)
        assert n in p.names

    def test_add_duplicate_name_returns_false(self):
        p = Person()
        n = QuickName("John Smith")
        p.add_name(n)
        assert p.add_name(n) is False

    def test_add_more_than_five_names_does_not_crash(self):
        """Regression: add_name() must not crash when more than 5 names are added.

        Name inherits Conclusion.__eq__ which compares id/lang/sources etc. but
        not nameForms, so names without explicit ids compare equal.  Give each
        name a unique id to make them distinct.
        """
        p = Person()
        for i in range(10):
            n = Name(id=f"N{i}", nameForms=[NameForm(fullText=f"Name{i}")])
            result = p.add_name(n)
            assert result is True, f"Expected True for name {i}, got False"
        assert len(p.names) == 10

    def test_add_name_none_returns_false(self):
        p = Person()
        assert p.add_name(None) is False

    def test_add_name_wrong_type_returns_false(self):
        p = Person()
        assert p.add_name("not a name") is False


class TestPersonNameProperty:
    def test_name_property_returns_fulltext(self):
        p = Person()
        p.add_name(QuickName("Alice Wonder"))
        assert p.name == "Alice Wonder"

    def test_name_property_returns_none_when_no_names(self):
        """Regression: name property must return None when names list is empty."""
        p = Person()
        assert p.name is None

    def test_name_property_returns_none_when_nameform_missing(self):
        """name property must return None when Name has no nameForms."""
        p = Person()
        bare_name = Name()  # no nameForms
        p.names.append(bare_name)
        assert p.name is None


class TestPersonGender:
    def test_set_gender(self):
        p = Person(gender=Gender(type=GenderType.Male))
        assert p.gender.type == GenderType.Male

    def test_default_gender_none(self):
        p = Person()
        assert p.gender is None


class TestQuickPerson:
    def test_creates_person(self):
        p = QuickPerson("John Smith")
        assert isinstance(p, Person)

    def test_has_name(self):
        p = QuickPerson("John Smith")
        assert len(p.names) >= 1

    def test_name_contains_text(self):
        p = QuickPerson("John Smith")
        full = p.names[0].nameForms[0].fullText
        assert "John" in full or "Smith" in full

    def test_with_birth_date(self):
        p = QuickPerson("John Smith", dob="1900-01-01")
        birth_facts = [f for f in p.facts if f.type == FactType.Birth]
        assert len(birth_facts) >= 1

    def test_with_death_date(self):
        p = QuickPerson("John Smith", dod="1980-06-15")
        death_facts = [f for f in p.facts if f.type == FactType.Death]
        assert len(death_facts) >= 1

    def test_independent_instances(self):
        p1 = QuickPerson("Alice")
        p2 = QuickPerson("Bob")
        p1.add_fact(Fact(type=FactType.Residence))
        death_in_p2 = [f for f in p2.facts if f.type == FactType.Residence]
        assert len(death_in_p2) == 0
