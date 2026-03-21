from __future__ import annotations
from typing import ClassVar

from .gx_base import GedcomXModel
from .resource import Resource


class OnlineAccount(GedcomXModel):
    identifier: ClassVar[str] = "http://gedcomx.org/v1/OnlineAccount"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    serviceHomepage: Resource
    accountName: str

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_instance, check_nonempty
        check_instance(result, "serviceHomepage", self.serviceHomepage, Resource)
        check_nonempty(result, "accountName", self.accountName, "error")
