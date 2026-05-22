
"""
======================================================================
 Project: Gedcom-X
 File:    mutations.py
 Author:  David J. Cartwright
 Purpose: Objects used to convert TAGs/Structues/Types from GEDCOM Versions
    when simple parsing will not work. (complex or ambiguous structures)

 Created: 2025-08-25
 Updated:
   - 2025-08-31: cleaned up imports and documentation
   - 2025-09-01: filename PEP8 standard, imports changed accordingly

======================================================================
"""

# GEDCOM Module Types
from typing import cast

from .._gedcom5x import Gedcom5xRecord
from .fact import Fact, FactType
from .event import Event, EventType
from .tag_mappings import GEDCOM_TAG_TO_FACT_EVENT_TYPE
# Logging
#=====================================================================

fact_event_table = GEDCOM_TAG_TO_FACT_EVENT_TYPE

class GedcomXObject:
    """Base wrapper capturing the GEDCOM5 record that spawned a GedcomX object."""

    def __init__(self,record: Gedcom5xRecord) -> None:
        self.record = record
        self.created_with_tag: str | None = record.tag if record and isinstance(record, Gedcom5xRecord) else None
        self.created_at_level: int | None = record.level if record and isinstance(record, Gedcom5xRecord) else None
        self.created_at_line_number: int | None = record.line if record and isinstance(record, Gedcom5xRecord) else None

class GedcomXSourceOrDocument(GedcomXObject):
    """Accumulates metadata fields for a GEDCOM SOUR or OBJE record before creating a SourceDescription."""

    def __init__(self,record: Gedcom5xRecord) -> None:
        super().__init__(record)
        self.title: str | None = None
        self.citation: str | None = None
        self.page: str | None = None
        self.contributor: str | None = None
        self.publisher: str | None = None
        self.rights: str | None = None
        self.url: str | None = None
        self.medium: str | None = None
        self.type: str | None = None
        self.format: str | None = None
        self.created: str | None = None
        self.modified: str | None = None
        self.language: str | None = None
        self.relation: str | None = None
        self.identifier: str | None = None
        self.description: str | None = None

class GedcomXEventOrFact(GedcomXObject):
    """Factory that returns the correct Fact or Event instance for a GEDCOM5 tag."""

    def __new__(cls,record: Gedcom5xRecord, _object_stack: dict | None = None) -> object:
        if record.tag in fact_event_table:

            if 'Fact' in fact_event_table[record.tag]:
                obj = Fact(type=cast(FactType, fact_event_table[record.tag]['Fact']))
                return obj
            if 'Event' in fact_event_table[record.tag]:
                obj = Event(type=cast(EventType, fact_event_table[record.tag]['Event']))
                return obj
            raise ValueError(
                f"tag '{record.tag}' found in map but has neither 'Fact' nor 'Event' key"
            )
        raise ValueError(f"{record.tag} not found in map")

class GedcomXRelationshipBuilder(GedcomXObject):
    """Placeholder builder for constructing complex GEDCOM relationship structures."""
