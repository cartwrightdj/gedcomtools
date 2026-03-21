"""
Tests for the FamilySearch AdditionalAttribution GedcomX extension.

Covers:
- Class structure (inherits Attribution, adds id)
- All Attribution fields accessible
- changeMessageResource field (added to base Attribution)
- additionalAttributions registered on Conclusion and all subclasses
- Validation passes / catches bad input
- Serialization via model_dump
- Integration via import_plugins
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def aa_cls():
    from gedcomtools.gedcomx.extensions.fs.additional_attribution import AdditionalAttribution
    return AdditionalAttribution


# ---------------------------------------------------------------------------
# Class structure
# ---------------------------------------------------------------------------

class TestAdditionalAttributionClass:
    def test_is_attribution_subclass(self, aa_cls):
        from gedcomtools.gedcomx.attribution import Attribution
        assert issubclass(aa_cls, Attribution)

    def test_is_gedcomx_model(self, aa_cls):
        from gedcomtools.gedcomx.gx_base import GedcomXModel
        assert issubclass(aa_cls, GedcomXModel)

    def test_identifier_uri(self, aa_cls):
        assert aa_cls.identifier == "http://familysearch.org/v1/AdditionalAttribution"

    def test_has_id_field(self, aa_cls):
        assert "id" in aa_cls.model_fields

    def test_inherited_fields_present(self, aa_cls):
        for field in ("contributor", "modified", "changeMessage",
                      "changeMessageResource", "creator", "created"):
            assert field in aa_cls.model_fields, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestAdditionalAttributionConstruction:
    def test_empty_construction(self, aa_cls):
        aa = aa_cls()
        assert aa.id is None
        assert aa.changeMessage is None

    def test_id_only(self, aa_cls):
        aa = aa_cls(id="aa-1")
        assert aa.id == "aa-1"

    def test_full_construction(self, aa_cls):
        aa = aa_cls(
            id="aa-1",
            changeMessage="Imported from legacy system",
            changeMessageResource="https://example.com/changes/1",
        )
        assert aa.id == "aa-1"
        assert aa.changeMessage == "Imported from legacy system"
        assert aa.changeMessageResource == "https://example.com/changes/1"

    def test_contributor_accepted(self, aa_cls):
        from gedcomtools.gedcomx.resource import Resource
        aa = aa_cls(contributor=Resource(resourceId="agent-1"))
        assert aa.contributor is not None

    def test_creator_accepted(self, aa_cls):
        from gedcomtools.gedcomx.resource import Resource
        aa = aa_cls(creator=Resource(resourceId="agent-2"))
        assert aa.creator is not None

    def test_change_message_resource(self, aa_cls):
        aa = aa_cls(changeMessageResource="https://example.com/log/42")
        assert aa.changeMessageResource == "https://example.com/log/42"


# ---------------------------------------------------------------------------
# Attribution base — changeMessageResource field
# ---------------------------------------------------------------------------

class TestAttributionChangeMessageResource:
    def test_field_on_attribution(self):
        from gedcomtools.gedcomx.attribution import Attribution
        assert "changeMessageResource" in Attribution.model_fields

    def test_attribution_stores_value(self):
        from gedcomtools.gedcomx.attribution import Attribution
        a = Attribution(changeMessageResource="https://example.com/msg")
        assert a.changeMessageResource == "https://example.com/msg"

    def test_attribution_default_none(self):
        from gedcomtools.gedcomx.attribution import Attribution
        a = Attribution()
        assert a.changeMessageResource is None


# ---------------------------------------------------------------------------
# Registration on Conclusion and subclasses
# ---------------------------------------------------------------------------

class TestAdditionalAttributionsRegistration:
    def test_on_conclusion(self):
        from gedcomtools.gedcomx.conclusion import Conclusion
        assert "additionalAttributions" in Conclusion.model_fields

    def test_on_person(self):
        from gedcomtools.gedcomx.person import Person
        assert "additionalAttributions" in Person.model_fields

    def test_on_relationship(self):
        from gedcomtools.gedcomx.relationship import Relationship
        assert "additionalAttributions" in Relationship.model_fields

    def test_on_fact(self):
        from gedcomtools.gedcomx.fact import Fact
        assert "additionalAttributions" in Fact.model_fields

    def test_person_accepts_list(self, aa_cls):
        from gedcomtools.gedcomx.person import Person
        p = Person(
            id="P1",
            additionalAttributions=[
                aa_cls(id="aa-1", changeMessage="First editor"),
                aa_cls(id="aa-2", changeMessage="Second editor"),
            ],
        )
        assert len(p.additionalAttributions) == 2
        assert p.additionalAttributions[0].id == "aa-1"
        assert p.additionalAttributions[1].changeMessage == "Second editor"

    def test_person_default_empty_list(self):
        from gedcomtools.gedcomx.person import Person
        p = Person(id="P1")
        assert p.additionalAttributions is None or p.additionalAttributions == []

    def test_fact_accepts_list(self, aa_cls):
        from gedcomtools.gedcomx.fact import Fact, FactType
        f = Fact(
            type=FactType.Birth,
            additionalAttributions=[aa_cls(id="aa-x", changeMessage="birth import")],
        )
        assert f.additionalAttributions[0].id == "aa-x"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestAdditionalAttributionValidation:
    def test_empty_passes(self, aa_cls):
        aa = aa_cls()
        result = aa.validate()
        assert not result.errors

    def test_full_passes(self, aa_cls):
        aa = aa_cls(
            id="aa-1",
            changeMessage="Imported",
            changeMessageResource="https://example.com/changes/1",
        )
        result = aa.validate()
        assert not result.errors

    def test_whitespace_id_warns(self, aa_cls):
        """Blank id string should generate a validation warning."""
        aa = aa_cls(id="   ")
        result = aa.validate()
        # check_nonempty issues a warning for whitespace-only strings
        assert result.warnings or result.errors  # at least one issue

    def test_whitespace_change_message_resource_warns(self, aa_cls):
        aa = aa_cls(changeMessageResource="  ")
        result = aa.validate()
        assert result.warnings or result.errors


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

class TestAdditionalAttributionSerialization:
    def test_model_dump_excludes_none(self, aa_cls):
        aa = aa_cls(id="aa-1", changeMessage="test")
        d = aa.model_dump(exclude_none=True)
        assert d["id"] == "aa-1"
        assert d["changeMessage"] == "test"
        assert "contributor" not in d

    def test_model_dump_includes_change_message_resource(self, aa_cls):
        aa = aa_cls(changeMessageResource="https://example.com/c/1")
        d = aa.model_dump(exclude_none=True)
        assert d["changeMessageResource"] == "https://example.com/c/1"

    def test_person_dump_includes_additional_attributions(self, aa_cls):
        from gedcomtools.gedcomx.person import Person
        p = Person(
            id="P1",
            additionalAttributions=[aa_cls(id="aa-1", changeMessage="edit")],
        )
        d = p.model_dump(exclude_none=True)
        assert "additionalAttributions" in d
        assert d["additionalAttributions"][0]["id"] == "aa-1"


# ---------------------------------------------------------------------------
# String representations
# ---------------------------------------------------------------------------

class TestAdditionalAttributionStr:
    def test_str_contains_class_name(self, aa_cls):
        aa = aa_cls(id="aa-1")
        assert "AdditionalAttribution" in str(aa)

    def test_str_contains_id(self, aa_cls):
        aa = aa_cls(id="aa-99")
        assert "aa-99" in str(aa)

    def test_repr_contains_class_name(self, aa_cls):
        aa = aa_cls(id="aa-1")
        assert "AdditionalAttribution" in repr(aa)

    def test_repr_contains_all_field_names(self, aa_cls):
        aa = aa_cls()
        r = repr(aa)
        for field in ("id", "contributor", "modified", "changeMessage",
                      "changeMessageResource", "creator", "created"):
            assert field in r, f"repr missing field: {field}"


# ---------------------------------------------------------------------------
# Import via plugin system
# ---------------------------------------------------------------------------

class TestPluginLoading:
    def test_no_errors_on_load(self):
        from gedcomtools.gedcomx.extensible import import_plugins
        result = import_plugins("gedcomx")
        assert result["errors"] == {}

    def test_fs_package_loaded(self):
        from gedcomtools.gedcomx.extensible import import_plugins
        result = import_plugins("gedcomx")
        assert any("fs" in m for m in result["imported"])
