"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/person.py
 Author:  David J. Cartwright
 Purpose: GedcomX Person model with facts, names, gender, and display helpers

 Created: 2025-08-25
 Updated:
======================================================================
"""
from __future__ import annotations

from typing import Any, ClassVar, List, Optional

from pydantic import Field, PrivateAttr

from .fact import Fact, FactType
from .gender import Gender
from .name import Name, QuickName
from .subject import Subject

from ..glog import get_logger

log = get_logger(__name__)


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

    def display(self) -> dict:
        """Return a display-summary dict with name, gender, lifespan, birth date, and death date."""
        try:
            name_text = self.names[0].nameForms[0].fullText
        except (IndexError, AttributeError):
            name_text = None

        birth_date: Optional[str] = None
        death_date: Optional[str] = None
        for fact in self.facts:
            if fact.type == FactType.Birth and fact.date:
                birth_date = fact.date.original
            elif fact.type == FactType.Death and fact.date:
                death_date = fact.date.original

        if birth_date and death_date:
            lifespan = f"{birth_date}-{death_date}"
        elif birth_date:
            lifespan = f"{birth_date}-"
        elif death_date:
            lifespan = f"-{death_date}"
        else:
            lifespan = None

        return {
            "ascendancyNumber": None,
            "deathDate": death_date,
            "descendancyNumber": None,
            "gender": self.gender.type if self.gender else None,
            "lifespan": lifespan,
            "name": name_text,
        }

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
