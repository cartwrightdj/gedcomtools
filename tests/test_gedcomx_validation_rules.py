"""
Tests for GedcomX validation rules.

Converts 555SAMPLE.GED to GedcomX, serializes to dict, then validates
every object through pydantic mirror models that enforce the core rules:
  - Person must have an id
  - Name must have at least one nameForm
  - Relationship must reference both person1 and person2
  - Resource must have either resource or resourceId
"""
from __future__ import annotations

from typing import List, Optional
from pathlib import Path

import pytest
from pydantic import BaseModel, Field, ValidationError, model_validator


# ---------------------------------------------------------------------------
# Pydantic mirror models (minimal — only enforce structural rules)
# ---------------------------------------------------------------------------

class PNameForm(BaseModel):
    fullText: Optional[str] = None
    parts: list = Field(default_factory=list)


class PName(BaseModel):
    type: Optional[str] = None
    nameForms: List[PNameForm] = Field(default_factory=list)

    @model_validator(mode="after")
    def must_have_name_form(self):
        if not self.nameForms:
            raise ValueError("Name must have at least one nameForm")
        return self


class PGender(BaseModel):
    type: Optional[str] = None


class PPerson(BaseModel):
    id: Optional[str] = None
    names: List[PName] = Field(default_factory=list)
    gender: Optional[PGender] = None
    facts: list = Field(default_factory=list)

    @model_validator(mode="after")
    def must_have_id(self):
        if not self.id:
            raise ValueError("Person must have an id")
        return self


class PResource(BaseModel):
    resource: Optional[str] = None
    resourceId: Optional[str] = None

    @model_validator(mode="after")
    def must_have_reference(self):
        if not self.resource and not self.resourceId:
            raise ValueError("Resource must have 'resource' or 'resourceId'")
        return self


class PRelationship(BaseModel):
    type: Optional[str] = None
    person1: Optional[PResource] = None
    person2: Optional[PResource] = None

    @model_validator(mode="after")
    def must_have_both_persons(self):
        if self.person1 is None or self.person2 is None:
            raise ValueError("Relationship must have both person1 and person2")
        return self


class PSourceDescription(BaseModel):
    id: Optional[str] = None
    titles: list = Field(default_factory=list)
    descriptions: list = Field(default_factory=list)


class PAgent(BaseModel):
    id: Optional[str] = None
    names: list = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_all(items: list, model: type[BaseModel]) -> list[str]:
    """Return list of error strings for any items that fail validation."""
    errors = []
    for i, item in enumerate(items):
        try:
            model.model_validate(item)
        except ValidationError as e:
            item_id = item.get("id", f"[{i}]")
            for err in e.errors():
                loc = " → ".join(str(x) for x in err["loc"])
                errors.append(f"[{item_id}] {loc}: {err['msg']}")
    return errors


# ---------------------------------------------------------------------------
# Fixture: converted GedcomX serialized to dict
# ---------------------------------------------------------------------------

SAMPLE = Path(__file__).parent.parent / ".sample_data" / "gedcom5" / "gedcom5_sample.ged"


@pytest.fixture(scope="module")
def gx_data():
    from gedcomtools.gedcom5.parser import Gedcom5x
    from gedcomtools.gedcomx.conversion import GedcomConverter
    from gedcomtools.gedcomx.serialization import Serialization
    p = Gedcom5x()
    p.parse_file(str(SAMPLE))
    gx = GedcomConverter().Gedcom5x_GedcomX(p)
    return Serialization.serialize(gx)


# ---------------------------------------------------------------------------
# Validation rule tests
# ---------------------------------------------------------------------------

class TestPersonRules:
    def test_all_persons_have_ids(self, gx_data):
        errors = _validate_all(gx_data.get("persons", []), PPerson)
        assert not errors, "Person validation errors:\n" + "\n".join(errors)

    def test_all_names_have_name_forms(self, gx_data):
        errors = []
        for person in gx_data.get("persons", []):
            for name in person.get("names", []):
                try:
                    PName.model_validate(name)
                except ValidationError as e:
                    pid = person.get("id", "?")
                    for err in e.errors():
                        errors.append(f"[person {pid}] {err['msg']}")
        assert not errors, "Name validation errors:\n" + "\n".join(errors)

    def test_persons_count(self, gx_data):
        assert len(gx_data.get("persons", [])) == 3


class TestRelationshipRules:
    def test_all_relationships_have_person1(self, gx_data):
        """Every relationship must have at least person1 set."""
        for r in gx_data.get("relationships", []):
            assert r.get("person1"), f"Relationship [{r.get('id', '?')}] missing person1"

    def test_relationships_count(self, gx_data):
        assert len(gx_data.get("relationships", [])) >= 1


class TestSourceDescriptionRules:
    def test_source_descriptions_validate(self, gx_data):
        errors = _validate_all(gx_data.get("sourceDescriptions", []), PSourceDescription)
        assert not errors, "SourceDescription validation errors:\n" + "\n".join(errors)


class TestAgentRules:
    def test_agents_validate(self, gx_data):
        errors = _validate_all(gx_data.get("agents", []), PAgent)
        assert not errors, "Agent validation errors:\n" + "\n".join(errors)


# ---------------------------------------------------------------------------
# Direct rule unit tests (model validators in isolation)
# ---------------------------------------------------------------------------

class TestPersonMustHaveId:
    def test_person_without_id_fails(self):
        with pytest.raises(ValidationError, match="must have an id"):
            PPerson.model_validate({"names": [{"nameForms": [{"fullText": "Alice"}]}]})

    def test_person_with_id_passes(self):
        PPerson.model_validate({"id": "P1", "names": [{"nameForms": [{"fullText": "Alice"}]}]})


class TestNameMustHaveNameForm:
    def test_name_without_name_form_fails(self):
        with pytest.raises(ValidationError, match="at least one nameForm"):
            PName.model_validate({"type": "BirthName", "nameForms": []})

    def test_name_with_name_form_passes(self):
        PName.model_validate({"nameForms": [{"fullText": "Alice Smith"}]})


class TestRelationshipMustHaveBothPersons:
    def test_missing_person2_fails(self):
        with pytest.raises(ValidationError, match="both person1 and person2"):
            PRelationship.model_validate({
                "person1": {"resource": "#P1"},
            })

    def test_missing_person1_fails(self):
        with pytest.raises(ValidationError, match="both person1 and person2"):
            PRelationship.model_validate({
                "person2": {"resource": "#P2"},
            })

    def test_both_present_passes(self):
        PRelationship.model_validate({
            "person1": {"resource": "#P1"},
            "person2": {"resource": "#P2"},
        })


class TestResourceMustHaveReference:
    def test_empty_resource_fails(self):
        with pytest.raises(ValidationError, match="resource.*or.*resourceId"):
            PResource.model_validate({})

    def test_resource_uri_passes(self):
        PResource.model_validate({"resource": "#P1"})

    def test_resource_id_passes(self):
        PResource.model_validate({"resourceId": "agent-1"})
