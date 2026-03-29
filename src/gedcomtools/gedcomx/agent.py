"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/agent.py
 Author:  David J. Cartwright
 Purpose: GedcomX Agent model: person, organisation, or software that created or modified data

 Created: 2025-08-25
 Updated:
======================================================================
"""
# GedcomX Agent model.
# Represents a person, organisation, or software that created or modified data.
# Equality is semantic: person reference takes priority; falls back to name overlap.
# __hash__ = None — mutable object, not safely hashable.

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Union

if TYPE_CHECKING:
    from .attribution import Attribution
    from .person import Person
    _PersonOrResource = Union[Person, Resource]

from pydantic import Field, PrivateAttr, field_validator

from .address import Address
from .gx_base import GedcomXModel
from .identifier import Identifier, IdentifierList, make_uid
from .online_account import OnlineAccount
from .resource import Resource
from .textvalue import TextValue
from .uri import URI


class Agent(GedcomXModel):
    """A GedcomX Agent — a person, organisation, or software that created/modified data."""

    # Internal URI (not serialized)
    _uri: Optional[URI] = PrivateAttr(default=None)

    id: str = Field(default_factory=make_uid)
    identifiers: IdentifierList = Field(default_factory=IdentifierList)
    names: List[TextValue] = Field(default_factory=list)
    homepage: Optional[URI] = None
    openid: Optional[URI] = None
    accounts: List[OnlineAccount] = Field(default_factory=list)
    emails: List[URI] = Field(default_factory=list)
    phones: List[URI] = Field(default_factory=list)
    addresses: List[Address] = Field(default_factory=list)
    # TYPE_CHECKING branch: gives type checkers Union[Person, Resource] / Attribution.
    # Runtime branch: keeps Any so Pydantic never tries to resolve Person/Attribution
    # before they exist (circular build chain:
    # attribution.py → agent.py ← person.py ← fact.py ← conclusion.py → attribution.py).
    if TYPE_CHECKING:
        person: Optional[Union[Person, Resource]] = None
        attribution: Optional[Attribution] = None
    else:
        person: Optional[Any] = None
        attribution: Optional[Any] = None
    @field_validator("addresses", mode="before")
    @classmethod
    def _drop_none_addresses(cls, v: Any) -> Any:
        if isinstance(v, list):
            return [a for a in v if a is not None]
        return v

    def model_post_init(self, __context: object) -> None:
        """Populate derived state after model initialization."""
        self._uri = URI(fragment=self.id)

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def _append_to_name(self, text_to_append: str) -> None:
        if self.names and self.names[0] and self.names[0].value:
            self.names[0].value = self.names[0].value + text_to_append
        elif self.names and self.names[0]:
            self.names[0].value = text_to_append
        else:
            raise ValueError("Agent has no names to append to")

    def add_address(self, address_to_add: Address) -> None:
        """Add an Address to this agent, skipping duplicates."""
        if not isinstance(address_to_add, Address):
            raise ValueError(f"address must be of type Address, not {type(address_to_add)}")
        for current in self.addresses:
            if address_to_add == current:
                return
        self.addresses.append(address_to_add)

    def add_name(self, name_to_add: Union[TextValue, str]) -> None:
        """Add a name to this agent, skipping duplicates.  Accepts a string or TextValue."""
        if isinstance(name_to_add, str):
            name_to_add = TextValue(value=name_to_add)
        if not isinstance(name_to_add, TextValue):
            raise ValueError(f"name must be str or TextValue, got {type(name_to_add)}")
        if name_to_add.value is None or name_to_add.value == "":
            raise ValueError("name value must not be empty")
        for current in self.names:
            if name_to_add == current:
                return
        self.names.append(name_to_add)

    def add_identifier(self, identifier_to_add: Identifier) -> None:
        """Append an Identifier to this agent's identifier list."""
        self.identifiers.append(identifier_to_add)

    # ------------------------------------------------------------------
    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_instance
        if not self.names:
            result.warn("names", "Agent has no names")
        for i, tv in enumerate(self.names):
            check_instance(result, f"names[{i}]", tv, TextValue)
        check_instance(result, "homepage", self.homepage, URI)
        check_instance(result, "openid", self.openid, URI)
        for i, e in enumerate(self.emails):
            check_instance(result, f"emails[{i}]", e, URI)
        for i, p in enumerate(self.phones):
            check_instance(result, f"phones[{i}]", p, URI)
        for i, acc in enumerate(self.accounts):
            check_instance(result, f"accounts[{i}]", acc, OnlineAccount)
        for i, addr in enumerate(self.addresses):
            check_instance(result, f"addresses[{i}]", addr, Address)
        if self.person is not None:
            from .person import Person
            check_instance(result, "person", self.person, Person, Resource)
        if self.attribution is not None:
            from .attribution import Attribution
            check_instance(result, "attribution", self.attribution, Attribution)
    # Dunder methods
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        primary_name = self.names[0].value if self.names else "Unnamed Agent"
        homepage_str = f", homepage={self.homepage}" if self.homepage else ""
        return f"Agent(id={self.id}, name='{primary_name}'{homepage_str})"

    __hash__ = None  # mutable object with semantic equality — not safely hashable

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Agent):
            return NotImplemented
        if self.person is not None:
            return self.person == other.person
        self_values = {(tv.value or "").casefold() for tv in self.names if tv.value}
        other_values = {(tv.value or "").casefold() for tv in other.names if tv.value}
        return bool(self_values & other_values)

    @property
    def sorted_names(self) -> List[TextValue]:
        """Return names sorted alphabetically by value (primary name order preserved in self.names)."""
        return sorted(self.names, key=lambda tv: (tv.value or "").casefold())

    def shares_name(self, other: "Agent") -> bool:
        """Return True if this agent and *other* share at least one name value."""
        if not isinstance(other, Agent):
            return False
        self_names = {n.value for n in self.names if hasattr(n, "value") and n.value}
        other_names = {n.value for n in other.names if hasattr(n, "value") and n.value}
        return bool(self_names & other_names)


