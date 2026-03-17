"""
Tests for gedcomtools.gedcomx.name — Name, NameForm, NamePart, QuickName
"""
import pytest
from gedcomtools.gedcomx.name import (
    Name, NameForm, NamePart, NameType, NamePartType, NamePartQualifier, QuickName
)


class TestNamePart:
    def test_basic(self):
        part = NamePart(type=NamePartType.Given, value="John")
        assert part.value == "John"
        assert part.type == NamePartType.Given

    def test_equality(self):
        p1 = NamePart(type=NamePartType.Surname, value="Smith")
        p2 = NamePart(type=NamePartType.Surname, value="Smith")
        assert p1 == p2

    def test_inequality_different_value(self):
        p1 = NamePart(type=NamePartType.Given, value="John")
        p2 = NamePart(type=NamePartType.Given, value="Jane")
        assert p1 != p2

    def test_inequality_different_type(self):
        p1 = NamePart(type=NamePartType.Given, value="John")
        p2 = NamePart(type=NamePartType.Surname, value="John")
        assert p1 != p2

    def test_str(self):
        part = NamePart(type=NamePartType.Given, value="John")
        assert "John" in str(part)

    def test_with_qualifier(self):
        part = NamePart(
            type=NamePartType.Given,
            value="John",
            qualifiers=[NamePartQualifier.Primary]
        )
        assert part.qualifiers is not None


class TestNameForm:
    def test_basic(self):
        nf = NameForm(fullText="John Smith")
        assert nf.fullText == "John Smith"

    def test_with_parts(self):
        nf = NameForm(
            fullText="John Smith",
            parts=[
                NamePart(type=NamePartType.Given, value="John"),
                NamePart(type=NamePartType.Surname, value="Smith"),
            ]
        )
        assert len(nf.parts) == 2

    def test_with_lang(self):
        nf = NameForm(fullText="Jean Dupont", lang="fr")
        assert nf.lang == "fr"


class TestNameSimple:
    def test_simple_full_name(self):
        n = Name.simple("John Smith")
        assert n is not None
        assert isinstance(n, Name)

    def test_simple_has_name_form(self):
        n = Name.simple("John Smith")
        assert len(n.nameForms) >= 1

    def test_simple_has_given_and_surname(self):
        n = Name.simple("John Smith")
        nf = n.nameForms[0]
        types = [p.type for p in nf.parts]
        assert NamePartType.Given in types
        assert NamePartType.Surname in types

    def test_simple_given_value(self):
        n = Name.simple("John Smith")
        nf = n.nameForms[0]
        given = next(p for p in nf.parts if p.type == NamePartType.Given)
        assert given.value == "John"

    def test_simple_surname_value(self):
        n = Name.simple("John Smith")
        nf = n.nameForms[0]
        surname = next(p for p in nf.parts if p.type == NamePartType.Surname)
        assert surname.value == "Smith"

    def test_simple_single_name(self):
        n = Name.simple("Madonna")
        nf = n.nameForms[0]
        types = [p.type for p in nf.parts]
        assert NamePartType.Given in types
        assert NamePartType.Surname not in types

    # --- GEDCOM slash notation ---

    def test_slash_surname(self):
        n = Name.simple("John /Smith/")
        nf = n.nameForms[0]
        types = [p.type for p in nf.parts]
        assert NamePartType.Given in types
        assert NamePartType.Surname in types

    def test_slash_surname_value(self):
        n = Name.simple("John /Smith/")
        nf = n.nameForms[0]
        surname = next(p for p in nf.parts if p.type == NamePartType.Surname)
        assert surname.value == "Smith"

    def test_slash_given_value(self):
        n = Name.simple("John /Smith/")
        nf = n.nameForms[0]
        given = next(p for p in nf.parts if p.type == NamePartType.Given)
        assert given.value == "John"

    def test_slash_multiword_given(self):
        n = Name.simple("John Robert /Smith/")
        nf = n.nameForms[0]
        given = next(p for p in nf.parts if p.type == NamePartType.Given)
        assert given.value == "John Robert"

    def test_slash_compound_surname(self):
        n = Name.simple("John /van der Berg/")
        nf = n.nameForms[0]
        surname = next(p for p in nf.parts if p.type == NamePartType.Surname)
        assert surname.value == "van der Berg"

    def test_slash_with_suffix(self):
        n = Name.simple("John /Smith/ Jr.")
        nf = n.nameForms[0]
        types = [p.type for p in nf.parts]
        assert NamePartType.Suffix in types
        suffix = next(p for p in nf.parts if p.type == NamePartType.Suffix)
        assert suffix.value == "Jr."

    def test_slash_surname_only(self):
        n = Name.simple("/Smith/")
        nf = n.nameForms[0]
        types = [p.type for p in nf.parts]
        assert NamePartType.Surname in types
        assert NamePartType.Given not in types

    def test_slash_fulltext_has_no_slashes(self):
        n = Name.simple("John /Smith/")
        assert "/" not in n.nameForms[0].fullText

    def test_empty_string_returns_empty_name(self):
        n = Name.simple("")
        assert n is not None
        assert isinstance(n, Name)


class TestQuickName:
    def test_creates_name(self):
        n = QuickName("John Smith")
        assert isinstance(n, Name)

    def test_full_text_set(self):
        n = QuickName("John Smith")
        assert n.nameForms[0].fullText == "John Smith"


class TestNameConstruction:
    def test_birth_name_type(self):
        n = Name(type=NameType.BirthName, nameForms=[NameForm(fullText="John Smith")])
        assert n.type == NameType.BirthName

    def test_no_args(self):
        n = Name()
        assert n.nameForms == []

    def test_mutable_default_independence(self):
        """Regression: two Name instances must not share nameForms list."""
        n1 = Name()
        n2 = Name()
        n1.nameForms.append(NameForm(fullText="Test"))
        assert len(n2.nameForms) == 0

    def test_add_name_part(self):
        n = Name(nameForms=[NameForm(fullText="John")])
        part = NamePart(type=NamePartType.Given, value="John")
        n._add_name_part(part)
        assert part in n.nameForms[0].parts
