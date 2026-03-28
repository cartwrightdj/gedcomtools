from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Union

from pydantic import Field, PrivateAttr, field_validator

from .address import Address
from .gx_base import GedcomXModel
from .identifier import Identifier, IdentifierList, make_uid
from .online_account import OnlineAccount
from .resource import Resource
from .textvalue import TextValue
from .uri import URI

if TYPE_CHECKING:
    pass


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
    person: Optional[Any] = None        # Person | Resource (avoids circular import)
    attribution: Optional[Any] = None   # Attribution
    xnotes: List[Any] = Field(default_factory=list)

    @field_validator("addresses", mode="before")
    @classmethod
    def _drop_none_addresses(cls, v: Any) -> Any:
        if isinstance(v, list):
            return [a for a in v if a is not None]
        return v

    def model_post_init(self, __context: object) -> None:
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
        if not isinstance(address_to_add, Address):
            raise ValueError(f"address must be of type Address, not {type(address_to_add)}")
        for current in self.addresses:
            if address_to_add == current:
                return
        self.addresses.append(address_to_add)

    def add_name(self, name_to_add: Union[TextValue, str]) -> None:
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

    def add_note(self, note_to_add: Any) -> None:
        from .note import Note
        if not isinstance(note_to_add, Note):
            raise ValueError(f"note must be of type Note, got {type(note_to_add)}")
        self.xnotes.append(note_to_add)

    def add_identifier(self, identifier_to_add: Identifier) -> None:
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
        for i, n in enumerate(self.xnotes):
            from .note import Note
            check_instance(result, f"xnotes[{i}]", n, Note)

    # Dunder methods
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        primary_name = self.names[0].value if self.names else "Unnamed Agent"
        homepage_str = f", homepage={self.homepage}" if self.homepage else ""
        return f"Agent(id={self.id}, name='{primary_name}'{homepage_str})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Agent):
            return NotImplemented
        return (
            self.id == other.id
            and self.identifiers == other.identifiers
            and self.names == other.names
            and self.homepage == other.homepage
            and self.openid == other.openid
            and self.accounts == other.accounts
            and self.emails == other.emails
            and self.phones == other.phones
            and self.addresses == other.addresses
            and self.person == other.person
            and self.attribution == other.attribution
            and self.xnotes == other.xnotes
            and self._uri == other._uri
        )

    def shares_name(self, other: "Agent") -> bool:
        if not isinstance(other, Agent):
            return False
        self_names = {n.value for n in self.names if hasattr(n, "value") and n.value}
        other_names = {n.value for n in other.names if hasattr(n, "value") and n.value}
        return bool(self_names & other_names)
