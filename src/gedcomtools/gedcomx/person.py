from typing import List, Optional
from urllib.parse import urljoin

"""
======================================================================
 Project: Gedcom-X
 File:    Person.py
 Author:  David J. Cartwright
 Purpose: Python Object representation of GedcomX Person Type

 Created: 2025-08-25
 Updated:
   - 2025-08-31: _as_dict_ to only create entries in dict for fields that hold data
   - 2025-09-03: _from_json_ refactor
   - 2025-09-09: added schema_class
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Types
======================================================================
"""
from .attribution import Attribution
from .conclusion import ConfidenceLevel
from .date import Date
from .evidence_reference import EvidenceReference

from .extensible import Extensible
from .fact import Fact, FactType
from .gender import Gender, GenderType
from .identifier import IdentifierList
from ..logging_hub import hub, logging
from .name import Name, QuickName
from .note import Note
from .resource import Resource
from .schemas import extensible
from .source_reference import SourceReference
from .subject import Subject

log = logging.getLogger("gedcomx")
deserial_log = "gedcomx.deserialization"


@extensible(toplevel=True)
class Person(Extensible,Subject):
    """A person in the system.

    Args:
        id (str):      Unique identifier for this person.
        name (str):    Full name.
        birth (date):  Birth date (YYYY-MM-DD).
        friends (List[Person], optional): List of friends. Defaults to None.

    Raises:
        ValueError: If `id` is not a valid UUID.
    """
    identifier = 'http://gedcomx.org/v1/Person'
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self, id: Optional[str] = None,
             lang: str | None = None,
             sources: Optional[List[SourceReference]] = None,
             analysis: Optional[Resource] = None,
             notes: Optional[List[Note]] = None,
             confidence: Optional[ConfidenceLevel] = None,
             attribution: Optional[Attribution] = None,
             extracted: Optional[bool] = None,
             evidence: Optional[List[EvidenceReference]] = None,
             media: Optional[List[SourceReference]] = None,
             identifiers: Optional[IdentifierList] = None,
             private: Optional[bool] = None,
             gender: Optional[Gender] = None,
             names: Optional[List[Name]] = None,
             facts: Optional[List[Fact]] = None,
             living: Optional[bool] = None,):
             #links: Optional[_rsLinks] = None,) -> None:
        # Call superclass initializer if needed
        super().__init__(id, lang, sources, analysis, notes, confidence, attribution, extracted, evidence, media, identifiers)
        
        # Initialize mutable attributes to empty lists if None
        self.sources = sources if sources is not None else []
        self.notes = notes if notes is not None else []
        self.evidence = evidence if evidence is not None else []
        self.media = media if media is not None else []
        self.names = names if names is not None else []
        self.facts = facts if facts is not None else []

        self.private = private
        self.gender = gender

        self.living = living       #TODO This is from familysearch API

        self._relationships = []
          
    def add_fact(self, fact_to_add: Fact) -> bool:
        if fact_to_add and isinstance(fact_to_add,Fact):
            for current_fact in self.facts:
                if fact_to_add == current_fact:
                    return False
            self.facts.append(fact_to_add)
            return True
        return False

    def add_name(self, name_to_add: Name) -> bool:
        if len(self.names) > 5: 
            for name in self.names:
                print(name)
            raise
        if name_to_add and isinstance(name_to_add, Name):
            for current_name in self.names:
                if name_to_add == current_name:
                    return False
            self.names.append(name_to_add)
            return True
        return False
    
    def _add_relationship(self, relationship_to_add: object):
        from .relationship import Relationship
        if isinstance(relationship_to_add,Relationship):
            self._relationships.append(relationship_to_add)
        else:
            raise ValueError()
    
    def display(self):
        display = {
        "ascendancyNumber": "1",
        "deathDate": "from 2001 to 2005",
        "descendancyNumber": "1",
        "gender": self.gender.type if self.gender else 'Unknown',
        "lifespan": "-2005",
        "name": self.names[0].nameForms[0].fullText
            }
        
        return display
    
    @property
    def name(self) -> str:
        return self.names[0].nameForms[0].fullText

    @property
    def to_dict(self):
        from .serialization import Serialization
        return Serialization.serialize(self)
                
           
    @classmethod
    def from_json(cls, data: dict, context = None) -> "Person":
        def _to_bool(v):
            if isinstance(v, str):
                return v.strip().lower() in ("1", "true", "yes", "y", "t")
            return bool(v)
        with hub.use(deserial_log):
            log.debug("Deserializing a Person")
            person_data: dict = Subject.dict_from_json(data,context)
            if (private := data.get("private")) is not None:
                person_data["private"] = _to_bool(private)
            if (living := data.get("living")) is not None:
                person_data["living"] = _to_bool(living)
            if (gender := data.get("gender")) is not None:
                person_data["gender"] = Gender.from_json(gender, context)
            if (names := data.get("names")) is not None:
                person_data["names"] = [Name.from_json(n, context) for n in names]
            if (facts := data.get("facts")) is not None:
                person_data["facts"] = [Fact.from_json(f, context) for f in facts]
            
            diff = data.keys() - person_data.keys()
            if diff:
                log.debug("Deserialization: unrecognised keys {}", diff)

        return cls(**person_data)

    @classmethod
    def from_familysearch(cls, pid: str, token: str, *, base_url: Optional[str] = None):
        from .serialization import Serialization
        """
        Fetch a single person by PID from FamilySearch and return a Person.
        - pid: e.g. "KPHP-4B4"
        - token: OAuth2 access token (Bearer)
        - base_url: override API base (defaults to settings.FS_API_BASE or prod)
        """
        import requests
        default_base = "https://apibeta.familysearch.org/platform/"

        base = (base_url or default_base).rstrip("/") + "/"
        url = urljoin(base, f"tree/persons/{pid}")

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }

        resp = requests.get(url, headers=headers, timeout=(5, 30))
        resp.raise_for_status()

        payload = resp.json()
        persons = payload.get("persons") or []

        # Prefer exact match on PID, else first item if present
        person_json = next((p for p in persons if (p.get("id") == pid)), None) or (persons[0] if persons else None)
        if not person_json:
            raise ValueError(f"FamilySearch returned no person for PID {pid}")

        # Keep your existing deserialization helper
        return Person.from_json(person_json)    

class QuickPerson:
    """A GedcomX Person Data Type created with basic information.

    Underlying GedcomX Types are created for you.
        
    Args:
        name (str):    Full name.
        birth (date,Optional):  Birth date (YYYY-MM-DD).
        death (date, Optional)

        

    Raises:
        ValueError: If `id` is not a valid UUID.
    """
    def __new__(cls, name: str, dob: Optional[str] = None, dod: Optional[str] = None):
        # Build facts from args
        facts = []
        if dob:
            facts.append(Fact(type=FactType.Birth, date=Date(original=dob)))
        if dod:
            facts.append(Fact(type=FactType.Death, date=Date(original=dod)))

        # Return the different class instance
        return Person(facts=facts, names=[QuickName(name=name)] if name else None)