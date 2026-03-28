"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/arango.py
 Author:  David J. Cartwright
 Purpose: Build ArangoDB graph import files (vertices and edges) from a GedcomX object

 Created: 2025-08-25
 Updated:

======================================================================
"""
from typing import Dict

from gedcomtools.glog import get_logger
from .gedcomx import GedcomX
from .fact import FactType
log = get_logger(__name__)

def make_arango_graph_files(gedcomx: GedcomX) -> Dict[str, list]:
    graph_files = {
        "persons": [],
        "relationships": []
    }

    # -----------------
    # PERSONS (vertices)
    # -----------------
    for person in gedcomx.persons:
        person_entry = {}
        person_entry["_key"] = person.id.replace("@", "")
        log.info(f"Building Person with id: {person.id}")

        person_entry["adbgDescription"] = person.names[0].nameForms[0].fullText
        person_entry["full_name"] = person.names[0].nameForms[0].fullText

        try:
            gender_type = person.gender.type if person.gender else None
            person_entry["gender"] = gender_type.value.split("/")[-1] if gender_type and gender_type.value else None
        except Exception:
            person_entry["gender"] = None

        facts = []
        for fact in person.facts:
            fact_type_val = fact.type.value if fact.type and fact.type.value else ""
            fact_desc = {
                "type": fact_type_val.split("/")[-1],
                "adbgDescription": fact_type_val.split("/")[-1],
            }

            if fact.type == FactType.Birth and fact.date:
                person_entry["DOB"] = fact.date.original

            if fact.date and fact.date.original is not None:
                fact_desc["date"] = fact.date.original
            if fact.place and fact.place.descriptionRef is not None:
                fact_desc["place"] = fact.place.descriptionRef.id or ""

            facts.append(fact_desc)

        person_entry["facts"] = facts
        graph_files["persons"].append(person_entry)

    # -----------------------
    # RELATIONSHIPS (edges)
    # -----------------------
    for rel in gedcomx.relationships:
        edge = {}
        log.info(f"Processing Relationship: {rel.id}")
        # clean IDs like @I123@
        if not (rel.person1 and rel.person2):
            #TODO log malformed relationship
            continue
        p1 = rel.person1.id.split("#")[-1].replace("@", "")
        p2 = rel.person2.id.split("#")[-1].replace("@", "")

        edge["_from"] = f"knPersons/{p1}"
        edge["_to"] = f"knPersons/{p2}"

        rel_type_val = rel.type.value if rel.type and rel.type.value else ""
        edge["type"] = rel_type_val.split("/")[-1]
        edge["adbgDescription"] = edge["type"]

        if rel.id:
            edge["_key"] = rel.id.replace("@", "")

        graph_files["relationships"].append(edge)

    return graph_files
