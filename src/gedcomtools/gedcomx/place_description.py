from __future__ import annotations

from typing import Any, ClassVar, List, Optional, Union

from .date import Date
from .evidence_reference import EvidenceReference
from .identifier import IdentifierList
from .note import Note
from .resource import Resource
from .source_reference import SourceReference
from .subject import Subject
from .textvalue import TextValue
from .uri import URI


class PlaceDescription(Subject):
    """PlaceDescription describes the details of a place in terms of its name
    and possibly its type, time period, and/or a geospatial description.
    """

    identifier: ClassVar[str] = "http://gedcomx.org/v1/PlaceDescription"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    names: Optional[List[TextValue]] = None
    type: Optional[str] = None  # TODO: replace with enumeration
    place: Optional[URI] = None
    jurisdiction: Optional[Any] = None  # Resource | PlaceDescription
    latitude: Optional[Union[float, str]] = None
    longitude: Optional[Union[float, str]] = None
    temporalDescription: Optional[Date] = None
    spatialDescription: Optional[Any] = None  # PlaceReference

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_instance
        if self.names is not None and len(self.names) == 0:
            result.warn("names", "PlaceDescription.names list is empty")
        if self.latitude is not None:
            if isinstance(self.latitude, (int, float)):
                if not (-90.0 <= self.latitude <= 90.0):
                    result.error("latitude", f"Latitude {self.latitude} out of range [-90, 90]")
            else:
                result.warn("latitude", f"Expected float, got {type(self.latitude).__name__}: {self.latitude!r}")
        if self.longitude is not None:
            if isinstance(self.longitude, (int, float)):
                if not (-180.0 <= self.longitude <= 180.0):
                    result.error("longitude", f"Longitude {self.longitude} out of range [-180, 180]")
            else:
                result.warn("longitude", f"Expected float, got {type(self.longitude).__name__}: {self.longitude!r}")
        if self.jurisdiction is not None:
            check_instance(result, "jurisdiction", self.jurisdiction, Resource, PlaceDescription)
        if self.spatialDescription is not None:
            from .place_reference import PlaceReference
            check_instance(result, "spatialDescription", self.spatialDescription, PlaceReference)
        check_instance(result, "temporalDescription", self.temporalDescription, Date)
        check_instance(result, "place", self.place, URI)
