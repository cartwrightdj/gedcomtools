# GedcomX PlaceDescription model.
# jurisdiction typed as Union[Resource, PlaceDescription] (self-reference).
# spatialDescription typed as PlaceReference; both resolved via bottom-of-file model_rebuild().

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, List, Optional, Union

if TYPE_CHECKING:
    from .place_reference import PlaceReference

from .date import Date
from .resource import Resource
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
    jurisdiction: Optional[Union[Resource, PlaceDescription]] = None
    latitude: Optional[Union[float, str]] = None
    longitude: Optional[Union[float, str]] = None
    temporalDescription: Optional[Date] = None
    spatialDescription: Optional[PlaceReference] = None

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_instance
        if self.names is None or len(self.names) == 0:
            result.warn("names", "PlaceDescription has no names")
        if self.latitude is not None:
            if isinstance(self.latitude, (int, float)):
                if not -90.0 <= self.latitude <= 90.0:
                    result.error("latitude", f"Latitude {self.latitude} out of range [-90, 90]")
            else:
                result.warn("latitude", f"Expected float, got {type(self.latitude).__name__}: {self.latitude!r}")
        if self.longitude is not None:
            if isinstance(self.longitude, (int, float)):
                if not -180.0 <= self.longitude <= 180.0:
                    result.error("longitude", f"Longitude {self.longitude} out of range [-180, 180]")
            else:
                result.warn("longitude", f"Expected float, got {type(self.longitude).__name__}: {self.longitude!r}")
        if self.jurisdiction is not None:
            check_instance(result, "jurisdiction", self.jurisdiction, Resource, PlaceDescription)
        if self.spatialDescription is not None:
            check_instance(result, "spatialDescription", self.spatialDescription, PlaceReference)
        check_instance(result, "temporalDescription", self.temporalDescription, Date)
        check_instance(result, "place", self.place, URI)


# Resolve forward references (self-reference + PlaceReference).
from .place_reference import PlaceReference  # noqa: E402
PlaceDescription.model_rebuild()
