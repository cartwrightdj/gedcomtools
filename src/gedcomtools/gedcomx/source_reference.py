from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, List, Optional, Union

from pydantic import Field

from .attribution import Attribution
from .gx_base import GedcomXModel
from .qualifier import Qualifier
from .resource import Resource
from .uri import URI

if TYPE_CHECKING:
    from .source_description import SourceDescription


class KnownSourceReference(Qualifier):
    CharacterRegion: ClassVar[str] = "http://gedcomx.org/CharacterRegion"
    RectangleRegion: ClassVar[str] = "http://gedcomx.org/RectangleRegion"
    TimeRegion: ClassVar[str] = "http://gedcomx.org/TimeRegion"
    Page: ClassVar[str] = "http://gedcomx.org/Page"

    @property
    def description_text(self) -> str:
        descriptions = {
            self.CharacterRegion: "A region of text in a digital document.",
            self.RectangleRegion: "A rectangular region of a digital image.",
            self.TimeRegion: "A region of time in a digital audio or video recording.",
            self.Page: "A single page in a multi-page document.",
        }
        return descriptions.get(self.value or "", "No description available.")


class SourceReference(GedcomXModel):
    identifier: ClassVar[str] = "http://gedcomx.org/v1/SourceReference"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    description: Optional[Any] = None   # URI | SourceDescription
    descriptionId: Optional[str] = None
    attribution: Optional[Attribution] = None
    qualifiers: List[Qualifier] = Field(default_factory=list)

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_instance, check_nonempty
        if self.description is None and self.descriptionId is None:
            result.warn("", "SourceReference has neither description nor descriptionId")
        if self.description is not None:
            from .source_description import SourceDescription
            check_instance(result, "description", self.description, URI, Resource, SourceDescription)
        if self.descriptionId is not None:
            check_nonempty(result, "descriptionId", self.descriptionId)
        check_instance(result, "attribution", self.attribution, Attribution)
        for i, q in enumerate(self.qualifiers):
            check_instance(result, f"qualifiers[{i}]", q, Qualifier)

    def add_qualifier(self, qualifier: Qualifier) -> None:
        if not isinstance(qualifier, (Qualifier, KnownSourceReference)):
            raise ValueError(
                "The 'qualifier' must be type 'Qualifier' or 'KnownSourceReference', "
                f"not {type(qualifier)}"
            )
        for current in self.qualifiers:
            if qualifier == current:
                return
        self.qualifiers.append(qualifier)

    def append(self, text_to_add: str) -> None:
        if text_to_add and isinstance(text_to_add, str):
            if self.descriptionId is None:
                self.descriptionId = text_to_add
            else:
                self.descriptionId += text_to_add
        else:
            raise ValueError("The 'text_to_add' must be a non-empty string.")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        self_uri = getattr(self.description, "_uri", None)
        other_uri = getattr(other.description, "_uri", None)
        return self_uri == other_uri
