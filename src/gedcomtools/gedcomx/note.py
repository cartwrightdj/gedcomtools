"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/note.py
 Author:  David J. Cartwright
 Purpose: GedcomX Note model

 Created: 2025-08-25
 Updated:
======================================================================
"""
from __future__ import annotations

from typing import ClassVar, Optional

from .attribution import Attribution
from .gx_base import GedcomXModel


class Note(GedcomXModel):
    """A free-text note attached to a conclusion or source, with optional language and attribution."""

    identifier: ClassVar[str] = "http://gedcomx.org/v1/Note"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    lang: Optional[str] = "en"
    subject: Optional[str] = None
    text: Optional[str] = None
    attribution: Optional[Attribution] = None

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_lang, check_instance
        check_lang(result, "lang", self.lang)
        if self.text is None:
            result.warn("text", "Note has no text")
        elif not self.text.strip():
            result.warn("text", "Note.text is blank")
        check_instance(result, "attribution", self.attribution, Attribution)

    def append(self, text_to_add: str) -> None:
        """Append *text_to_add* to the existing note text."""
        if text_to_add and isinstance(text_to_add, str):
            self.text = (self.text + text_to_add) if self.text else text_to_add
        else:
            raise ValueError("The text to add must be a non-empty string.")

    @staticmethod
    def _norm(s: str | None) -> str:
        return (s or "").strip()

    def _key(self) -> tuple:
        return (
            self._norm(self.lang).casefold(),
            self._norm(self.subject),
            self._norm(self.text),
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Note):
            return NotImplemented
        return self._key() == other._key()

    def __hash__(self) -> int:
        return hash(self._key())
