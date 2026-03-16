import difflib
import re

from enum import Enum
from typing import List, Optional, Dict, Any, Union, TYPE_CHECKING
"""
======================================================================
 Project: Gedcom-X
 File:    fact.py
 Author:  David J. Cartwright
 Purpose: 

 Created: 2025-08-25
 Updated:
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
from .conclusion import Conclusion, ConfidenceLevel
from .date import Date
from .document import Document
from .note import Note
from .place_reference import PlaceReference
from .qualifier import Qualifier
from .resource import Resource
from .schemas import extensible
from .source_reference import SourceReference
from ..logging_hub import hub, logging
"""
======================================================================
Logging
======================================================================
"""
log = logging.getLogger("gedcomx")
serial_log = "gedcomx.serialization"
#=====================================================================


class FactType(Enum):
    # Person Fact Types
    Adoption = "http://gedcomx.org/Adoption"
    AdultChristening = "http://gedcomx.org/AdultChristening"
    Amnesty = "http://gedcomx.org/Amnesty"
    AncestralHall = "http://gedcomx.org/AncestralHall"
    AncestralPoem = "http://gedcomx.org/AncestralPoem"
    Apprenticeship = "http://gedcomx.org/Apprenticeship"
    Arrest = "http://gedcomx.org/Arrest"
    Award = "http://gedcomx.org/Award"
    Baptism = "http://gedcomx.org/Baptism"
    BarMitzvah = "http://gedcomx.org/BarMitzvah"
    BatMitzvah = "http://gedcomx.org/BatMitzvah"
    Birth = "http://gedcomx.org/Birth"
    BirthNotice = "http://gedcomx.org/BirthNotice"
    Blessing = "http://gedcomx.org/Blessing"
    Branch = "http://gedcomx.org/Branch"
    Burial = "http://gedcomx.org/Burial"
    Caste = "http://gedcomx.org/Caste"
    Census = "http://gedcomx.org/Census"
    Christening = "http://gedcomx.org/Christening"
    Circumcision = "http://gedcomx.org/Circumcision"
    Clan = "http://gedcomx.org/Clan"
    Confirmation = "http://gedcomx.org/Confirmation"
    Court = "http://gedcomx.org/Court"
    Cremation = "http://gedcomx.org/Cremation"
    Death = "http://gedcomx.org/Death"
    Education = "http://gedcomx.org/Education"
    EducationEnrollment = "http://gedcomx.org/EducationEnrollment"
    Emigration = "http://gedcomx.org/Emigration"
    Enslavement = "http://gedcomx.org/Enslavement"
    Ethnicity = "http://gedcomx.org/Ethnicity"
    Excommunication = "http://gedcomx.org/Excommunication"
    FirstCommunion = "http://gedcomx.org/FirstCommunion"
    Funeral = "http://gedcomx.org/Funeral"
    GenderChange = "http://gedcomx.org/GenderChange"
    GenerationNumber = "http://gedcomx.org/GenerationNumber"
    Graduation = "http://gedcomx.org/Graduation"
    Heimat = "http://gedcomx.org/Heimat"
    Immigration = "http://gedcomx.org/Immigration"
    Imprisonment = "http://gedcomx.org/Imprisonment"
    Inquest = "http://gedcomx.org/Inquest"
    LandTransaction = "http://gedcomx.org/LandTransaction"
    Language = "http://gedcomx.org/Language"
    Living = "http://gedcomx.org/Living"
    MaritalStatus = "http://gedcomx.org/MaritalStatus"
    Medical = "http://gedcomx.org/Medical"
    MilitaryAward = "http://gedcomx.org/MilitaryAward"
    MilitaryDischarge = "http://gedcomx.org/MilitaryDischarge"
    MilitaryDraftRegistration = "http://gedcomx.org/MilitaryDraftRegistration"
    MilitaryInduction = "http://gedcomx.org/MilitaryInduction"
    MilitaryService = "http://gedcomx.org/MilitaryService"
    Mission = "http://gedcomx.org/Mission"
    MoveFrom = "http://gedcomx.org/MoveFrom"
    MoveTo = "http://gedcomx.org/MoveTo"
    MultipleBirth = "http://gedcomx.org/MultipleBirth"
    NationalId = "http://gedcomx.org/NationalId"
    Nationality = "http://gedcomx.org/Nationality"
    Naturalization = "http://gedcomx.org/Naturalization"
    NumberOfChildren = "http://gedcomx.org/NumberOfChildren"
    NumberOfMarriages = "http://gedcomx.org/NumberOfMarriages"
    Obituary = "http://gedcomx.org/Obituary"
    OfficialPosition = "http://gedcomx.org/OfficialPosition"
    Occupation = "http://gedcomx.org/Occupation"
    Ordination = "http://gedcomx.org/Ordination"
    Pardon = "http://gedcomx.org/Pardon"
    PhysicalDescription = "http://gedcomx.org/PhysicalDescription"
    Probate = "http://gedcomx.org/Probate"
    Property = "http://gedcomx.org/Property"
    Race = "http://gedcomx.org/Race"
    Religion = "http://gedcomx.org/Religion"
    Residence = "http://gedcomx.org/Residence"
    Retirement = "http://gedcomx.org/Retirement"
    Stillbirth = "http://gedcomx.org/Stillbirth"
    TaxAssessment = "http://gedcomx.org/TaxAssessment"
    Tribe = "http://gedcomx.org/Tribe"
    Will = "http://gedcomx.org/Will"
    Visit = "http://gedcomx.org/Visit"
    Yahrzeit = "http://gedcomx.org/Yahrzeit"

    # Couple Relationship Fact Types
    Annulment = "http://gedcomx.org/Annulment"
    CommonLawMarriage = "http://gedcomx.org/CommonLawMarriage"
    CivilUnion = "http://gedcomx.org/CivilUnion"
    Divorce = "http://gedcomx.org/Divorce"
    DivorceFiling = "http://gedcomx.org/DivorceFiling"
    DomesticPartnership = "http://gedcomx.org/DomesticPartnership"
    Engagement = "http://gedcomx.org/Engagement"
    Marriage = "http://gedcomx.org/Marriage"
    MarriageBanns = "http://gedcomx.org/MarriageBanns"
    MarriageContract = "http://gedcomx.org/MarriageContract"
    MarriageLicense = "http://gedcomx.org/MarriageLicense"
    MarriageNotice = "http://gedcomx.org/MarriageNotice"
    Separation = "http://gedcomx.org/Separation"

    # Parent-Child Relationship Fact Types
    AdoptiveParent = "http://gedcomx.org/AdoptiveParent"
    BiologicalParent = "http://gedcomx.org/BiologicalParent"
    ChildOrder = "http://gedcomx.org/ChildOrder"
    EnteringHeir = "http://gedcomx.org/EnteringHeir"
    ExitingHeir = "http://gedcomx.org/ExitingHeir"
    FosterParent = "http://gedcomx.org/FosterParent"
    GuardianParent = "http://gedcomx.org/GuardianParent"
    StepParent = "http://gedcomx.org/StepParent"
    SociologicalParent = "http://gedcomx.org/SociologicalParent"
    SurrogateParent = "http://gedcomx.org/SurrogateParent"
    Unknown = 'null'

    @classmethod
    def from_value(cls, value: str):
        for member in cls:
            if member.value == value:
                return member
        return FactType.Unknown
    
    @property
    def description(self):
        descriptions = {
            FactType.Adoption: "A fact of a person's adoption.",
            FactType.AdultChristening: "A fact of a person's christening or baptism as an adult.",
            FactType.Amnesty: "A fact of a person's amnesty.",
            FactType.AncestralHall: "A fact of a person's ancestral hall.",
            FactType.AncestralPoem: "A fact of a person's ancestral poem.",
            FactType.Apprenticeship: "A fact of a person's apprenticeship.",
            FactType.Arrest: "A fact of a person's arrest.",
            FactType.Award: "A fact of a person's award (medal, honor).",
            FactType.Baptism: "A fact of a person's baptism.",
            FactType.BarMitzvah: "A fact of a person's bar mitzvah.",
            FactType.BatMitzvah: "A fact of a person's bat mitzvah.",
            FactType.Birth: "A fact of a person's birth.",
            FactType.BirthNotice: "A fact of a person's birth notice.",
            FactType.Blessing: "A fact of an official blessing received by a person.",
            FactType.Branch: "A fact of a person's branch within an extended clan.",
            FactType.Burial: "A fact of the burial of a person's body after death.",
            FactType.Caste: "A fact of a person's caste.",
            FactType.Census: "A fact of a person's participation in a census.",
            FactType.Christening: "A fact of a person's christening at birth.",
            FactType.Circumcision: "A fact of a person's circumcision.",
            FactType.Clan: "A fact of a person's clan.",
            FactType.Confirmation: "A fact of a person's confirmation.",
            FactType.Court: "A fact of the appearance of a person in a court proceeding.",
            FactType.Cremation: "A fact of the cremation of a person's body.",
            FactType.Death: "A fact of the death of a person.",
            FactType.Education: "A fact of a person's education or educational achievement.",
            FactType.EducationEnrollment: "A fact of a person's enrollment in an educational program.",
            FactType.Emigration: "A fact of the emigration of a person.",
            FactType.Enslavement: "A fact of the enslavement of a person.",
            FactType.Ethnicity: "A fact of a person's ethnicity.",
            FactType.Excommunication: "A fact of a person's excommunication.",
            FactType.FirstCommunion: "A fact of a person's first communion.",
            FactType.Funeral: "A fact of a person's funeral.",
            FactType.GenderChange: "A fact of a person's gender change.",
            FactType.GenerationNumber: "A fact of a person's generation number.",
            FactType.Graduation: "A fact of a person's graduation.",
            FactType.Heimat: "A fact of a person's heimat.",
            FactType.Immigration: "A fact of a person's immigration.",
            FactType.Imprisonment: "A fact of a person's imprisonment.",
            FactType.Inquest: "A legal inquest, often after a suspicious death.",
            FactType.LandTransaction: "A fact of a land transaction by a person.",
            FactType.Language: "A fact of a language spoken by a person.",
            FactType.Living: "A fact of a record of a person's living for a period.",
            FactType.MaritalStatus: "A fact of a person's marital status.",
            FactType.Medical: "A fact of a person's medical record.",
            FactType.MilitaryAward: "A fact of a person's military award.",
            FactType.MilitaryDischarge: "A fact of a person's military discharge.",
            FactType.MilitaryDraftRegistration: "A fact of a person's draft registration.",
            FactType.MilitaryInduction: "A fact of a person's military induction.",
            FactType.MilitaryService: "A fact of a person's military service.",
            FactType.Mission: "A fact of a person's church mission.",
            FactType.MoveFrom: "A fact of a person's move from a location.",
            FactType.MoveTo: "A fact of a person's move to a new location.",
            FactType.MultipleBirth: "A fact of a person's birth as part of a multiple birth.",
            FactType.NationalId: "A fact of a person's national ID.",
            FactType.Nationality: "A fact of a person's nationality.",
            FactType.Naturalization: "A fact of a person's naturalization.",
            FactType.NumberOfChildren: "A fact of the number of children.",
            FactType.NumberOfMarriages: "A fact of a person's number of marriages.",
            FactType.Obituary: "A fact of a person's obituary.",
            FactType.OfficialPosition: "A fact of a person's official government position.",
            FactType.Occupation: "A fact of a person's occupation.",
            FactType.Ordination: "A fact of a person's ordination.",
            FactType.Pardon: "A fact of a person's legal pardon.",
            FactType.PhysicalDescription: "A fact of a person's physical description.",
            FactType.Probate: "A fact of a person's probate receipt.",
            FactType.Property: "A fact of a person's property.",
            FactType.Race: "A fact of a person's race.",
            FactType.Religion: "A fact of a person's religion.",
            FactType.Residence: "A fact of a person's residence.",
            FactType.Retirement: "A fact of a person's retirement.",
            FactType.Stillbirth: "A fact of a person's stillbirth.",
            FactType.TaxAssessment: "A fact of a person's tax assessment.",
            FactType.Tribe: "A fact of a person's tribe.",
            FactType.Will: "A fact of a person's will.",
            FactType.Visit: "A fact of a person's visit to a place.",
            FactType.Yahrzeit: "A fact of a person's yahrzeit.",
            FactType.AdoptiveParent: "A fact about an adoptive relationship.",
            FactType.BiologicalParent: "A fact about the biological relationship.",
            FactType.ChildOrder: "A fact about the child order.",
            FactType.EnteringHeir: "A fact about an entering heir relationship.",
            FactType.ExitingHeir: "A fact about an exiting heir relationship.",
            FactType.FosterParent: "A fact about a foster relationship.",
            FactType.GuardianParent: "A fact about legal guardianship.",
            FactType.StepParent: "A fact about the step relationship.",
            FactType.SociologicalParent: "A fact about a sociological relationship.",
            FactType.SurrogateParent: "A fact about a surrogate relationship.",
            FactType.Annulment: "A fact of an annulment of marriage.",
            FactType.CommonLawMarriage: "A fact of marriage by common law.",
            FactType.CivilUnion: "A fact of a civil union.",
            FactType.DomesticPartnership: "A fact of a domestic partnership.",
            FactType.Engagement: "A fact of an engagement to marry.",
            FactType.MarriageBanns: "A fact of marriage banns.",
            FactType.MarriageContract: "A fact of a marriage contract.",
            FactType.MarriageLicense: "A fact of a marriage license.",
            FactType.MarriageNotice: "A fact of a marriage notice.",
            FactType.Separation: "A fact of a couple's separation."
        }
        return descriptions.get(self, "No description available.")
    
    @staticmethod
    def guess(description):
        keywords_to_fact_type = {
            # Person Fact Types
            "adoption": FactType.Adoption,
            "adult christening": FactType.AdultChristening,
            "amnesty": FactType.Amnesty,
            "ancestral hall": FactType.AncestralHall,
            "ancestral poem": FactType.AncestralPoem,
            "apprenticeship": FactType.Apprenticeship,
            "arrest": FactType.Arrest,
            "award": FactType.Award,
            "baptism": FactType.Baptism,
            "bar mitzvah": FactType.BarMitzvah,
            "bat mitzvah": FactType.BatMitzvah,
            "birth": FactType.Birth,
            "birth notice": FactType.BirthNotice,
            "blessing": FactType.Blessing,
            "branch": FactType.Branch,
            "burial": FactType.Burial,
            "caste": FactType.Caste,
            "census": FactType.Census,
            "christening": FactType.Christening,
            "circumcision": FactType.Circumcision,
            "clan": FactType.Clan,
            "confirmation": FactType.Confirmation,
            "court": FactType.Court,
            "cremation": FactType.Cremation,
            "death": FactType.Death,
            "education": FactType.Education,
            "education enrollment": FactType.EducationEnrollment,
            "emigration": FactType.Emigration,
            "enslavement": FactType.Enslavement,
            "ethnicity": FactType.Ethnicity,
            "excommunication": FactType.Excommunication,
            "first communion": FactType.FirstCommunion,
            "funeral": FactType.Funeral,
            "gender change": FactType.GenderChange,
            "generation number": FactType.GenerationNumber,
            "graduation": FactType.Graduation,
            "heimat": FactType.Heimat,
            "immigration": FactType.Immigration,
            "imprisonment": FactType.Imprisonment,
            "inquest": FactType.Inquest,
            "land transaction": FactType.LandTransaction,
            "language": FactType.Language,
            "living": FactType.Living,
            "marital status": FactType.MaritalStatus,
            "medical": FactType.Medical,
            "military award": FactType.MilitaryAward,
            "military discharge": FactType.MilitaryDischarge,
            "military draft registration": FactType.MilitaryDraftRegistration,
            "military induction": FactType.MilitaryInduction,
            "military service": FactType.MilitaryService,
            "mission": FactType.Mission,
            "move from": FactType.MoveFrom,
            "move to": FactType.MoveTo,
            "multiple birth": FactType.MultipleBirth,
            "national id": FactType.NationalId,
            "nationality": FactType.Nationality,
            "naturalization": FactType.Naturalization,
            "number of children": FactType.NumberOfChildren,
            "number of marriages": FactType.NumberOfMarriages,
            "obituary": FactType.Obituary,
            "official position": FactType.OfficialPosition,
            "occupation": FactType.Occupation,
            "ordination": FactType.Ordination,
            "pardon": FactType.Pardon,
            "physical description": FactType.PhysicalDescription,
            "probate": FactType.Probate,
            "property": FactType.Property,
            "race": FactType.Race,
            "religion": FactType.Religion,
            "residence": FactType.Residence,
            "retirement": FactType.Retirement,
            "stillbirth": FactType.Stillbirth,
            "tax assessment": FactType.TaxAssessment,
            "tribe": FactType.Tribe,
            "will": FactType.Will,
            "visit": FactType.Visit,
            "yahrzeit": FactType.Yahrzeit,

            # Couple Relationship Fact Types
            "annulment": FactType.Annulment,
            "common law marriage": FactType.CommonLawMarriage,
            "civil union": FactType.CivilUnion,
            "divorce": FactType.Divorce,
            "divorce filing": FactType.DivorceFiling,
            "domestic partnership": FactType.DomesticPartnership,
            "engagement": FactType.Engagement,
            "marriage": FactType.Marriage,
            "marriage banns": FactType.MarriageBanns,
            "marriage contract": FactType.MarriageContract,
            "marriage license": FactType.MarriageLicense,
            "marriage notice": FactType.MarriageNotice,
            "couple number of children": FactType.NumberOfChildren,
            "separation": FactType.Separation,

            # Parent-Child Relationship Fact Types
            "adoptive parent": FactType.AdoptiveParent,
            "biological parent": FactType.BiologicalParent,
            "child order": FactType.ChildOrder,
            "entering heir": FactType.EnteringHeir,
            "exiting heir": FactType.ExitingHeir,
            "foster parent": FactType.FosterParent,
            "guardian parent": FactType.GuardianParent,
            "step parent": FactType.StepParent,
            "sociological parent": FactType.SociologicalParent,
            "surrogate parent": FactType.SurrogateParent
        }


        description_lower = description.lower()
    
        # Replace any non-alphanumeric characters with a space
        description_clean = re.sub(r'[^a-z0-9\s]', ' ', description_lower)
        
        # Get a list of words in the cleaned description
        words = description_clean.split()

        # Check for the best matching keyword in the description
        for word in words:
            matches = difflib.get_close_matches(word, keywords_to_fact_type.keys(), n=1, cutoff=0.8)
            if matches:
                return keywords_to_fact_type[matches[0]]
        return None

class FactQualifier(Enum):
    Age = "http://gedcomx.org/Age"
    Cause = "http://gedcomx.org/Cause"
    Religion = "http://gedcomx.org/Religion"
    Transport = "http://gedcomx.org/Transport"
    NonConsensual = "http://gedcomx.org/NonConsensual"
    
    @property
    def description(self):
        descriptions = {
            FactQualifier.Age: "The age of a person at the event described by the fact.",
            FactQualifier.Cause: "The cause of the fact, such as the cause of death.",
            FactQualifier.Religion: "The religion associated with a religious event such as a baptism or excommunication.",
            FactQualifier.Transport: "The name of the transport associated with an event that indicates a move.",
            FactQualifier.NonConsensual: "An indicator that the event occurred non-consensually, e.g., under enslavement."
        }
        return descriptions.get(self, "No description available.")

@extensible()
class Fact(Conclusion):
    identifier = 'http://gedcomx.org/v1/Fact'
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self,
                 id: Optional[str] = None,
                 lang: Optional[str] = None,
                 sources: Optional[List[SourceReference]] = None,
                 analysis: Optional[Union[Resource,Document]] = None,
                 notes: Optional[List[Note]] = None,
                 confidence: Optional[ConfidenceLevel] = None,
                 attribution: Optional[Attribution] = None,
                 type: Optional[FactType] = None,
                 date: Optional[Date] = None,
                 place: Optional[PlaceReference] = None,
                 value: Optional[str] = None,
                 qualifiers: Optional[List[FactQualifier]] = None):
                 #links: Optional[_rsLinks] = None):
        super().__init__(id, lang, sources, analysis, notes, confidence, attribution)
        self.type = type
        self.date = date
        self.place = place
        self.value = value
        self._qualifiers = qualifiers if qualifiers else []
        self.id = id if id else None # No need for id on 'Fact' unless provided
    
    @property
    def qualifiers(self) -> List[FactQualifier]:
        return self._qualifiers # type: ignore

    @qualifiers.setter
    def qualifiers(self, value: List[FactQualifier]):
        if (not isinstance(value, list)) or (not all(isinstance(item, FactQualifier) for item in value)):
            raise ValueError("sources must be a list of GedcomRecord objects.")
        self._qualifiers.extend(value)

    @property
    def to_dict(self):
        '''
        Standard GedcomX Type JSON Serialization
        Returns: dict that contains only field for which the object has data in
        '''
        with hub.use(serial_log):
            type_as_dict = super().to_dict or {}
            if self.type:
                type_as_dict['type'] = getattr(self.type, 'value', self.type)
            if self.date:
                type_as_dict['date'] = self.date.to_dict
            if self.place:
                type_as_dict['place'] = self.place.to_dict
            if self.value:
                type_as_dict['value'] = self.value
            if self.qualifiers and self.qualifiers != []:
                type_as_dict['qualifiers'] = [getattr(q, 'value', q) for q in self.qualifiers]
            if type_as_dict == {}:
                log.warning("Serializing empty Fact (id={})", self.id)
        
        return type_as_dict if type_as_dict != {} else None 
        
    @classmethod
    def from_json(cls, data: Dict[str, Any], context: Any = None) -> "Fact":
        if not isinstance(data, dict):
            raise TypeError(f"{cls.__name__}._from_json_ expected dict, got {type(data)}")
        fact_data = Conclusion.dict_from_json(data,context)
        if (val := data.get("value")) is not None:
            fact_data["value"] = val
        if (date := data.get("date")) is not None:
            fact_data["date"] = Date.from_json(date, context)
        if (place := data.get("place")) is not None:
            fact_data["place"] = PlaceReference.from_json(place, context)
        if (ft := data.get("type")) is not None:
            fact_data["type"] = FactType(ft)
        if (quals := data.get("qualifiers")) is not None:
            fact_data["qualifiers"] = [Qualifier.from_json(q) for q in quals if q is not None] 
            
        return cls(**fact_data) 

    def __str__(self):
        return f"{self.type.value if self.type else ''} {self.value}"        




