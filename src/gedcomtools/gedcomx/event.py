"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/event.py
 Author:  David J. Cartwright
 Purpose: GedcomX Event model: Event, EventType, and EventRole types

 Created: 2025-08-25
 Updated: 2026-03-31 — replaced bare bottom-of-file circular-import pattern with
                        explicit _types_namespace={"Person": ...} rebuild call;
                        adds del to keep Person out of module's public namespace
======================================================================
"""
# GedcomX Event and EventRole models.
# EventRole.person typed as Union[Person, Resource]; circular import resolved via
# bottom-of-file import and model_rebuild().

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, List, Optional, Union

if TYPE_CHECKING:
    from .person import Person

from pydantic import Field, field_validator

from .conclusion import Conclusion
from .date import Date
from .place_reference import PlaceReference
from .resource import Resource
from .subject import Subject


class EventRoleType(Enum):
    """Enumeration of recognized roles a person may play in an event."""

    Principal = "http://gedcomx.org/Principal"
    Participant = "http://gedcomx.org/Participant"
    Official = "http://gedcomx.org/Official"
    Witness = "http://gedcomx.org/Witness"

    @property
    def description(self):
        """Return a human-readable description of this event role type."""
        descriptions = {
            EventRoleType.Principal: "The person is the principal person of the event.",
            EventRoleType.Participant: "A participant in the event.",
            EventRoleType.Official: "A person officiating the event.",
            EventRoleType.Witness: "A witness of the event.",
        }
        return descriptions.get(self, "No description available.")


class EventRole(Conclusion):
    """A person's role in a genealogical event."""

    identifier: ClassVar[str] = "http://gedcomx.org/v1/EventRole"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    person: Optional[Union[Person, Resource]] = None
    type: Optional[EventRoleType] = None
    details: Optional[str] = None

    @field_validator("person", mode="before")
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
        if self.type is not None and not isinstance(self.type, EventRoleType):
            result.error("type", f"Expected EventRoleType, got {type(self.type).__name__}: {self.type!r}")
        if self.person is None:
            result.warn("person", "EventRole has no person")
        else:
            from .person import Person
            check_instance(result, "person", self.person, Person, Resource)

    def __str__(self) -> str:
        parts = []
        if self.type is not None:
            parts.append(f"type={getattr(self.type, 'name', str(self.type))}")
        if self.person is not None:
            parts.append(f"person={self.person}")
        if self.details:
            parts.append(f"details={self.details!r}")
        if getattr(self, "id", None):
            parts.append(f"id={self.id!r}")
        return f"EventRole({', '.join(parts)})" if parts else "EventRole()"

    def __repr__(self) -> str:
        if self.type is not None:
            tcls = self.type.__class__.__name__
            tname = getattr(self.type, "name", str(self.type))
            tval = getattr(self.type, "value", self.type)
            type_repr = f"<{tcls}.{tname}: {tval!r}>"
        else:
            type_repr = "None"
        return (
            f"{self.__class__.__name__}("
            f"id={getattr(self, 'id', None)!r}, "
            f"lang={getattr(self, 'lang', None)!r}, "
            f"type={type_repr}, "
            f"person={self.person!r}, "
            f"details={self.details!r})"
        )


class EventType(Enum):
    """Enumeration of known genealogical event types."""

    Adoption = "http://gedcomx.org/Adoption"
    AdultChristening = "http://gedcomx.org/AdultChristening"
    Annulment = "http://gedcomx.org/Annulment"
    Baptism = "http://gedcomx.org/Baptism"
    BarMitzvah = "http://gedcomx.org/BarMitzvah"
    BatMitzvah = "http://gedcomx.org/BatMitzvah"
    Birth = "http://gedcomx.org/Birth"
    Blessing = "http://gedcomx.org/Blessing"
    Burial = "http://gedcomx.org/Burial"
    Census = "http://gedcomx.org/Census"
    Christening = "http://gedcomx.org/Christening"
    Circumcision = "http://gedcomx.org/Circumcision"
    Confirmation = "http://gedcomx.org/Confirmation"
    Cremation = "http://gedcomx.org/Cremation"
    Death = "http://gedcomx.org/Death"
    Divorce = "http://gedcomx.org/Divorce"
    DivorceFiling = "http://gedcomx.org/DivorceFiling"
    Education = "http://gedcomx.org/Education"
    Engagement = "http://gedcomx.org/Engagement"
    Emigration = "http://gedcomx.org/Emigration"
    Excommunication = "http://gedcomx.org/Excommunication"
    FirstCommunion = "http://gedcomx.org/FirstCommunion"
    Funeral = "http://gedcomx.org/Funeral"
    Immigration = "http://gedcomx.org/Immigration"
    LandTransaction = "http://gedcomx.org/LandTransaction"
    Marriage = "http://gedcomx.org/Marriage"
    MilitaryAward = "http://gedcomx.org/MilitaryAward"
    MilitaryDischarge = "http://gedcomx.org/MilitaryDischarge"
    Mission = "http://gedcomx.org/Mission"
    MoveFrom = "http://gedcomx.org/MoveFrom"
    MoveTo = "http://gedcomx.org/MoveTo"
    Naturalization = "http://gedcomx.org/Naturalization"
    Ordination = "http://gedcomx.org/Ordination"
    Retirement = "http://gedcomx.org/Retirement"
    MarriageSettlment = "https://gedcom.io/terms/v7/MARS"
    UnknowUserCreated = "https://gedcom.io/terms/v1/UUCE"

    @property
    def description(self):
        """Return a human-readable description of this event type."""
        descriptions = {
            EventType.Adoption: "An adoption event.",
            EventType.AdultChristening: "An adult christening event.",
            EventType.Annulment: "An annulment event of a marriage.",
            EventType.Baptism: "A baptism event.",
            EventType.BarMitzvah: "A bar mitzvah event.",
            EventType.BatMitzvah: "A bat mitzvah event.",
            EventType.Birth: "A birth event.",
            EventType.Blessing: "An official blessing event.",
            EventType.Burial: "A burial event.",
            EventType.Census: "A census event.",
            EventType.Christening: "A christening event at birth.",
            EventType.Circumcision: "A circumcision event.",
            EventType.Confirmation: "A confirmation event.",
            EventType.Cremation: "A cremation event after death.",
            EventType.Death: "A death event.",
            EventType.Divorce: "A divorce event.",
            EventType.DivorceFiling: "A divorce filing event.",
            EventType.Education: "An education or educational achievement event.",
            EventType.Engagement: "An engagement to be married event.",
            EventType.Emigration: "An emigration event.",
            EventType.Excommunication: "An excommunication event from a church.",
            EventType.FirstCommunion: "A first communion event.",
            EventType.Funeral: "A funeral event.",
            EventType.Immigration: "An immigration event.",
            EventType.LandTransaction: "A land transaction event.",
            EventType.Marriage: "A marriage event.",
            EventType.MilitaryAward: "A military award event.",
            EventType.MilitaryDischarge: "A military discharge event.",
            EventType.Mission: "A mission event.",
            EventType.MoveFrom: "An event of a move from a location.",
            EventType.MoveTo: "An event of a move to a location.",
            EventType.Naturalization: "A naturalization event.",
            EventType.Ordination: "An ordination event.",
            EventType.Retirement: "A retirement event.",
        }
        return descriptions.get(self, "No description available.")

    @staticmethod
    def guess(description):
        """Return the best-matching EventType for the given description string, or None."""
        keywords_to_event_type = {
            "adoption": EventType.Adoption,
            "christening": EventType.Christening,
            "annulment": EventType.Annulment,
            "baptism": EventType.Baptism,
            "bar mitzvah": EventType.BarMitzvah,
            "bat mitzvah": EventType.BatMitzvah,
            "birth": EventType.Birth,
            "blessing": EventType.Blessing,
            "burial": EventType.Burial,
            "census": EventType.Census,
            "circumcision": EventType.Circumcision,
            "confirmation": EventType.Confirmation,
            "cremation": EventType.Cremation,
            "death": EventType.Death,
            "divorce": EventType.Divorce,
            "divorce filing": EventType.DivorceFiling,
            "education": EventType.Education,
            "engagement": EventType.Engagement,
            "emigration": EventType.Emigration,
            "excommunication": EventType.Excommunication,
            "first communion": EventType.FirstCommunion,
            "funeral": EventType.Funeral,
            "arrival": EventType.Immigration,
            "immigration": EventType.Immigration,
            "land transaction": EventType.LandTransaction,
            "marriage": EventType.Marriage,
            "military award": EventType.MilitaryAward,
            "military discharge": EventType.MilitaryDischarge,
            "mission": EventType.Mission,
            "move from": EventType.MoveFrom,
            "move to": EventType.MoveTo,
            "naturalization": EventType.Naturalization,
            "ordination": EventType.Ordination,
            "retirement": EventType.Retirement,
        }
        description_lower = description.lower()
        for keyword, event_type in keywords_to_event_type.items():
            if keyword in description_lower:
                return event_type
        return None


class Event(Subject):
    """A genealogical event with an optional date, place, and participant roles."""

    identifier: ClassVar[str] = "http://gedcomx.org/v1/Event"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    type: Optional[EventType] = None
    date: Optional[Date] = None
    place: Optional[PlaceReference] = None
    roles: List[EventRole] = Field(default_factory=list)

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_instance
        if self.type is not None and not isinstance(self.type, EventType):
            result.error("type", f"Expected EventType, got {type(self.type).__name__}: {self.type!r}")
        if self.date is None and self.place is None:
            result.warn("", "Event has neither date nor place")
        check_instance(result, "date", self.date, Date)
        check_instance(result, "place", self.place, PlaceReference)
        for i, role in enumerate(self.roles):
            check_instance(result, f"roles[{i}]", role, EventRole)


# Resolve the Person ↔ EventRole forward reference.
# person.py does not import event.py at module level, so this deferred import
# is safe.  _types_namespace makes the resolution explicit and keeps 'Person'
# out of event.py's public namespace.
from .person import Person as _Person_rebuild  # noqa: E402
EventRole.model_rebuild(_types_namespace={"Person": _Person_rebuild})
del _Person_rebuild
