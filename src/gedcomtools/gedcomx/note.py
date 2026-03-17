from typing import Any, Optional
"""
======================================================================
 Project: Gedcom-X
 File:    note.py
 Author:  David J. Cartwright
 Purpose: Python Object representation of GedcomX Name, NameType, NameForm, NamePart Types

 Created: 2025-08-25
 Updated:
   - 2025-09-03: _from_json_ refactor
   - 2025-09-09: added schema_class
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
from .attribution import Attribution
from .schemas import extensible
"""
======================================================================
Logging
======================================================================
"""
#=====================================================================

@extensible()
class Note:
    identifier = 'http://gedcomx.org/v1/Note'
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self,lang: Optional[str] = 'en', subject: Optional[str] = None, text: Optional[str] = None, attribution: Optional[Attribution] = None) -> None:
        self.lang = lang
        self.subject = subject
        self.text = text
        self.attribution = attribution  

    def append(self, text_to_add: str):
        """Append text to the note, concatenating with any existing text.

        Raises:
            ValueError: If text_to_add is not a non-empty string.
        """
        if text_to_add and isinstance(text_to_add, str):
            if self.text:
                self.text = self.text + text_to_add
            else:
                self.text = text_to_add
        else:
            raise ValueError("The text to add must be a non-empty string.")
    
    # ---- hashing & equality ----
    @staticmethod
    def _norm(s: str | None) -> str:
        # normalize None -> "", strip outer whitespace
        return (s or "").strip()

    def _key(self) -> tuple:
        # Base identity: language (case-insensitive), subject, text
        base = (
            self._norm(self.lang).casefold(),
            self._norm(self.subject),
            self._norm(self.text),
        )
        # If you want attribution to affect identity AND it has a stable id,
        # uncomment the next 3 lines:
        # a = self.attribution
        # a_id = getattr(a, "id", None) if a is not None else None
        # return base + (a_id,)
        return base

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Note):
            return NotImplemented
        return self._key() == other._key()

    
