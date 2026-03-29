"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/document.py
 Author:  David J. Cartwright
 Purpose: GedcomX Document model: abstract, transcription, translation, or analysis text

 Created: 2025-08-25
 Updated:
======================================================================
"""
from __future__ import annotations

from enum import Enum
from typing import ClassVar, Optional, Union


from .conclusion import Conclusion
from .source_description import SourceDescription


class DocumentType(Enum):
    """Enumeration of recognized GedcomX document types."""

    Abstract = "http://gedcomx.org/Abstract"
    Transcription = "http://gedcomx.org/Transcription"
    Translation = "http://gedcomx.org/Translation"
    Analysis = "http://gedcomx.org/Analysis"

    @property
    def description(self) -> str:
        """Return a human-readable description of this document type."""
        descriptions = {
            DocumentType.Abstract: "The document is an abstract of a record or document.",
            DocumentType.Transcription: "The document is a transcription of a record or document.",
            DocumentType.Translation: "The document is a translation of a record or document.",
            DocumentType.Analysis: "The document is an analysis done by a researcher.",
        }
        return descriptions.get(self, "No description available.")


class TextType(Enum):
    """Enumeration of text content types for Document.textType."""

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

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        if self.type is not None and not isinstance(self.type, DocumentType):
            result.error("type", f"Expected DocumentType, got {type(self.type).__name__}: {self.type!r}")
        if self.textType is not None and not isinstance(self.textType, TextType):
            result.error("textType", f"Expected TextType, got {type(self.textType).__name__}: {self.textType!r}")
        if self.extracted is not None and not isinstance(self.extracted, bool):
            result.error("extracted", f"Expected bool, got {type(self.extracted).__name__}")
        if self.text is None:
            result.warn("text", "Document has no text")


class DocumentParsingContainer:
    """Thin wrapper used during GEDCOM parsing to associate OBJE sub-records."""

    def __init__(self, source: SourceDescription) -> None:
        self.sourceDescription = source


# Resolve forward references that point back to Document or SourceDescription.
from .source_reference import SourceReference  # noqa: E402
# Include SourceDescription so the cascade rebuild of SourceReference also resolves.
SourceDescription.model_rebuild(_types_namespace={"Document": Document, "SourceDescription": SourceDescription})
