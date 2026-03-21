from __future__ import annotations

import difflib
import re
from enum import Enum
from typing import Any, ClassVar, List, Optional, Union

from pydantic import Field, PrivateAttr

from .attribution import Attribution
from .conclusion import Conclusion, ConfidenceLevel
from .date import Date
from .document import Document
from .gx_base import GedcomXModel
from .note import Note
from .place_reference import PlaceReference
from .qualifier import Qualifier
from .resource import Resource
from .source_reference import SourceReference


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
    # Couple Relationship
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
    # Parent-Child
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
    Unknown = "null"

    @classmethod
    def from_value(cls, value: str) -> "FactType":
        for member in cls:
            if member.value == value:
                return member
        return cls.Unknown

    @staticmethod
    def guess(description: str) -> Optional["FactType"]:
        keywords: dict = {
            "birth": FactType.Birth, "death": FactType.Death,
            "marriage": FactType.Marriage, "burial": FactType.Burial,
            "baptism": FactType.Baptism, "census": FactType.Census,
            "immigration": FactType.Immigration, "emigration": FactType.Emigration,
            "occupation": FactType.Occupation, "residence": FactType.Residence,
        }
        desc_lower = re.sub(r"[^a-z0-9\s]", " ", description.lower())
        for word in desc_lower.split():
            matches = difflib.get_close_matches(word, keywords.keys(), n=1, cutoff=0.8)
            if matches:
                return keywords[matches[0]]
        return None


class FactQualifier(Enum):
    Age = "http://gedcomx.org/Age"
    Cause = "http://gedcomx.org/Cause"
    Religion = "http://gedcomx.org/Religion"
    Transport = "http://gedcomx.org/Transport"
    NonConsensual = "http://gedcomx.org/NonConsensual"


class Fact(Conclusion):
    identifier: ClassVar[str] = "http://gedcomx.org/v1/Fact"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    type: Optional[FactType] = None
    date: Optional[Date] = None
    place: Optional[PlaceReference] = None
    value: Optional[str] = None
    _qualifiers: List[FactQualifier] = PrivateAttr(default_factory=list)

    def model_post_init(self, __context: object) -> None:
        super().model_post_init(__context)
        # Preserve qualifiers passed at construction
        raw = (self.model_extra or {}).get("qualifiers")
        if raw and isinstance(raw, list):
            self._qualifiers = list(raw)

    @property
    def qualifiers(self) -> List[FactQualifier]:
        return self._qualifiers

    @qualifiers.setter
    def qualifiers(self, value: List[FactQualifier]) -> None:
        if not isinstance(value, list) or not all(isinstance(i, FactQualifier) for i in value):
            raise ValueError("qualifiers must be a list of FactQualifier objects.")
        self._qualifiers = list(value)

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_instance, check_nonempty
        if self.type is not None and not isinstance(self.type, FactType):
            result.error("type", f"Expected FactType, got {type(self.type).__name__}: {self.type!r}")
        check_instance(result, "date", self.date, Date)
        check_instance(result, "place", self.place, PlaceReference)
        if self.value is not None:
            check_nonempty(result, "value", self.value)

    def __str__(self) -> str:
        return f"{self.type.value if self.type else ''} {self.value or ''}"
