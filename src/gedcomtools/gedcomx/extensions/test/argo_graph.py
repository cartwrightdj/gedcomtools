


"""
======================================================================
 Project: Gedcom-X
 File:    desc_ext.py
 Author:  David J. Cartwright
 Purpose: Extnsion to add certain human readbale fields to complexe Gedcom-X Objects

 Created: 2023-02-23
 Updated:
   - 2023-02-23: arango_description expanded
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================="""
from ...schemas import SCHEMA, schema_property_plugin, apply_schema_property, bind_schema_property
from gedcomtools.gedcomx.person import Person



def ext_description_set(self) -> str:
    return self.names[0].nameForms[0].fullText

def ext_description_get(self) -> dict:
    person = {
        "name": None,
        "gender": None,
        "living": None,
        "facts": []
    }

    # -------------------
    # Name
    # -------------------
    try:
        person["name"] = self.names[0].nameForms[0].fullText
    except (IndexError, AttributeError):
        person["name"] = "Unknown Person"

    # -------------------
    # Gender
    # -------------------
    if getattr(self, "gender", None) and getattr(self.gender, "type", None):
        try:
            person["gender"] = self.gender.type.name
        except AttributeError:
            person["gender"] = None

    # -------------------
    # Facts
    # -------------------
    for fact in getattr(self, "facts", []):
        try:
            fact_entry = {
                "type": None,
                "date": None,
                "place": None
            }

            # Fact Type
            if getattr(fact, "type", None):
                try:
                    fact_entry["type"] = fact.type.name
                except AttributeError:
                    fact_entry["type"] = "Unknown"

            # Date
            if getattr(fact, "date", None):
                fact_entry["date"] = getattr(fact.date, "original", None)

            # Place
            if getattr(fact, "place", None):
                fact_entry["place"] = getattr(fact.place, "original", None)

            person["facts"].append(fact_entry)

        except AttributeError:
            continue

    # -------------------
    # Living Status
    # -------------------
    if hasattr(self, "living"):
        person["living"] = bool(self.living)

    return person

def ext_emb_narrative_get(self) -> str:
    lines = []

    lines.append("TYPE: Person")

    # Primary name
    try:
        primary_name = self.names[0].nameForms[0].fullText
    except (IndexError, AttributeError):
        primary_name = "Unknown"
    lines.append(f"NAME: {primary_name}")

    # Alt names
    try:
        alt_names = [
            n.nameForms[0].fullText
            for n in self.names[1:]
            if n.nameForms and n.nameForms[0].fullText != primary_name
        ]
        lines.append(f"ALT_NAMES: {', '.join(alt_names) if alt_names else 'none'}")
    except (IndexError, AttributeError):
        lines.append("ALT_NAMES: none")

    # Gender
    if self.gender and self.gender.type:
        lines.append(f"GENDER: {self.gender.type.name}")

    # Vitals - birth and death
    vitals = []
    residences = []
    year_hints = []
    other_facts = []

    for fact in self.facts:
        try:
            fact_name = fact.type.name if fact.type else None
            date_str = fact.date.original if fact.date else None
            place_str = fact.place.original if fact.place and hasattr(fact.place, 'original') else None

            if date_str:
                year = date_str.split()[-1] if date_str else None
                if year and year.isdigit():
                    year_hints.append(year)

            if fact_name in ("Birth", "Death", "Christening", "Burial"):
                detail = f"{fact_name.lower()} {date_str}" if date_str else fact_name.lower()
                if place_str:
                    detail += f" in {place_str}"
                vitals.append(detail)

            elif fact_name == "Residence":
                detail = date_str if date_str else ""
                if place_str:
                    detail += f" {place_str}" if detail else place_str
                if detail:
                    residences.append(detail)

            else:
                detail = fact_name or "Unknown"
                if date_str:
                    detail += f": {date_str}"
                if place_str:
                    detail += f" at {place_str}"
                other_facts.append(detail)

        except AttributeError:
            continue

    lines.append(f"VITALS: {'; '.join(vitals) if vitals else 'none'}")
    lines.append(f"RESIDENCES: {', '.join(residences) if residences else 'none'}")

    if other_facts:
        lines.append(f"OTHER: {'; '.join(other_facts)}")

    if self.living is not None:
        lines.append(f"LIVING: {'yes' if self.living else 'no'}")

    lines.append(f"YEAR_HINT: {year_hints[0] if year_hints else 'none'}")

    return "\n".join(lines)


bind_schema_property(
    Person,
    ext_description_get,
    fset=ext_description_set,
    name="ext_description",
    schema=SCHEMA,
)

bind_schema_property(
    Person,
    ext_emb_narrative_get,
    fset=None,
    name="Narrative_for_Embedding",
    schema=SCHEMA,
)
