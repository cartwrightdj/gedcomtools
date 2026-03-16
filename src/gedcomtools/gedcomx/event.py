from enum import Enum
from typing import Any, Dict, List, Optional

"""
======================================================================
 Project: Gedcom-X
 File:    Event.py
 Author:  David J. Cartwright
 Purpose: Python Object representation of GedcomX Event Type, EventType, EventRole, EventRoleType Types

 Created: 2025-08-25
 Updated:
   - 2025-08-31: fixed mutible [] in init, replaced List[Identifer] with IdentifierList
   - 2025-09-03: _from_json_ refactor
   - 2025-09-04: changed _as_dict_ to std dict creation and removed call to serailization
   - 2025-09-09: added schema_class
   
======================================================================
"""

"""
======================================================================
GEDCOM Module Type Imports
======================================================================
"""
from .attribution import Attribution
from .conclusion import ConfidenceLevel, Conclusion
from .date import Date
from .evidence_reference import EvidenceReference
from .identifier import IdentifierList
from .note import Note
from .place_reference import PlaceReference
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

@extensible()
class EventRoleType(Enum):
    Principal = "http://gedcomx.org/Principal"
    Participant = "http://gedcomx.org/Participant"
    Official = "http://gedcomx.org/Official"
    Witness = "http://gedcomx.org/Witness"
    
    @property
    def description(self):
        descriptions = {
            EventRoleType.Principal: "The person is the principal person of the event. For example, the principal of a birth event is the person that was born.",
            EventRoleType.Participant: "A participant in the event.",
            EventRoleType.Official: "A person officiating the event.",
            EventRoleType.Witness: "A witness of the event."
        }
        return descriptions.get(self, "No description available.")

@extensible()
class EventRole(Conclusion):
    identifier = 'http://gedcomx.org/v1/EventRole'
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self,
                 id: Optional[str] = None,
                 lang: Optional[str] = None,
                 sources: Optional[List[SourceReference]] = [],
                 analysis: Optional[Resource] = None,
                 notes: Optional[List[Note]] = [],
                 confidence: Optional[ConfidenceLevel] = None,
                 attribution: Optional[Attribution] = None,
                 person: Optional[Resource] = None,
                 type: Optional[EventRoleType] = None,
                 details: Optional[str] = None) -> None:
        super().__init__(id, lang, sources, analysis, notes, confidence, attribution)
        self.person = person
        self.type = type
        self.details = details
        
    def __str__(self) -> str:
        parts = []
        if self.type is not None:
            # assume enums expose .name
            parts.append(f"type={getattr(self.type, 'name', str(self.type))}")
        if self.person is not None:
            # assume classes have meaningful __str__
            parts.append(f"person={self.person}")
        if self.details:
            parts.append(f"details={self.details!r}")
        if getattr(self, "id", None):
            parts.append(f"id={self.id!r}")
        return f"EventRole({', '.join(parts)})" if parts else "EventRole()"

    def __repr__(self) -> str:
        # assume enums expose .name and .value
        if self.type is not None:
            tcls = self.type.__class__.__name__
            tname = getattr(self.type, "name", str(self.type))
            tval = getattr(self.type, "value", self.type)
            type_repr = f"<{tcls}.{tname}: {tval!r}>"
        else:
            type_repr = "None"
        return (
            f"{self.__class__.__name__}("
            f"id={getattr(self, 'id', None)!r}, "
            f"lang={getattr(self, 'lang', None)!r}, "
            f"type={type_repr}, "
            f"person={self.person!r}, "
            f"details={self.details!r})"
        )
    
    @property
    def to_dict(self):
        type_as_dict = super().to_dict
        if self.person:
            type_as_dict['person'] = Resource(target=self.person).to_dict
        if self.type is not None:
            type_as_dict['type'] = getattr(self.type, 'value', self.type)
        if self.details:
            type_as_dict['details'] = self.details

        return type_as_dict if type_as_dict != {} else None


    @classmethod
    def from_json(cls,data,context):
        
        if not isinstance(data, dict):
            print("Event: from:",data)
            raise TypeError(f"{cls.__name__}._from_json_ expected dict or str, got {type(data)}")
        event_role_data = Conclusion.dict_from_json(data,context)
        event_role_data: Dict[str, Any] = {}

        # person: Person | Resource | URI string
        if (p := data.get("person")) is not None:
            event_role_data["person"] = Resource.from_json(p, context)
            

        # type: EventRoleType (enum-ish)
        if (typ := data.get("type")) is not None:
            event_role_data["type"] = EventRoleType(typ)
            

        # details: TextValue | str
        if (det := data.get("details")) is not None:
            event_role_data["details"] = det  # str or passthrough

        return cls(**event_role_data)
    
class EventType(Enum):
    Adoption = "http://gedcomx.org/Adoption"
    AdultChristening = "http://gedcomx.org/AdultChristening"
    Annulment = "http://gedcomx.org/Annulment"
    Baptism = "http://gedcomx.org/Baptism"
    BarMitzvah = "http://gedcomx.org/BarMitzvah"
    BatMitzvah = "http://gedcomx.org/BatMitzvah"
    Birth = "http://gedcomx.org/Birth"
    Blessing = "http://gedcomx.org/Blessing"
    Burial = "http://gedcomx.org/Burial"
    Census = "http://gedcomx.org/Census"
    Christening = "http://gedcomx.org/Christening"
    Circumcision = "http://gedcomx.org/Circumcision"
    Confirmation = "http://gedcomx.org/Confirmation"
    Cremation = "http://gedcomx.org/Cremation"
    Death = "http://gedcomx.org/Death"
    Divorce = "http://gedcomx.org/Divorce"
    DivorceFiling = "http://gedcomx.org/DivorceFiling"
    Education = "http://gedcomx.org/Education"
    Engagement = "http://gedcomx.org/Engagement"
    Emigration = "http://gedcomx.org/Emigration"
    Excommunication = "http://gedcomx.org/Excommunication"
    FirstCommunion = "http://gedcomx.org/FirstCommunion"
    Funeral = "http://gedcomx.org/Funeral"
    Immigration = "http://gedcomx.org/Immigration"
    LandTransaction = "http://gedcomx.org/LandTransaction"
    Marriage = "http://gedcomx.org/Marriage"
    MilitaryAward = "http://gedcomx.org/MilitaryAward"
    MilitaryDischarge = "http://gedcomx.org/MilitaryDischarge"
    Mission = "http://gedcomx.org/Mission"
    MoveFrom = "http://gedcomx.org/MoveFrom"
    MoveTo = "http://gedcomx.org/MoveTo"
    Naturalization = "http://gedcomx.org/Naturalization"
    Ordination = "http://gedcomx.org/Ordination"
    Retirement = "http://gedcomx.org/Retirement"
    MarriageSettlment = 'https://gedcom.io/terms/v7/MARS'
    
    @property
    def description(self):
        descriptions = {
            EventType.Adoption: "An adoption event.",
            EventType.AdultChristening: "An adult christening event.",
            EventType.Annulment: "An annulment event of a marriage.",
            EventType.Baptism: "A baptism event.",
            EventType.BarMitzvah: "A bar mitzvah event.",
            EventType.BatMitzvah: "A bat mitzvah event.",
            EventType.Birth: "A birth event.",
            EventType.Blessing: "An official blessing event, such as at the hands of a clergy member or at another religious rite.",
            EventType.Burial: "A burial event.",
            EventType.Census: "A census event.",
            EventType.Christening: "A christening event at birth. Note: use AdultChristening for a christening event as an adult.",
            EventType.Circumcision: "A circumcision event.",
            EventType.Confirmation: "A confirmation event (or other rite of initiation) in a church or religion.",
            EventType.Cremation: "A cremation event after death.",
            EventType.Death: "A death event.",
            EventType.Divorce: "A divorce event.",
            EventType.DivorceFiling: "A divorce filing event.",
            EventType.Education: "An education or educational achievement event (e.g., diploma, graduation, scholarship, etc.).",
            EventType.Engagement: "An engagement to be married event.",
            EventType.Emigration: "An emigration event.",
            EventType.Excommunication: "An excommunication event from a church.",
            EventType.FirstCommunion: "A first communion event.",
            EventType.Funeral: "A funeral event.",
            EventType.Immigration: "An immigration event.",
            EventType.LandTransaction: "A land transaction event.",
            EventType.Marriage: "A marriage event.",
            EventType.MilitaryAward: "A military award event.",
            EventType.MilitaryDischarge: "A military discharge event.",
            EventType.Mission: "A mission event.",
            EventType.MoveFrom: "An event of a move (i.e., change of residence) from a location.",
            EventType.MoveTo: "An event of a move (i.e., change of residence) to a location.",
            EventType.Naturalization: "A naturalization event (i.e., acquisition of citizenship and nationality).",
            EventType.Ordination: "An ordination event.",
            EventType.Retirement: "A retirement event."
        }
        return descriptions.get(self, "No description available.")

    @staticmethod
    def guess(description):
        keywords_to_event_type = {
            "adoption": EventType.Adoption,
            "christening": EventType.Christening,
            "annulment": EventType.Annulment,
            "baptism": EventType.Baptism,
            "bar mitzvah": EventType.BarMitzvah,
            "bat mitzvah": EventType.BatMitzvah,
            "birth": EventType.Birth,
            "blessing": EventType.Blessing,
            "burial": EventType.Burial,
            "census": EventType.Census,
            "circumcision": EventType.Circumcision,
            "confirmation": EventType.Confirmation,
            "cremation": EventType.Cremation,
            "death": EventType.Death,
            "divorce": EventType.Divorce,
            "divorce filing": EventType.DivorceFiling,
            "education": EventType.Education,
            "engagement": EventType.Engagement,
            "emigration": EventType.Emigration,
            "excommunication": EventType.Excommunication,
            "first communion": EventType.FirstCommunion,
            "funeral": EventType.Funeral,
            "arrival": EventType.Immigration,
            "immigration": EventType.Immigration,
            "land transaction": EventType.LandTransaction,
            "marriage": EventType.Marriage,
            "military award": EventType.MilitaryAward,
            "military discharge": EventType.MilitaryDischarge,
            "mission": EventType.Mission,
            "move from": EventType.MoveFrom,
            "move to": EventType.MoveTo,
            "naturalization": EventType.Naturalization,
            "ordination": EventType.Ordination,
            "retirement": EventType.Retirement,
        }

        description_lower = description.lower()

        for keyword, event_type in keywords_to_event_type.items():
            if keyword in description_lower:
                return event_type

        return None  # Default to UNKNOWN if no match is found

@extensible(toplevel=True)
class Event(Subject):
    identifier = 'http://gedcomx.org/v1/Event'
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self,
                 id: Optional[str] = None,
                 lang: Optional[str] = None,
                 sources: Optional[List[SourceReference]] = None,
                 analysis: Optional[Resource] = None,
                 notes: Optional[List[Note]] = None,
                 confidence: Optional[ConfidenceLevel] = None,
                 attribution: Optional[Attribution] = None,
                 extracted: Optional[bool] = False,
                 evidence: Optional[List[EvidenceReference]] = None,
                 media: Optional[List[SourceReference]] = None,
                 #identifiers: Optional[List[Identifier]] = [],
                 identifiers: Optional[IdentifierList] = None,
                 type: Optional[EventType] = None,
                 date: Optional[Date] = None,
                 place: Optional[PlaceReference] = None,
                 roles: Optional[List[EventRole]] = []) -> None:
        super().__init__(id, lang, sources, analysis, notes, confidence, attribution, extracted, evidence, media, identifiers)

        self.type = type if type and isinstance(type, EventType) else None
        self.date = date if date and isinstance(date, Date) else None               
        self.place = place if place and isinstance(place, PlaceReference) else None
        self.roles = roles if roles and isinstance(roles, list) else []
    
    @property
    def to_dict(self):
        from .serialization import Serialization
        type_as_dict = {}
        if self.type:
            type_as_dict['type'] = self.type.value
        if self.date:
            type_as_dict['date'] = self.date.to_dict
        if self.place:
            type_as_dict['place'] = self.place.to_dict 
        if self.roles:
            #print(self.roles)
            for role in self.roles:
                if isinstance(role,list):
                    assert False
            type_as_dict['roles'] = [role.to_dict for role in self.roles]
        
        return type_as_dict if type_as_dict != {} else None
  
    
    @classmethod
    def from_json(cls, data: Dict[str, Any], context: Any = None) -> "Event":
        if not isinstance(data, dict):
            raise TypeError(f"{cls.__name__}._from_json_ expected dict, got {type(data)}")

        event_data: Dict[str, Any] = Subject.dict_from_json(data,context)

        # Enum / type
        if (typ := data.get("type")) is not None:
            event_data["type"] = EventType(typ)
            

        # Objects
        if (dt := data.get("date")) is not None:
            event_data["date"] = Date.from_json(dt, context)

        if (pl := data.get("place")) is not None:
            event_data["place"] = PlaceReference.from_json(pl, context)

        # Lists
        if (rls := data.get("roles")) is not None:
            event_data["roles"] = [EventRole.from_json(r, context) for r in rls]

        return cls(**event_data)