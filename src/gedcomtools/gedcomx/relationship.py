# GedcomX Relationship model.
# person1/person2 typed as Union[Person, Resource]; circular import resolved via
# bottom-of-file import and model_rebuild().

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, List, Optional, Union

from pydantic import Field, field_validator

from .fact import Fact
from .resource import Resource
from .subject import Subject

if TYPE_CHECKING:
    from .person import Person


class RelationshipType(Enum):
    Couple = "http://gedcomx.org/Couple"
    ParentChild = "http://gedcomx.org/ParentChild"

    @property
    def description(self) -> str:
        descriptions = {
            RelationshipType.Couple: "A relationship of a pair of persons.",
            RelationshipType.ParentChild: "A relationship from a parent to a child.",
        }
        return descriptions.get(self, "No description available.")


class Relationship(Subject):
    """Represents a relationship between two persons."""

    identifier: ClassVar[str] = "http://gedcomx.org/v1/Relationship"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    type: Optional[RelationshipType] = None
    person1: Optional[Union[Person, Resource]] = None
    person2: Optional[Union[Person, Resource]] = None
    facts: List[Fact] = Field(default_factory=list)

    @field_validator("person1", "person2", mode="before")
    @classmethod
    def _coerce_person(cls, v: Any) -> Any:
        if isinstance(v, dict):
            return Resource.model_validate(v)
        if isinstance(v, str):
            return Resource(resource=v)
        return v

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_instance
        from .person import Person
        if self.type is not None and not isinstance(self.type, RelationshipType):
            result.error("type", f"Expected RelationshipType, got {type(self.type).__name__}: {self.type!r}")
        if self.person1 is None:
            result.warn("person1", "Relationship has no person1")
        else:
            check_instance(result, "person1", self.person1, Person, Resource)
        if self.person2 is None:
            result.warn("person2", "Relationship has no person2")
        else:
            check_instance(result, "person2", self.person2, Person, Resource)
        for i, f_ in enumerate(self.facts):
            check_instance(result, f"facts[{i}]", f_, Fact)

    def add_fact(self, fact: Fact) -> None:
        if fact is not None and isinstance(fact, Fact):
            for existing in self.facts:
                if fact == existing:
                    return
            self.facts.append(fact)
        else:
            raise TypeError(f"Expected type 'Fact', received type {type(fact)}")

    @staticmethod
    def _short(s: Any, n: int = 60) -> str:
        if s is None:
            return "None"
        s = str(s)
        return s if len(s) <= n else s[: n - 1] + "…"

    @staticmethod
    def _label_person(p: Any) -> str:
        if p is None:
            return "None"
        try:
            pid = getattr(p, "id", None)
            pname = getattr(p, "name", None)
            if pid or pname:
                parts = []
                if pid:
                    parts.append(f"id={pid}")
                if pname:
                    parts.append(f"name={Relationship._short(pname)}")
                return f"Person({', '.join(parts)})"
        except Exception:
            pass
        for attr in ("resource", "resourceId"):
            val = getattr(p, attr, None)
            if val:
                return f"Resource(ref={Relationship._short(val)})"
        pid = getattr(p, "id", None)
        base = type(p).__name__
        return f"{base}(id={pid})" if pid else f"<{base}>"

    def __str__(self) -> str:
        p1 = self._label_person(self.person1)
        p2 = self._label_person(self.person2)
        t = getattr(self.type, "name", None) or self.type or "Unknown"
        fact_count = len(self.facts) if self.facts is not None else 0
        rid_part = f"id={self.id}, " if self.id else ""
        return (
            f"Relationship({rid_part}type={t}, "
            f"person1={p1}, person2={p2}, facts={fact_count})"
        )

    def __repr__(self) -> str:
        return (
            f"Relationship(person1={self.person1!r}, person2={self.person2!r}, "
            f"facts={self.facts!r}, id={self.id!r}, type={self.type!r})"
        )


# Break the Person ↔ Relationship circular reference by rebuilding after both
# classes are fully defined.
from .person import Person  # noqa: E402
Relationship.model_rebuild()
Person.model_rebuild()
