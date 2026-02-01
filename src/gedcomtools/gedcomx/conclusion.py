from __future__ import annotations
import warnings

from typing import Any, Optional, List, Union, TYPE_CHECKING

"""
======================================================================
 Project: Gedcom-X
 File:    conclusion.py
 Author:  David J. Cartwright
 Purpose: 

 Created: 2025-08-25
 Updated:
   - 2025-09-03: _from_json_ refactor 
   - 2025-09-09: added schema_class
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Type Imports
======================================================================
"""
from .attribution import Attribution
if TYPE_CHECKING:
    from .document import Document

from .extensible import Extensible
from .note import Note
from .qualifier import Qualifier
from .resource import Resource, URI
from .schemas import extensible
from .source_reference import SourceReference
from ..logging_hub import hub, logging
from .identifier import make_uid
"""
======================================================================
Logging
======================================================================
"""
log = logging.getLogger("gedcomx")
serial_log = "gedcomx.serialization"
#=====================================================================




class ConfidenceLevel(Qualifier):
    High = "http://gedcomx.org/High"
    Medium = "http://gedcomx.org/Medium"
    Low = "http://gedcomx.org/Low"

    _NAME_TO_URI = {
        "high": High,
        "medium": Medium,
        "low": Low,
    }

    @classmethod
    def _from_json_(cls, data,context):
        """
        Accepts:
          - "High" | "Medium" | "Low"
          - "http://gedcomx.org/High" | ".../Medium" | ".../Low"
          - {"type": "..."} or {"value": "..."} or {"confidence": "..."} or {"level": "..."} or {"uri": "..."}
          - existing ConfidenceLevel instance
        Returns:
          ConfidenceLevel instance with .value set to the canonical URI.
        """
        if data is None:
            return None

        if isinstance(data, cls):
            return data

        # Extract token from dicts or use the raw scalar
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

        # Normalize to canonical URI
        if token_str.lower() in cls._NAME_TO_URI:
            uri = cls._NAME_TO_URI[token_str.lower()]
        elif token_str in (cls.High, cls.Medium, cls.Low):
            uri = token_str
        else:
            raise ValueError(f"Unknown ConfidenceLevel: {token!r}")

        # Create a ConfidenceLevel instance without invoking Qualifier.__init__
        obj = cls.__new__(cls)
        # store the canonical URI on the instance; used by description and (optionally) serialization
        obj.value = uri
        return obj

    @property
    def description(self):
        descriptions = {
            self.High: "The contributor has a high degree of confidence that the assertion is true.",
            self.Medium: "The contributor has a medium degree of confidence that the assertion is true.",
            self.Low: "The contributor has a low degree of confidence that the assertion is true."
        }
        # Works whether the instance holds .value or (edge-case) if `self` is compared directly
        key = getattr(self, "value", self)
        return descriptions.get(key, "No description available.")


@extensible()    
class Conclusion():
    """
    Represents a conclusion in the GEDCOM X conceptual model. A conclusion is a 
    genealogical assertion about a person, relationship, or event, derived from 
    one or more sources, with optional supporting metadata such as confidence, 
    attribution, and notes.

    Args:
        id (str, optional): A unique identifier for the conclusion. If not provided, 
            a UUID-based identifier will be automatically generated.
        lang (str, optional): The language code of the conclusion. 
        sources (list[SourceReference], optional): A list of source references that 
            support the conclusion.
        analysis (Document | Resource, optional): A reference to an analysis document 
            or resource that supports the conclusion.
        notes (list[Note], optional): A list of notes providing additional context. 
            Defaults to an empty list.
        confidence (ConfidenceLevel, optional): The contributor's confidence in the 
            conclusion (High, Medium, or Low).
        attribution (Attribution, optional): Information about who contributed the 
            conclusion and when.
        uri (Resource, optional): A URI reference for the conclusion. Defaults to a 
            URI with the fragment set to the `id`.
        links (_LinkList, optional): A list of links associated with the conclusion. 
            Defaults to an empty `_LinkList`.  
    """
    identifier = 'http://gedcomx.org/v1/Conclusion'
    version = 'http://gedcomx.org/conceptual-model/v1'
   
    def __init__(self,
                 id: Optional[str] = None,
                 lang: Optional[str] = None,
                 sources: Optional[List[SourceReference]] = None,
                 analysis: Optional[Union[Resource,Document]] = None,
                 notes: Optional[List[Note]] = None,
                 confidence: Optional[ConfidenceLevel] = None,
                 attribution: Optional[Attribution] = None,) -> None:
               
        self.id = id if id else make_uid()
        self.lang = lang
        self.sources = sources if sources else []
        self.analysis = analysis
        self.notes = notes if notes else []
        self.confidence = confidence
        self.attribution = attribution
        self._uri = URI(fragment=id) if id else None
    
    def add_note(self,note: Note):
        if note and isinstance(note,Note):
            for existing in self.notes:
                if note == existing:
                    return False
            self.notes.append(note)
        else: raise ValueError(f"'note' must be of Type 'Note'")

    def add_source_reference(self, source_to_add: SourceReference):
        if source_to_add and isinstance(source_to_add,SourceReference):
            for current_source in self.sources:
                if source_to_add == current_source:
                    return
            self.sources.append(source_to_add)
        else:
            raise ValueError()
        
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        
        return (
            self.id == other.id and
            self.lang == other.lang and
            self.sources == other.sources and
            self.analysis == other.analysis and
            self.notes == other.notes and
            self.confidence == other.confidence and
            self.attribution == other.attribution
        )