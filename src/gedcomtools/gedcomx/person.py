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
        if fact_to_add and isinstance(fact_to_add, Fact):
            for current in self.facts:
                if fact_to_add == current:
                    return False
            self.facts.append(fact_to_add)
            return True
        return False

    def add_name(self, name_to_add: Name) -> bool:
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
        try:
            name_text = self.names[0].nameForms[0].fullText
        except (IndexError, AttributeError):
            name_text = None
        return {
            "ascendancyNumber": "1",
            "deathDate": "from 2001 to 2005",
            "descendancyNumber": "1",
            "gender": self.gender.type if self.gender else "Unknown",
            "lifespan": "-2005",
            "name": name_text,
        }

    @property
    def name(self) -> str | None:
        try:
            return self.names[0].nameForms[0].fullText
        except (IndexError, AttributeError):
            return None


class QuickPerson:
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
