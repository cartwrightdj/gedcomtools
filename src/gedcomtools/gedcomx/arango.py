from typing import Dict, Any

from .gedcomx import GedcomX
from gedcomtools.loggingkit import setup_logging, get_log, LoggerSpec
mgr = setup_logging("gedcomtools")  # console-only
log = mgr.get_common()

def make_arango_graph_files(gedcomx: GedcomX) -> Dict[str,list]:
    graph_files = {'persons':[]}
    # PERSONS
    for person in gedcomx.persons:
        person_entry = {}
        person_entry['_key'] = person.id
        log.info(f'Building Person with id: {person.id}')
        person_entry['adbgDescription'] = person.names[0].nameForms[0].fullText
        person_entry['full_name'] = person.names[0].nameForms[0].fullText 
        try:
            person_entry['gender'] = person.gender.type.value.split("/")[-1]
        except:
            person_entry['gender'] = None

        facts = []
        for fact in person.facts:
            fact_desc = {}
            fact_desc['type'] = fact.type.value.split("/")[-1]
            fact_desc['adbgDescription'] = fact.type.value.split("/")[-1]
            if fact.date:
                fact_desc['data'] = fact.date.original
            if fact.place:
                fact_desc['place'] = fact.place.description
            facts.append(fact_desc)
        person_entry['facts'] = facts   

        log.info(f'{person_entry}')
        graph_files = ['persons'].append

    return graph_files