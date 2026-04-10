
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
from .._gedcom5x import Gedcom5xRecord
from .fact import Fact, FactType
from .event import Event, EventType
# Logging
#=====================================================================

fact_event_table = {
    # Person Fact / Event Types
    "ADOP": {
        "Fact": FactType.AdoptiveParent,
        "Event": EventType.Adoption,
    },
    "CHR": {
        "Fact": FactType.AdultChristening,
        "Event": EventType.AdultChristening,
    },
    "EVEN": {
        "Fact": FactType.Amnesty,
        # no Event
    },
    "BAPM": {
        "Fact": FactType.Baptism,
        "Event": EventType.Baptism,
    },
    "BARM": {
        "Fact": FactType.BarMitzvah,
        "Event": EventType.BarMitzvah,
    },
    "BASM": {
        "Fact": FactType.BatMitzvah,
        "Event": EventType.BatMitzvah,
    },
    "BIRT": {
        "Fact": FactType.Birth,
        "Event": EventType.Birth,
    },
    "BIRT, CHR": {
        "Fact": FactType.Birth,
        "Event": EventType.Birth,
    },
    "BLES": {
        "Fact": FactType.Blessing,
        "Event": EventType.Blessing,
    },
    "BURI": {
        "Fact": FactType.Burial,
        "Event": EventType.Burial,
    },
    "CAST": {
        "Fact": FactType.Caste,
        # no Event
    },
    "CENS": {
        "Fact": FactType.Census,
        "Event": EventType.Census,
    },
    "CIRC": {
        "Fact": FactType.Circumcision,
        "Event": EventType.Circumcision,
    },
    "CONF": {
        "Fact": FactType.Confirmation,
        "Event": EventType.Confirmation,
    },
    "CREM": {
        "Fact": FactType.Cremation,
        "Event": EventType.Cremation,
    },
    "DEAT": {
        "Fact": FactType.Death,
        "Event": EventType.Death,
    },
    "EDUC": {
        "Fact": FactType.Education,
        "Event": EventType.Education,
    },
    "EMIG": {
        "Fact": FactType.Emigration,
        "Event": EventType.Emigration,
    },
    "FCOM": {
        "Fact": FactType.FirstCommunion,
        "Event": EventType.FirstCommunion,
    },
    "GRAD": {
        "Fact": FactType.Graduation,
        # no Event
    },
    "IMMI": {
        "Fact": FactType.Immigration,
        "Event": EventType.Immigration,
    },
    "MIL": {
        "Fact": FactType.MilitaryService,
        # no Event
    },
    "NATI": {
        "Fact": FactType.Nationality,
        # no Event
    },
    "NATU": {
        "Fact": FactType.Naturalization,
        "Event": EventType.Naturalization,
    },
    "OCCU": {
        "Fact": FactType.Occupation,
        # no Event
    },
    "ORDN": {
        "Fact": FactType.Ordination,
        "Event": EventType.Ordination,
    },
    "DSCR": {
        "Fact": FactType.PhysicalDescription,
        # no Event
    },
    "PROB": {
        "Fact": FactType.Probate,
        # no Event
    },
    "PROP": {
        "Fact": FactType.Property,
        # no Event
    },
    "RELI": {
        "Fact": FactType.Religion,
        # no Event
    },
    "RESI": {
        "Fact": FactType.Residence,
        # no Event
    },
    "WILL": {
        "Fact": FactType.Will,
        # no Event
    },

    # Couple Relationship Fact / Event Types
    "ANUL": {
        "Fact": FactType.Annulment,
        "Event": EventType.Annulment,
    },
    "DIV": {
        "Fact": FactType.Divorce,
        "Event": EventType.Divorce,
    },
    "DIVF": {
        "Fact": FactType.DivorceFiling,
        "Event": EventType.DivorceFiling,
    },
    "ENGA": {
        "Fact": FactType.Engagement,
        "Event": EventType.Engagement,
    },
    "MARR": {
        "Fact": FactType.Marriage,
        "Event": EventType.Marriage,
    },
    "MARB": {
        "Fact": FactType.MarriageBanns,
        # no Event
    },
    "MARC": {
        "Fact": FactType.MarriageContract,
        # no Event
    },
    "MARL": {
        "Fact": FactType.MarriageLicense,
        # no Event
    },
    "MARS":{
        "Event": EventType.MarriageSettlment
    },
    "SEPA": {
        "Fact": FactType.Separation,
        # no Event
    },

}

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
                obj = Fact(type=fact_event_table[record.tag]['Fact'])
                return obj
            if 'Event' in fact_event_table[record.tag]:
                obj = Event(type=fact_event_table[record.tag]['Event'])
                return obj
            raise ValueError(
                f"tag '{record.tag}' found in map but has neither 'Fact' nor 'Event' key"
            )
        raise ValueError(f"{record.tag} not found in map")

class GedcomXRelationshipBuilder(GedcomXObject):
    """Placeholder builder for constructing complex GEDCOM relationship structures."""
    pass
