from enum import Enum
from typing import Any, Dict, Optional, List, Union
"""
======================================================================
 Project: Gedcom-X
 File:    relationship.py
 Author:  David J. Cartwright
 Purpose: 

 Created: 2025-08-25
 Updated:
   - 2025-09-31: filename PEP8 standard
   - 2025-09-03: _from_json_ refactor
   - 2025-09-09: added schema_class
   - 2025-09-17: cahnged '.identifiers' to IdentifierList
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
from .attribution import Attribution
from .conclusion import ConfidenceLevel
from .evidence_reference import EvidenceReference
from .fact import Fact
from .identifier import IdentifierList
from .identifier import make_uid
from .note import Note
from .person import Person
from .resource import Resource
from .schemas import extensible
from .source_reference import SourceReference
from .subject import Subject
"""
======================================================================
Logging
======================================================================
"""
#=====================================================================


class RelationshipType(Enum):
    Couple = "http://gedcomx.org/Couple"
    ParentChild = "http://gedcomx.org/ParentChild"
    
    @property
    def description(self):
        descriptions = {
            RelationshipType.Couple: "A relationship of a pair of persons.",
            RelationshipType.ParentChild: "A relationship from a parent to a child."
        }
        return descriptions.get(self, "No description available.")

@extensible(toplevel=True)    
class Relationship(Subject):
    """Represents a relationship between two Person(s)

    Args:
        type (RelationshipType): Type of relationship 
        person1 (Person) = First Person in Relationship
        person2 (Person): Second Person in Relationship

    Raises:
        
    """
    identifier = 'http://gedcomx.org/v1/Relationship'
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self,
             person1: Optional[Union[Resource,Person]] = None,
             person2: Optional[Union[Resource,Person]] = None,
             facts: Optional[List[Fact]] = None,  
             id: Optional[str] = None,
             lang: Optional[str] = None,
             sources: Optional[List[SourceReference]] = None,
             analysis: Optional[Resource] = None,
             notes: Optional[List[Note]] = None,
             confidence: Optional[ConfidenceLevel] = None,
             attribution: Optional[Attribution] = None,
             extracted: Optional[bool] = None,
             evidence: Optional[List[EvidenceReference]] = None,
             media: Optional[List[SourceReference]] = None,
             identifiers:Optional[IdentifierList] = None,
             type: Optional[RelationshipType] = None,
             ) -> None:
    
        # Call superclass initializer if required
        super().__init__(id, lang, sources, analysis, notes, confidence, attribution, extracted, evidence, media, identifiers)
        
        #self.id = id if id else make_uid()
        self.type = type
        self.person1 = person1
        self.person2 = person2
        self.facts = facts if facts else []
    
    def add_fact(self,fact: Fact):
        if (fact is not None) and isinstance(fact,Fact):
            for existing_fact in self.facts:
                if fact == existing_fact:
                    return
            self.facts.append(fact)
        else:
            raise TypeError(f"Expected type 'Fact' recieved type {type(fact)}")

    # ------------- repr/str helpers -----------------------------------------
    @staticmethod
    def _short(s: str, n: int = 60) -> str:
        """Clip long strings for single-line displays."""
        if s is None:
            return "None"
        s = str(s)
        return s if len(s) <= n else (s[: n - 1] + "…")

    @staticmethod
    def _label_person(p: Optional[Union[Resource, Person]]) -> str:
        """Human-ish label for a Person or Resource without forcing heavy reprs."""
        if p is None:
            return "None"
        try:
            # Prefer Person(id, name) if available
            pid = getattr(p, "id", None) or getattr(p, "identifier", None)
            # Common GedcomX person name patterns
            pname = (
                getattr(p, "display", None).name if hasattr(p, "display") and getattr(p, "display") else None
            ) or getattr(p, "fullText", None) \
              or getattr(p, "name", None)

            if pid or pname:
                parts = []
                if pid:   parts.append(f"id={pid}")
                if pname: parts.append(f"name={Relationship._short(pname)}")
                return f"Person({', '.join(parts)})"
        except Exception:
            pass

        # If it's a Resource-like wrapper, try resource / resourceId / resourceRef
        for attr in ("resource", "resourceId", "resourceRef"):
            if hasattr(p, attr):
                val = getattr(p, attr, None)
                if val:
                    return f"Resource(ref={Relationship._short(val)})"

        # Fallback: class and maybe id/str
        pid = getattr(p, "id", None)
        base = type(p).__name__
        if pid:
            return f"{base}(id={pid})"
        return f"<{base}>"

    @staticmethod
    def _summ_fact(f: Any) -> str:
        """Short single-line summary of a Fact (type/date/place)."""
        try:
            ftype = getattr(f, "type", None)
            # Relationship Fact type might be enum; prefer name over raw value
            if hasattr(ftype, "name"):
                ftype = ftype.name
            date = getattr(getattr(f, "date", None), "original", None) or getattr(f, "date", None)
            plac = getattr(getattr(f, "place", None), "original", None) or getattr(f, "place", None)
            bits = [b for b in [ftype, date, plac] if b]
            if bits:
                return Relationship._short(" / ".join(map(str, bits)), 50)
        except Exception:
            pass
        return Relationship._short(repr(f), 50)

    # ------------- dunder representations ------------------------------------
    def __str__(self) -> str:
        """
        Human-friendly one-liner, safe for logs and tables.
        Example:
          Relationship(id=R-123, type=Couple, person1=Person(id=P1,name=John Doe), person2=Person(id=P2,name=Jane Roe), facts=2)
        """
        p1 = self._label_person(self.person1)
        p2 = self._label_person(self.person2)

        t = getattr(self.type, "name", None) or self.type or "Unknown"
        fact_count = len(self.facts) if getattr(self, "facts", None) is not None else 0

        # Optionally include a tiny peek at first fact
        hint = ""
        if fact_count:
            hint = f", firstFact={self._summ_fact(self.facts[0])}"

        rid = getattr(self, "id", None)
        rid_part = f"id={rid}, " if rid else ""
        lang = f", lang={self.lang}" if getattr(self, "lang", None) else ""

        return (
            f"Relationship({rid_part}"
            f"type={t}, "
            f"person1={p1}, "
            f"person2={p2}, "
            f"facts={fact_count}{hint}{lang})"
        )

    def __repr__(self) -> str:
        """
        Developer/debug representation.
        Tries to be as reconstructible as possible by using !r for fields and not
        invoking heavy conversions beyond simple helpers.
        """
        return (
            f"{self.__class__.__name__}("
            f"person1={self.person1!r}, "
            f"person2={self.person2!r}, "
            f"facts={self.facts!r}, "
            f"id={self.id!r}, "
            f"lang={self.lang!r}, "
            f"sources={self.sources!r}, "
            f"analysis={self.analysis!r}, "
            f"notes={self.notes!r}, "
            f"confidence={self.confidence!r}, "
            f"attribution={self.attribution!r}, "
            f"extracted={self.extracted!r}, "
            f"evidence={self.evidence!r}, "
            f"media={self.media!r}, "
            f"identifiers={self.identifiers!r}, "
            f"type={self.type!r}"
            f")"
        )
