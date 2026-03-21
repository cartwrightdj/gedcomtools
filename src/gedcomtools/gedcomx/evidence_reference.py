from __future__ import annotations
from typing import TYPE_CHECKING, Any, ClassVar, Optional, Union

from .attribution import Attribution
from .gx_base import GedcomXModel
from .resource import Resource

if TYPE_CHECKING:
    from .subject import Subject


class EvidenceReference(GedcomXModel):
    identifier: ClassVar[str] = "http://gedcomx.org/v1/EvidenceReference"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    resource: Optional[Any] = None       # Resource | Subject
    attribution: Optional[Attribution] = None

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_instance
        if self.resource is None:
            result.warn("resource", "EvidenceReference has no resource")
        else:
            from .subject import Subject
            check_instance(result, "resource", self.resource, Resource, Subject)
        check_instance(result, "attribution", self.attribution, Attribution)
