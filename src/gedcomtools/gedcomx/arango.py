from typing import Dict, Any

from .gedcomx import GedcomX
from .fact import FactType
from gedcomtools.loggingkit import setup_logging, get_log, LoggerSpec
log = get_log(__name__)

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
            person_entry["gender"] = person.gender.type.value.split("/")[-1]
        except Exception:
            person_entry["gender"] = None

        facts = []
        for fact in person.facts:
            fact_desc = {
                "type": fact.type.value.split("/")[-1],
                "adbgDescription": fact.type.value.split("/")[-1],
            }

            if fact.type == FactType.Birth and fact.date:
                person_entry["DOB"] = fact.date.original

            if fact.date:
                fact_desc["date"] = fact.date.original
            if fact.place:
                fact_desc["place"] = fact.place.description.id

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

        edge["type"] = rel.type.value.split("/")[-1]
        edge["adbgDescription"] = edge["type"]

        if rel.id:
            edge["_key"] = rel.id.replace("@", "")

        graph_files["relationships"].append(edge)

    return graph_files
