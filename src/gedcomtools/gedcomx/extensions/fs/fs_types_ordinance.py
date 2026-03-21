"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/extensions/fs/fs_types_ordinance.py
 Purpose: FamilySearch GedcomX ordinance extension types.

 Types: OrdinanceType, OrdinanceStatus, OrdinanceStatusReason,
        OrdinanceSexType, OrdinanceRoleType,
        OrdinanceReservationAssigneeType, OrdinanceReservationClaimType,
        OrdinanceRollupStatus,
        OrdinanceActions, OrdinanceParticipant, OrdinanceReservation,
        OrdinanceSummary, OrdinanceRollup, Ordinance

 Specification:
   https://github.com/FamilySearch/gedcomx-fs/blob/master/specifications/
   fs-gedcomx-extension-specification.md

 Created: 2026-03-21
======================================================================
"""
from __future__ import annotations

import enum
from typing import Any, ClassVar, List, Optional

from pydantic import Field

from gedcomtools.gedcomx.conclusion import Conclusion
from gedcomtools.gedcomx.gx_base import GedcomXModel
from gedcomtools.gedcomx.resource import Resource
from gedcomtools.glog import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Enum types
# ---------------------------------------------------------------------------

class OrdinanceType(str, enum.Enum):
    """URI constants for LDS ordinance types."""

    Baptism = "http://churchofjesuschrist.org/Baptism"
    Confirmation = "http://churchofjesuschrist.org/Confirmation"
    Initiatory = "http://churchofjesuschrist.org/Initiatory"
    Endowment = "http://churchofjesuschrist.org/Endowment"
    SealingToSpouse = "http://churchofjesuschrist.org/SealingToSpouse"
    SealingChildToParents = "http://churchofjesuschrist.org/SealingChildToParents"


class OrdinanceStatus(str, enum.Enum):
    """URI constants for the status of an LDS ordinance."""

    BornInCovenant = "http://familysearch.org/v1/BornInCovenant"
    Completed = "http://familysearch.org/v1/Completed"
    NeedMoreInformation = "http://familysearch.org/v1/NeedMoreInformation"
    NeedPermission = "http://familysearch.org/v1/NeedPermission"
    NotAvailable = "http://familysearch.org/v1/NotAvailable"
    NotNeeded = "http://familysearch.org/v1/NotNeeded"
    NotReady = "http://familysearch.org/v1/NotReady"
    Ready = "http://familysearch.org/v1/Ready"
    Reserved = "http://familysearch.org/v1/Reserved"
    ReservedPrinted = "http://familysearch.org/v1/ReservedPrinted"
    ReservedWaiting = "http://familysearch.org/v1/ReservedWaiting"
    ReservedShared = "http://familysearch.org/v1/ReservedShared"
    ReservedSharedReady = "http://familysearch.org/v1/ReservedSharedReady"
    ReservedSharedPrinted = "http://familysearch.org/v1/ReservedSharedPrinted"


class OrdinanceStatusReason(str, enum.Enum):
    """URI constants describing why an ordinance is in a given status.

    The FamilySearch API defines approximately 50 reason codes; the values
    below are the documented ones from the public specification.
    """

    BornInCovenant = "http://familysearch.org/v1/BornInCovenant"
    DiedBeforeAgeEight = "http://familysearch.org/v1/DiedBeforeAgeEight"
    InvalidName = "http://familysearch.org/v1/InvalidName"
    NeedPermission = "http://familysearch.org/v1/NeedPermission"
    NotDeadAtLeastOneYear = "http://familysearch.org/v1/NotDeadAtLeastOneYear"
    Reserved = "http://familysearch.org/v1/Reserved"
    SameSex = "http://familysearch.org/v1/SameSex"
    UnknownGender = "http://familysearch.org/v1/UnknownGender"


class OrdinanceSexType(str, enum.Enum):
    """URI constants for the sex type of an ordinance participant."""

    Male = "http://familysearch.org/v1/Male"
    Female = "http://familysearch.org/v1/Female"
    Unknown = "http://familysearch.org/v1/Unknown"


class OrdinanceRoleType(str, enum.Enum):
    """URI constants for participant role in an ordinance."""

    Parent = "http://familysearch.org/v1/Parent"
    Spouse = "http://familysearch.org/v1/Spouse"


class OrdinanceReservationAssigneeType(str, enum.Enum):
    """URI constants for who is assigned as the ordinance reservation holder."""

    Church = "http://churchofjesuschrist.org/Church"
    Personal = "http://churchofjesuschrist.org/Personal"


class OrdinanceReservationClaimType(str, enum.Enum):
    """URI constants for the claim basis of an ordinance reservation."""

    Default = "http://familysearch.org/v1/Default"
    FamilyGroup = "http://familysearch.org/v1/FamilyGroup"
    InstantName = "http://familysearch.org/v1/InstantName"
    SharedReady = "http://familysearch.org/v1/SharedReady"


class OrdinanceRollupStatus(str, enum.Enum):
    """URI constants for the rollup status of an ordinance."""

    RolledUpCompleted = "http://familysearch.org/v1/RolledUpCompleted"
    RolledUpNeedMoreInformation = "http://familysearch.org/v1/RolledUpNeedMoreInformation"
    RolledUpNotAvailable = "http://familysearch.org/v1/RolledUpNotAvailable"
    RolledUpReady = "http://familysearch.org/v1/RolledUpReady"
    RolledUpReserved = "http://familysearch.org/v1/RolledUpReserved"
    RolledUpReservedSharedReady = "http://familysearch.org/v1/RolledUpReservedSharedReady"


# ---------------------------------------------------------------------------
# Model types
# ---------------------------------------------------------------------------

class OrdinanceActions(GedcomXModel):
    """Available actions for an LDS ordinance.

    Fields:
        reservable:   Whether the ordinance can be reserved.
        unReservable: Whether an existing reservation can be released.
        shareable:    Whether the ordinance can be shared.
        unShareable:  Whether an existing share can be withdrawn.
        printable:    Whether a family ordinance card can be printed.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/OrdinanceActions"

    reservable: Optional[bool] = None
    unReservable: Optional[bool] = None
    shareable: Optional[bool] = None
    unShareable: Optional[bool] = None
    printable: Optional[bool] = None


class OrdinanceParticipant(GedcomXModel):
    """A participant in an LDS ordinance.

    Fields:
        roleType:    The participant's role (see OrdinanceRoleType).
        sexType:     The participant's sex (see OrdinanceSexType).
        participant: Reference to the participant person/resource.
        fullName:    The participant's full name.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/OrdinanceParticipant"

    roleType: Optional[str] = None
    sexType: Optional[str] = None
    participant: Optional[Resource] = None
    fullName: Optional[str] = None


class OrdinanceReservation(GedcomXModel):
    """A reservation entry for an LDS ordinance.

    Fields:
        owner:          The resource that holds the reservation.
        reserveDate:    The date the reservation was made (ms timestamp).
        updateDate:     The date the reservation was last updated (ms).
        expirationDate: The date the reservation expires (ms).
        claimType:      The claim basis (see OrdinanceReservationClaimType).
        assigneeType:   Who holds the reservation (see OrdinanceReservationAssigneeType).
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/OrdinanceReservation"

    owner: Optional[Resource] = None
    reserveDate: Optional[int] = None
    updateDate: Optional[int] = None
    expirationDate: Optional[int] = None
    claimType: Optional[str] = None
    assigneeType: Optional[str] = None


class OrdinanceSummary(GedcomXModel):
    """Summary counts of ordinance reservations.

    Fields:
        notSharedReservationCount: Count of reservations not shared.
        notSharedReservationLimit: Limit on not-shared reservations.
        sharedReservationCount:    Count of shared reservations.
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/OrdinanceSummary"

    notSharedReservationCount: Optional[int] = None
    notSharedReservationLimit: Optional[int] = None
    sharedReservationCount: Optional[int] = None


class OrdinanceRollup(Conclusion):
    """A rollup conclusion for a set of ordinances.

    Extends :class:`~gedcomtools.gedcomx.conclusion.Conclusion` with
    ordinance-specific rollup fields.

    Fields:
        type:         The ordinance type (see OrdinanceType).
        rollupStatus: The rollup status (see OrdinanceRollupStatus).
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/OrdinanceRollup"

    type: Optional[str] = None
    rollupStatus: Optional[str] = None


class Ordinance(Conclusion):
    """An LDS temple ordinance conclusion.

    Extends :class:`~gedcomtools.gedcomx.conclusion.Conclusion` with
    ordinance-specific fields.

    Fields:
        type:                The ordinance type (see OrdinanceType).
        status:              The ordinance status (see OrdinanceStatus).
        statusReasons:       Reasons for the current status.
        actions:             Available actions for this ordinance.
        person:              The person for whom the ordinance is performed.
        sexType:             The sex type for this ordinance.
        participants:        Participants in this ordinance.
        reservation:         The primary ordinance reservation.
        secondaryReservation: A secondary reservation entry.
        callerReservation:   The caller's reservation entry.
        templeCode:          The code for the temple where completed.
        completeDate:        Human-readable completion date.
        fullName:            The full name used in the ordinance.
        completionDate:      Completion timestamp (ms).
    """

    identifier: ClassVar[str] = "http://familysearch.org/v1/Ordinance"

    type: Optional[str] = None
    status: Optional[str] = None
    statusReasons: List[str] = Field(default_factory=list)
    actions: Optional[OrdinanceActions] = None
    person: Optional[Resource] = None
    sexType: Optional[str] = None
    participants: List[OrdinanceParticipant] = Field(default_factory=list)
    reservation: Optional[OrdinanceReservation] = None
    secondaryReservation: Optional[OrdinanceReservation] = None
    callerReservation: Optional[OrdinanceReservation] = None
    templeCode: Optional[str] = None
    completeDate: Optional[str] = None
    fullName: Optional[str] = None
    completionDate: Optional[int] = None


log.debug(
    "fs_types_ordinance extension loaded — "
    "OrdinanceType, OrdinanceStatus, OrdinanceStatusReason, OrdinanceSexType, "
    "OrdinanceRoleType, OrdinanceReservationAssigneeType, OrdinanceReservationClaimType, "
    "OrdinanceRollupStatus, OrdinanceActions, OrdinanceParticipant, OrdinanceReservation, "
    "OrdinanceSummary, OrdinanceRollup, Ordinance defined"
)
