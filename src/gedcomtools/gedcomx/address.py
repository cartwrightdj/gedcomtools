"""
Address data types for the GedcomX conceptual model.
"""
from __future__ import annotations
from typing import ClassVar, Optional

from pydantic import PrivateAttr

from .gx_base import GedcomXModel


class Address(GedcomXModel):
    """GedcomX address data type."""

    identifier: ClassVar[str] = "http://gedcomx.org/v1/Address"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    city: Optional[str] = None
    country: Optional[str] = None
    postalCode: Optional[str] = None
    stateOrProvince: Optional[str] = None
    street: Optional[str] = None
    street2: Optional[str] = None
    street3: Optional[str] = None
    street4: Optional[str] = None
    street5: Optional[str] = None
    street6: Optional[str] = None

    # Raw free-form address string (used by _append; not serialized directly)
    _raw_value: Optional[str] = PrivateAttr(default=None)

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        if not self.value and not self._raw_value:
            result.warn("", "Address has no data (all fields are None or empty)")

    def model_post_init(self, __context: object) -> None:
        # Preserve raw_value passed as 'value' kwarg (handled by accept_extras)
        raw = (self.model_extra or {}).get("value")
        if raw is not None:
            self._raw_value = raw

    @property
    def value(self) -> str:
        return ", ".join(
            filter(
                None,
                [
                    self.street, self.street2, self.street3,
                    self.street4, self.street5, self.street6,
                    self.city, self.stateOrProvince,
                    self.postalCode, self.country,
                ],
            )
        )

    @value.setter
    def value(self, value: str) -> None:
        self._raw_value = value

    def _append(self, value: str) -> None:
        if self._raw_value:
            self._raw_value = self._raw_value + " " + value
        else:
            self._raw_value = value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return (
            self.value == other.value
            and self.city == other.city
            and self.country == other.country
            and self.postalCode == other.postalCode
            and self.stateOrProvince == other.stateOrProvince
            and self.street == other.street
            and self.street2 == other.street2
            and self.street3 == other.street3
            and self.street4 == other.street4
            and self.street5 == other.street5
            and self.street6 == other.street6
        )

    def __str__(self) -> str:
        parts = [
            self._raw_value, self.street, self.street2, self.street3,
            self.street4, self.street5, self.street6,
            self.city, self.stateOrProvince, self.postalCode, self.country,
        ]
        return ", ".join(str(p) for p in parts if p)
