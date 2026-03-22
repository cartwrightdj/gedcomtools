from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, List, Optional

from pydantic import Field, PrivateAttr

from .attribution import Attribution
from .gx_base import GedcomXModel
from .identifier import make_uid
from .note import Note
from .qualifier import Qualifier
from .resource import Resource
from .source_reference import SourceReference
from .uri import URI

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# ConfidenceLevel  (subclass of Qualifier — special enum-like usage)
# ---------------------------------------------------------------------------

class ConfidenceLevel(Qualifier):
    High: ClassVar[str] = "http://gedcomx.org/High"
    Medium: ClassVar[str] = "http://gedcomx.org/Medium"
    Low: ClassVar[str] = "http://gedcomx.org/Low"
    _name_required: ClassVar[bool] = False

    _NAME_TO_URI: ClassVar[dict] = {
        "high": "http://gedcomx.org/High",
        "medium": "http://gedcomx.org/Medium",
        "low": "http://gedcomx.org/Low",
    }

    @classmethod
    def from_json(cls, data: Any, _context: Any = None) -> Optional["ConfidenceLevel"]:
        if data is None:
            return None
        if isinstance(data, cls):
            return data
        if isinstance(data, dict):
            token = (
                data.get("confidence")
                or data.get("type")
                or data.get("value")
                or data.get("level")
                or data.get("uri")
            )
        else:
            token = data
        if token is None:
            return None
        token_str = str(token).strip()
        if token_str.lower() in cls._NAME_TO_URI:
            uri = cls._NAME_TO_URI[token_str.lower()]
        elif token_str in (cls.High, cls.Medium, cls.Low):
            uri = token_str
        else:
            raise ValueError(f"Unknown ConfidenceLevel: {token!r}")
        return cls.model_construct(value=uri)

    @property
    def description(self) -> str:
        descriptions = {
            self.High: "The contributor has a high degree of confidence that the assertion is true.",
            self.Medium: "The contributor has a medium degree of confidence that the assertion is true.",
            self.Low: "The contributor has a low degree of confidence that the assertion is true.",
        }
        return descriptions.get(self.value or "", "No description available.")


# ---------------------------------------------------------------------------
# Conclusion
# ---------------------------------------------------------------------------

class Conclusion(GedcomXModel):
    """Base class for genealogical assertions."""

    identifier: ClassVar[str] = "http://gedcomx.org/v1/Conclusion"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    # Internal URI (not serialized)
    _uri: Optional[URI] = PrivateAttr(default=None)

    id: str = Field(default_factory=make_uid)
    lang: Optional[str] = None
    sources: List[SourceReference] = Field(default_factory=list)
    analysis: Optional[Any] = None      # Resource | Document
    notes: List[Note] = Field(default_factory=list)
    confidence: Optional[ConfidenceLevel] = None
    attribution: Optional[Attribution] = None

    def model_post_init(self, __context: object) -> None:
        self._uri = URI(fragment=self.id)

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def add_note(self, note: Note) -> bool:
        if not isinstance(note, Note):
            raise ValueError("'note' must be of Type 'Note'")
        for existing in self.notes:
            if note == existing:
                return False
        self.notes.append(note)
        return True

    def add_source_reference(self, source_to_add: SourceReference) -> None:
        if not isinstance(source_to_add, SourceReference):
            raise ValueError(
                f"source_to_add must be a SourceReference, got {type(source_to_add).__name__}"
            )
        for current in self.sources:
            if source_to_add == current:
                return
        self.sources.append(source_to_add)

    def _validate_self(self, result: Any) -> None:
        from .validation import check_lang, check_instance
        # id must be a non-empty string
        if not self.id or not str(self.id).strip():
            result.error("id", "id must not be empty")
        # lang: BCP-47 format
        check_lang(result, "lang", self.lang)
        # analysis: Resource or Document
        if self.analysis is not None:
            from .document import Document
            check_instance(result, "analysis", self.analysis, Resource, Document)
        # attribution type
        check_instance(result, "attribution", self.attribution, Attribution)
        # confidence
        if self.confidence is not None:
            if not isinstance(self.confidence, ConfidenceLevel):
                result.error("confidence", f"Expected ConfidenceLevel, got {type(self.confidence).__name__}")
            elif self.confidence.value not in (ConfidenceLevel.High, ConfidenceLevel.Medium, ConfidenceLevel.Low):
                result.warn("confidence", f"Unrecognised confidence value: {self.confidence.value!r}")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return (
            self.id == other.id
            and self.lang == other.lang
            and self.sources == other.sources
            and self.analysis == other.analysis
            and self.notes == other.notes
            and self.confidence == other.confidence
            and self.attribution == other.attribution
        )
