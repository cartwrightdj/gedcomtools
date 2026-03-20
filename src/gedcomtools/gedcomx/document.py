from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar, List, Optional

from pydantic import Field

from .attribution import Attribution
from .conclusion import Conclusion, ConfidenceLevel
from .gx_base import GedcomXModel
from .note import Note
from .resource import Resource
from .source_description import SourceDescription, ResourceType
from .source_reference import SourceReference


class DocumentType(Enum):
    Abstract = "http://gedcomx.org/Abstract"
    Transcription = "http://gedcomx.org/Transcription"
    Translation = "http://gedcomx.org/Translation"
    Analysis = "http://gedcomx.org/Analysis"

    @property
    def description(self) -> str:
        descriptions = {
            DocumentType.Abstract: "The document is an abstract of a record or document.",
            DocumentType.Transcription: "The document is a transcription of a record or document.",
            DocumentType.Translation: "The document is a translation of a record or document.",
            DocumentType.Analysis: "The document is an analysis done by a researcher.",
        }
        return descriptions.get(self, "No description available.")


class TextType(Enum):
    plain = "plain"
    xhtml = "xhtml"


class Document(Conclusion):
    """A document extracted from a source."""

    identifier: ClassVar[str] = "http://gedcomx.org/v1/Document"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    type: Optional[DocumentType] = None
    extracted: Optional[bool] = None
    textType: Optional[TextType] = None
    text: Optional[str] = None


class DocumentParsingContainer:
    """Thin wrapper used during GEDCOM parsing to associate OBJE sub-records."""

    def __init__(self, source: SourceDescription) -> None:
        self.sourceDescription = source
