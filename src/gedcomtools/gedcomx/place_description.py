from __future__ import annotations
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
if TYPE_CHECKING:
    from .place_reference import PlaceReference

"""
======================================================================
 Project: Gedcom-X
 File:    place_description.py
 Author:  David J. Cartwright
 Purpose: 

 Created: 2025-08-25
 Updated:
   - 2025-09-01: filename PEP8 standard
   - 2025-09-03: _from_json_ refactored
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

from .identifier import IdentifierList
from .note import Note
from .resource import Resource
from .source_reference import SourceReference
from .schemas import extensible
from .subject import Subject
from .textvalue import TextValue
from .uri import URI
"""
======================================================================
Logging
======================================================================
"""
#=====================================================================

@extensible(toplevel=True)
class PlaceDescription(Subject):
    """PlaceDescription describes the details of a place in terms of 
    its name and possibly its type, time period, and/or a geospatial description
    functioning as a description of a place as a snapshot in time.

    Encapsulates textual names, geospatial coordinates, jurisdictional context,
    temporal coverage, and related resources (media, sources, evidence, etc.).
    

    Attributes:
        names (Optional[List[TextValue]]): Human-readable names or labels for
            the place (e.g., “Boston, Suffolk, Massachusetts, United States”).
        type (Optional[str]): A place type identifier (e.g., a URI). **TODO:**
            replace with an enumeration when finalized.
        place (Optional[URI]): Canonical identifier (URI) for the place.
        jurisdiction (Optional[Resource|PlaceDescription]): The governing or
            containing jurisdiction of this place (e.g., county for a town).
        latitude (Optional[float]): Latitude in decimal degrees (WGS84).
        longitude (Optional[float]): Longitude in decimal degrees (WGS84).
        temporalDescription (Optional[Date]): Temporal coverage/validity window
            for this description (e.g., when a jurisdictional boundary applied).
        spatialDescription (Optional[Resource]): A resource describing spatial
            geometry or a link to an external gazetteer/shape definition.
    """
    identifier = "http://gedcomx.org/v1/PlaceDescription"
    version = 'http://gedcomx.org/conceptual-model/v1'

    def __init__(self, id: Optional[str] =None,
                 lang: Optional[str] = None,
                 sources: Optional[List[SourceReference]] = None,
                 analysis: Optional[Resource] = None,
                 notes: Optional[List[Note]] =None,
                 confidence: Optional[ConfidenceLevel] = None,
                 attribution: Optional[Attribution] = None,
                 extracted: Optional[bool] = None,
                 evidence: Optional[List[EvidenceReference]] = None,
                 media: Optional[List[SourceReference]] = None,
                 identifiers: Optional[IdentifierList] = None,
                 names: Optional[List[TextValue]] = None,
                 type: Optional[str] = None,    #TODO This needs to be an enumerated value, work out details
                 place: Optional[URI] = None,
                 jurisdiction: Optional[Union[Resource,PlaceDescription]] = None, 
                 latitude: Optional[float] = None,
                 longitude: Optional[float] = None,
                 temporalDescription: Optional[Date] = None,

                 spatialDescription: Optional[PlaceReference] = None,
                 ) -> None:
        
        super().__init__(id, lang, sources, analysis, notes, confidence, attribution, extracted, evidence, media, identifiers)
        self.names = names
        self.type = type
        self.place = place
        self.jurisdiction = jurisdiction
        self.latitude = latitude
        self.longitude = longitude
        self.temporalDescription = temporalDescription
        self.spatialDescription = spatialDescription

    @property
    def to_dict(self):
        from .serialization import Serialization
        type_as_dict = super().to_dict or {}
        
        if self.names:
            type_as_dict["names"] = [n.to_dict for n in self.names if n]
        if self.type:
            type_as_dict["type"] = self.type    #TODO
        if self.place:
            type_as_dict["place"] = self.place.to_dict
        if self.jurisdiction:
            type_as_dict["jurisdiction"] = self.jurisdiction.to_dict 
        if self.latitude is not None: # include 0.0; exclude only None
            type_as_dict["latitude"] = float(self.latitude)
        if self.longitude is not None: # include 0.0; exclude only None
            type_as_dict["longitude"] = float(self.longitude)
        if self.temporalDescription:
            type_as_dict["temporalDescription"] = self.temporalDescription.to_dict
        if self.spatialDescription:
            type_as_dict["spatialDescription"] = self.spatialDescription.to_dict

        return type_as_dict if type_as_dict != {} else None
        return Serialization.serialize_dict(type_as_dict) 

'''
    @classmethod
    def from_json(cls, data: Any, context: Any = None) -> "PlaceDescription":
        """
        Create a PlaceDescription instance from a JSON-dict (already parsed).
        """        
        if not isinstance(data, dict):
            raise TypeError(f"{cls.__name__}._from_json_ expected dict or str, got {type(data)}")

        person_data: Dict[str, Any] = Subject.dict_from_json(data,context)

        # names (allow both list and a single 'name' alias)
        if (names := data.get("names")) is not None:
            person_data["names"] = [TextValue.from_json(n, context) for n in names]
        
        # type (string for now; promote to enum later)
        if (typ := data.get("type")) is not None:
            person_data["type"] = typ

        # place: URI (accept string or dict)
        if (pl := data.get("place")) is not None:
            person_data["place"] = URI(pl)

        # jurisdiction: Resource | PlaceDescription
        if (jur := data.get("jurisdiction")) is not None:
            person_data["jurisdiction"] = Resource.from_json(jur, context)
            
        # coordinates
        if (lat := data.get("latitude")) is not None:
            person_data["latitude"] = float(lat)
        if (lon := data.get("longitude")) is not None:
            person_data["longitude"] = float(lon)

        # temporal / spatial descriptions
        if (td := data.get("temporalDescription")) is not None:
            person_data["temporalDescription"] = Date.from_json(td, context)

        if (sd := data.get("spatialDescription")) is not None:
            person_data["spatialDescription"] = Resource.from_json(sd, context)

        return cls(**person_data)   
'''