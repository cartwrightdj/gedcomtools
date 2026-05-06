"""Shared GEDCOM tag to GedcomX type mappings."""

from __future__ import annotations

from typing import Optional

from .event import EventType
from .fact import FactType


GEDCOM_TAG_TO_FACT_TYPE: dict[str, FactType] = {
    "CHR": FactType.AdultChristening,
    "EVEN": FactType.Amnesty,
    "BAPM": FactType.Baptism,
    "BARM": FactType.BarMitzvah,
    "BASM": FactType.BatMitzvah,
    "BIRT": FactType.Birth,
    "BIRT, CHR": FactType.Birth,
    "BLES": FactType.Blessing,
    "BURI": FactType.Burial,
    "CAST": FactType.Caste,
    "CENS": FactType.Census,
    "CIRC": FactType.Circumcision,
    "CONF": FactType.Confirmation,
    "CREM": FactType.Cremation,
    "DEAT": FactType.Death,
    "EDUC": FactType.Education,
    "EMIG": FactType.Emigration,
    "FCOM": FactType.FirstCommunion,
    "GRAD": FactType.Graduation,
    "IMMI": FactType.Immigration,
    "MIL": FactType.MilitaryService,
    "NATI": FactType.Nationality,
    "NATU": FactType.Naturalization,
    "OCCU": FactType.Occupation,
    "ORDN": FactType.Ordination,
    "DSCR": FactType.PhysicalDescription,
    "PROB": FactType.Probate,
    "PROP": FactType.Property,
    "RELI": FactType.Religion,
    "RESI": FactType.Residence,
    "RETI": FactType.Retirement,
    "TITL": FactType.OfficialPosition,
    "WILL": FactType.Will,
    "ANUL": FactType.Annulment,
    "DIV": FactType.Divorce,
    "DIVF": FactType.DivorceFiling,
    "ENGA": FactType.Engagement,
    "MARR": FactType.Marriage,
    "MARB": FactType.MarriageBanns,
    "MARC": FactType.MarriageContract,
    "MARL": FactType.MarriageLicense,
    "SEPA": FactType.Separation,
    "ADOP": FactType.AdoptiveParent,
}


GEDCOM_TAG_TO_EVENT_TYPE: dict[str, EventType] = {
    "ADOP": EventType.Adoption,
    "CHR": EventType.AdultChristening,
    "BAPM": EventType.Baptism,
    "BARM": EventType.BarMitzvah,
    "BASM": EventType.BatMitzvah,
    "BIRT": EventType.Birth,
    "BIRT, CHR": EventType.Birth,
    "BLES": EventType.Blessing,
    "BURI": EventType.Burial,
    "CENS": EventType.Census,
    "CIRC": EventType.Circumcision,
    "CONF": EventType.Confirmation,
    "CREM": EventType.Cremation,
    "DEAT": EventType.Death,
    "EDUC": EventType.Education,
    "EMIG": EventType.Emigration,
    "FCOM": EventType.FirstCommunion,
    "IMMI": EventType.Immigration,
    "NATU": EventType.Naturalization,
    "ORDN": EventType.Ordination,
    "RETI": EventType.Retirement,
    "ANUL": EventType.Annulment,
    "DIV": EventType.Divorce,
    "DIVF": EventType.DivorceFiling,
    "ENGA": EventType.Engagement,
    "MARR": EventType.Marriage,
    "MARS": EventType.MarriageSettlement,
}


GEDCOM_TAG_TO_FACT_EVENT_TYPE: dict[str, dict[str, FactType | EventType]] = {
    tag: {
        **({"Fact": fact_type} if (fact_type := GEDCOM_TAG_TO_FACT_TYPE.get(tag)) else {}),
        **({"Event": event_type} if (event_type := GEDCOM_TAG_TO_EVENT_TYPE.get(tag)) else {}),
    }
    for tag in sorted(set(GEDCOM_TAG_TO_FACT_TYPE) | set(GEDCOM_TAG_TO_EVENT_TYPE))
}


def fact_from_even_tag(even_value: str) -> Optional[FactType]:
    """Return the GedcomX FactType mapped from a GEDCOM EVEN tag, or None."""
    return GEDCOM_TAG_TO_FACT_TYPE.get(even_value)


def event_from_even_tag(even_value: str) -> Optional[EventType]:
    """Return the GedcomX EventType mapped from a GEDCOM EVEN tag, or None."""
    return GEDCOM_TAG_TO_EVENT_TYPE.get(even_value)


# ---------------------------------------------------------------------------
# GEDCOM 7 tag → GedcomX URI (individual events/attributes and couple facts)
# CHR maps to Christening (at-birth) in G7, vs AdultChristening in G5 above.
# ---------------------------------------------------------------------------

GEDCOM7_INDI_FACT_MAP: dict[str, str] = {
    "BIRT": "http://gedcomx.org/Birth",
    "CHR":  "http://gedcomx.org/Christening",
    "DEAT": "http://gedcomx.org/Death",
    "BURI": "http://gedcomx.org/Burial",
    "CREM": "http://gedcomx.org/Cremation",
    "ADOP": "http://gedcomx.org/Adoption",
    "BAPM": "http://gedcomx.org/Baptism",
    "BARM": "http://gedcomx.org/BarMitzvah",
    "BASM": "http://gedcomx.org/BatMitzvah",
    "BLES": "http://gedcomx.org/Blessing",
    "CENS": "http://gedcomx.org/Census",
    "CONF": "http://gedcomx.org/Confirmation",
    "EMIG": "http://gedcomx.org/Emigration",
    "GRAD": "http://gedcomx.org/Graduation",
    "IMMI": "http://gedcomx.org/Immigration",
    "NATU": "http://gedcomx.org/Naturalization",
    "ORDN": "http://gedcomx.org/Ordination",
    "PROB": "http://gedcomx.org/Probate",
    "RETI": "http://gedcomx.org/Retirement",
    "WILL": "http://gedcomx.org/Will",
    "RESI": "http://gedcomx.org/Residence",
    "OCCU": "http://gedcomx.org/Occupation",
    "TITL": "http://gedcomx.org/OfficialPosition",
    "RELI": "http://gedcomx.org/Religion",
    "NATI": "http://gedcomx.org/Nationality",
}

GEDCOM7_FAM_FACT_MAP: dict[str, str] = {
    "MARR": "http://gedcomx.org/Marriage",
    "DIV":  "http://gedcomx.org/Divorce",
    "ENGA": "http://gedcomx.org/Engagement",
    "MARB": "http://gedcomx.org/MarriageBanns",
    "MARC": "http://gedcomx.org/MarriageContract",
    "MARL": "http://gedcomx.org/MarriageLicense",
    "MARS": "http://gedcomx.org/Separation",
    "ANUL": "http://gedcomx.org/Annulment",
    "DIVF": "http://gedcomx.org/DivorceFiling",
}
