"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/person.py
 Author:  David J. Cartwright
 Purpose: GedcomX Person model with facts, names, gender, and display helpers

 Created: 2025-08-25
 Updated:
   - 2026-04-08: add typed FamilySearch display alias handling with
                 deserialized-first, computed-fallback display data;
                 coerce FamilySearch PersonInfo extension items
======================================================================
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, List, Optional

from pydantic import Field, PrivateAttr, model_validator

from .fact import Fact, FactType
from .gender import Gender
from .name import Name, QuickName
from .subject import Subject

from ..glog import get_logger

log = get_logger(__name__)

if TYPE_CHECKING:
    from .extensions.fs.fs_types_rs import DisplayProperties


class Person(Subject):
    """A person in the GedcomX model."""

    identifier: ClassVar[str] = "http://gedcomx.org/v1/Person"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    _relationships: List[Any] = PrivateAttr(default_factory=list)

    private: Optional[bool] = None
    gender: Optional[Gender] = None
    names: List[Name] = Field(default_factory=list)
    facts: List[Fact] = Field(default_factory=list)
    living: Optional[bool] = None
    displayProperties: Optional[Any] = Field(default=None, alias="display")

    @model_validator(mode="before")
    @classmethod
    def _coerce_display_alias(cls, value: Any) -> Any:
        """Normalize incoming FamilySearch `display` payloads to the typed field."""
        if isinstance(value, dict) and "displayProperties" in value and "display" not in value:
            value = dict(value)
            value["display"] = value.pop("displayProperties")
        return value

    @model_validator(mode="after")
    def _coerce_display_properties(self) -> "Person":
        """Coerce aliased display payloads into typed FamilySearch display properties when available."""
        if isinstance(self.displayProperties, dict):
            try:
                from .extensions.fs.fs_types_rs import DisplayProperties
                self.displayProperties = DisplayProperties.model_validate(self.displayProperties)
            except Exception:
                pass
        if isinstance(getattr(self, "personInfo", None), list):
            try:
                from .extensions.fs.fs_types_core import PersonInfo
                self.personInfo = [  # pylint: disable=attribute-defined-outside-init
                    PersonInfo.model_validate(item) if isinstance(item, dict) else item
                    for item in self.personInfo
                ]
            except Exception:
                pass
        return self

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_instance
        if not self.names:
            result.warn("names", "Person has no names")
        check_instance(result, "gender", self.gender, Gender)
        if self.private is not None and not isinstance(self.private, bool):
            result.error("private", f"Expected bool, got {type(self.private).__name__}")
        if self.living is not None and not isinstance(self.living, bool):
            result.error("living", f"Expected bool, got {type(self.living).__name__}")
        for i, n in enumerate(self.names):
            check_instance(result, f"names[{i}]", n, Name)
        for i, f_ in enumerate(self.facts):
            check_instance(result, f"facts[{i}]", f_, Fact)

    def add_fact(self, fact_to_add: Fact) -> bool:
        """Add a Fact to this person, skipping duplicates.  Returns True if the fact was added."""
        if fact_to_add and isinstance(fact_to_add, Fact):
            for current in self.facts:
                if fact_to_add == current:
                    return False
            self.facts.append(fact_to_add)
            return True
        return False

    def add_name(self, name_to_add: Name) -> bool:
        """Add a Name to this person, skipping duplicates.  Returns True if the name was added."""
        if name_to_add and isinstance(name_to_add, Name):
            for current in self.names:
                if name_to_add == current:
                    return False
            self.names.append(name_to_add)
            return True
        return False

    def _add_relationship(self, relationship_to_add: Any) -> None:
        from .relationship import Relationship
        if isinstance(relationship_to_add, Relationship):
            self._relationships.append(relationship_to_add)
        else:
            raise ValueError("Expected a Relationship instance")

    @staticmethod
    def _gender_display_value(gender: Optional[Gender]) -> Optional[str]:
        """Return a human-friendly gender label from a GedcomX gender conclusion."""
        if gender is None or gender.type is None:
            return None
        value = getattr(gender.type, "value", str(gender.type))
        if value.endswith("/Male"):
            return "Male"
        if value.endswith("/Female"):
            return "Female"
        return value.rsplit("/", maxsplit=1)[-1]

    @staticmethod
    def _date_display_value(fact: Fact) -> Optional[str]:
        """Prefer original date text, then normalized text, then the formal value."""
        if fact.date is None:
            return None
        if fact.date.original:
            return fact.date.original
        if fact.date.normalized:
            return fact.date.normalized[0].value
        return fact.date.formal

    @staticmethod
    def _place_display_value(fact: Fact) -> Optional[str]:
        """Prefer original place text, then normalized text."""
        if fact.place is None:
            return None
        if fact.place.original:
            return fact.place.original
        if fact.place.normalized:
            return fact.place.normalized[0].value
        return None

    def _computed_display_properties(self):
        """Build display properties from the current person facts and names."""
        from .extensions.fs.fs_types_rs import DisplayProperties

        try:
            name_text = self.names[0].nameForms[0].fullText
        except (IndexError, AttributeError):
            name_text = None

        birth_date: Optional[str] = None
        birth_place: Optional[str] = None
        death_date: Optional[str] = None
        death_place: Optional[str] = None
        for fact in self.facts:
            if fact.type == FactType.Birth:
                birth_date = self._date_display_value(fact)
                birth_place = self._place_display_value(fact)
            elif fact.type == FactType.Death:
                death_date = self._date_display_value(fact)
                death_place = self._place_display_value(fact)

        if birth_date and death_date:
            lifespan = f"{birth_date}-{death_date}"
        elif birth_date:
            lifespan = f"{birth_date}-"
        elif death_date:
            lifespan = f"-{death_date}"
        else:
            lifespan = None

        return DisplayProperties(
            birthDate=birth_date,
            birthPlace=birth_place,
            deathDate=death_date,
            deathPlace=death_place,
            gender=self._gender_display_value(self.gender),
            lifespan=lifespan,
            name=name_text,
        )

    def display_object(self):
        """Return typed display data, preferring deserialized values and filling gaps from the person."""
        computed = self._computed_display_properties()
        if self.displayProperties is None:
            return computed

        display = self.displayProperties.model_copy(deep=True)
        for field_name, value in computed.model_dump(exclude_none=True).items():
            if getattr(display, field_name, None) is None:
                setattr(display, field_name, value)
        return display

    def ensure_display_properties(self) -> "DisplayProperties":
        """Materialize display properties from current person data."""
        from .extensions.fs.fs_types_rs import DisplayProperties
        self.displayProperties = self.display_object()
        if self.displayProperties is None:
            self.displayProperties = DisplayProperties()
        return self.displayProperties

    def display(self) -> dict:
        """Return display data, preferring FamilySearch JSON values and falling back to computed ones."""
        return self.display_object().model_dump(exclude_none=False)

    @property
    def name(self) -> str | None:
        """Return the full text of the primary name form, or None if unavailable."""
        try:
            return self.names[0].nameForms[0].fullText
        except (IndexError, AttributeError) as e:
            log.debug("Person {}: .name unavailable — {}", self.id, e)
            return None


class QuickPerson:
    """Convenience factory: ``QuickPerson("Jane Doe", dob="1900")`` returns a fully constructed Person."""

    def __new__(  # type: ignore[misc]
        cls,
        name: str,
        dob: Optional[str] = None,
        dod: Optional[str] = None,
    ) -> Person:
        from .date import Date
        facts = []
        if dob:
            facts.append(Fact(type=FactType.Birth, date=Date(original=dob)))
        if dod:
            facts.append(Fact(type=FactType.Death, date=Date(original=dod)))
        return Person(facts=facts, names=[QuickName(name=name)] if name else [])
