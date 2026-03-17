from enum import Enum
from typing import List, Optional
"""
======================================================================
 Project: Gedcom-X
 File:    gender.py
 Author:  David J. Cartwright
 Purpose: 

 Created: 2025-08-25
 Updated:
   - 2025-09-03: _from_json_ refactor 
   - 2025-09-09: added schema_class
   - 2025-11-12: added dunders
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
from .attribution import Attribution
from .conclusion import ConfidenceLevel, Conclusion

from .note import Note
from .resource import Resource
from .schemas import extensible
from .source_reference import SourceReference
"""
======================================================================
Logging
======================================================================
"""
#=====================================================================


class GenderType(Enum):
    Male = "http://gedcomx.org/Male"
    Female = "http://gedcomx.org/Female"
    Unknown = "http://gedcomx.org/Unknown"
    Intersex = "http://gedcomx.org/Intersex"
    
    @property
    def description(self):
        descriptions = {
            GenderType.Male: "Male gender.",
            GenderType.Female: "Female gender.",
            GenderType.Unknown: "Unknown gender.",
            GenderType.Intersex: "Intersex (assignment at birth)."
        }
        return descriptions.get(self, "No description available.")

@extensible()    
class Gender(Conclusion):
    identifier = 'http://gedcomx.org/v1/Gender'
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self,
                 id: Optional[str] = None,
                 lang: Optional[str] = None,
                 sources: Optional[List[SourceReference]] = None,
                 analysis: Optional[Resource] = None,
                 notes: Optional[List[Note]] = None,
                 confidence: Optional[ConfidenceLevel] = None,
                 attribution: Optional[Attribution] = None, 
                 type: Optional[GenderType] = None):
                 #links: Optional[_rsLinks] = None
                 #) -> None:
        super().__init__(id=id, lang=lang, sources=sources, analysis=analysis, notes=notes, confidence=confidence, attribution=attribution)
        self.type = type
        self.id = id if id else None # No need for id unless provided
    
    def __str__(self) -> str:
        """
        Human-readable summary of the Gender object.
        Shows only fields that exist, including type and id.
        """
        parts = []

        if self.id:
            parts.append(f"id={self.id!r}")

        if self.type:
            try:
                # Prefer Enum name (Male/Female/Unknown/Intersex)
                parts.append(f"type={self.type.name}")
            except Exception:
                parts.append(f"type={self.type!r}")

        if self.lang:
            parts.append(f"lang={self.lang!r}")

        if self.confidence:
            parts.append(f"confidence={self.confidence}")

        if self.attribution:
            parts.append(f"attribution={self.attribution}")

        # Notes & sources only show counts (they can be long lists)
        try:
            if self.notes:
                parts.append(f"notes×{len(self.notes)}")
        except Exception:
            parts.append("notes<?>")

        try:
            if self.sources:
                parts.append(f"sources×{len(self.sources)}")
        except Exception:
            parts.append("sources<?>")

        inner = ", ".join(parts) if parts else "no gender data"
        return f"Gender({inner})"


    def __repr__(self) -> str:
        """
        Developer-oriented representation.
        Shows constructor values exactly as passed.
        """
        return (
            f"Gender("
            f"id={self.id!r}, "
            f"lang={self.lang!r}, "
            f"sources={self.sources!r}, "
            f"analysis={self.analysis!r}, "
            f"notes={self.notes!r}, "
            f"confidence={self.confidence!r}, "
            f"attribution={self.attribution!r}, "
            f"type={self.type!r}"
            f")"
        )

    

        
        