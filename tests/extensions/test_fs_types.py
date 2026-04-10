"""
Tests for all FamilySearch GedcomX extension data types.

Updated: 2026-04-08 — verify `ChildAndParentsRelationship` deserializes
typed parent/child/fact fields and accepts inherited RS10-style `links`
maps from FamilySearch JSON payloads
Updated: 2026-04-08 — cover FamilySearch docs names `FieldInfo` and
`RelationshipType`, while preserving older compatibility aliases

Covers all 65 types listed in the FS JSON specification:
  https://www.familysearch.org/en/developers/docs/api/fs_json

One class per module/domain group.
"""
from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Alternate types  (fs_types_alternate)
# ---------------------------------------------------------------------------

class TestAlternateTypes:
    def test_alternate_date_is_date_subclass(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_alternate import AlternateDate
        from gedcomtools.gedcomx.date import Date
        assert issubclass(AlternateDate, Date)

    def test_alternate_date_identifier(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_alternate import AlternateDate
        assert AlternateDate.identifier == "http://familysearch.org/v1/AlternateDate"

    def test_alternate_date_construction(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_alternate import AlternateDate
        d = AlternateDate(original="abt 1850")
        assert d.original == "abt 1850"

    def test_alternate_place_reference_is_subclass(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_alternate import AlternatePlaceReference
        from gedcomtools.gedcomx.place_reference import PlaceReference
        assert issubclass(AlternatePlaceReference, PlaceReference)

    def test_alternate_place_reference_construction(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_alternate import AlternatePlaceReference
        p = AlternatePlaceReference(original="Salt Lake City, Utah")
        assert p.original == "Salt Lake City, Utah"


# ---------------------------------------------------------------------------
# Artifact types  (fs_types_artifact)
# ---------------------------------------------------------------------------

class TestArtifactTypes:
    def test_display_state_enum_values(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_artifact import ArtifactDisplayState
        assert ArtifactDisplayState.Approved.value == "http://familysearch.org/v1/Approved"
        assert ArtifactDisplayState.Restricted.value == "http://familysearch.org/v1/Restricted"

    def test_screening_state_enum_values(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_artifact import ArtifactScreeningState
        assert ArtifactScreeningState.Pending.value == "http://familysearch.org/v1/Pending"

    def test_artifact_metadata_empty(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_artifact import ArtifactMetadata
        m = ArtifactMetadata()
        assert m.filename is None
        assert m.editable is None

    def test_artifact_metadata_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_artifact import ArtifactMetadata
        m = ArtifactMetadata(filename="photo.jpg", width=1920, height=1080, size=204800, editable=True)
        assert m.filename == "photo.jpg"
        assert m.width == 1920
        assert m.size == 204800


# ---------------------------------------------------------------------------
# Change types  (fs_types_change)
# ---------------------------------------------------------------------------

class TestChangeTypes:
    def test_change_operation_values(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_change import ChangeOperation
        assert ChangeOperation.Create.value == "http://familysearch.org/v1/Create"
        assert ChangeOperation.Delete.value == "http://familysearch.org/v1/Delete"

    def test_change_object_type_values(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_change import ChangeObjectType
        assert ChangeObjectType.Person.value == "http://gedcomx.org/Person"

    def test_change_object_modifier_values(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_change import ChangeObjectModifier
        assert ChangeObjectModifier.Couple.value == "http://gedcomx.org/Couple"

    def test_change_info_empty(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_change import ChangeInfo
        c = ChangeInfo()
        assert c.operation is None

    def test_change_info_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_change import ChangeInfo, ChangeOperation
        from gedcomtools.gedcomx.resource import Resource
        c = ChangeInfo(
            operation=ChangeOperation.Update,
            objectType="http://gedcomx.org/Person",
            reason="Corrected birth year",
            resulting=Resource(resourceId="P1"),
        )
        assert c.operation == ChangeOperation.Update
        assert c.reason == "Corrected birth year"


# ---------------------------------------------------------------------------
# Core types  (fs_types_core)
# ---------------------------------------------------------------------------

class TestCoreTypes:
    def test_error_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_core import Error
        e = Error(code=404, label="Not Found", message="Resource not found")
        assert e.code == 404
        assert e.label == "Not Found"

    def test_feature_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_core import Feature
        f = Feature(name="beta-search", enabled=True, activationDate=1700000000000)
        assert f.name == "beta-search"
        assert f.enabled is True

    def test_tag_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_core import Tag
        t = Tag(resource="http://gedcomx.org/Birth", conclusionId="F1-C1")
        assert t.resource == "http://gedcomx.org/Birth"

    def test_agent_name_extends_text_value(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_core import AgentName
        from gedcomtools.gedcomx.textvalue import TextValue
        assert issubclass(AgentName, TextValue)

    def test_agent_name_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_core import AgentName
        a = AgentName(value="FamilySearch", lang="en", type="http://familysearch.org/v1/OfficialName")
        assert a.value == "FamilySearch"
        assert a.type == "http://familysearch.org/v1/OfficialName"

    def test_person_info_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_core import PersonInfo
        p = PersonInfo(canUserEdit=True, visibleToAll=False, treeId="TREE-1")
        assert p.canUserEdit is True
        assert p.treeId == "TREE-1"

    def test_feedback_info_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_core import FeedbackInfo
        f = FeedbackInfo(resolution="resolved", status="closed", details="Duplicate record merged")
        assert f.resolution == "resolved"

    def test_field_info_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_core import FieldInfo
        fi = FieldInfo(fieldType="http://familysearch.org/v1/BirthDate", displayLabel="Birth Date",
                       editable=True, displayable=True, elementTypes=["date"])
        assert fi.fieldType == "http://familysearch.org/v1/BirthDate"
        assert fi.elementTypes == ["date"]

    def test_field_info_identifier(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_core import FieldInfo
        assert FieldInfo.identifier == "http://familysearch.org/v1/FieldInfo"

    def test_fs_field_info_alias_preserved(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_core import FieldInfo, FsFieldInfo
        assert FsFieldInfo is FieldInfo

    def test_plt_api_read_message_empty(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_core import PltApiReadMessage
        m = PltApiReadMessage()
        assert m is not None

    def test_tags_registered_on_conclusion(self):
        from gedcomtools.gedcomx.conclusion import Conclusion
        assert "tags" in Conclusion.model_fields

    def test_person_info_registered_on_person(self):
        from gedcomtools.gedcomx.person import Person
        assert "personInfo" in Person.model_fields


# ---------------------------------------------------------------------------
# Discussion types  (fs_types_discussion)
# ---------------------------------------------------------------------------

class TestDiscussionTypes:
    def test_comment_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_discussion import Comment
        from gedcomtools.gedcomx.resource import Resource
        c = Comment(id="C1", text="Great find!", created=1700000000000,
                    contributor=Resource(resourceId="U1"))
        assert c.text == "Great find!"
        assert c.contributor is not None
        assert c.contributor.resourceId == "U1"

    def test_discussion_with_comments(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_discussion import Discussion, Comment
        d = Discussion(
            id="D1",
            title="Birth year question",
            details="Is 1852 correct?",
            comments=[Comment(text="Looks right to me")],
        )
        assert d.title == "Birth year question"
        assert len(d.comments) == 1

    def test_discussion_reference_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_discussion import DiscussionReference
        dr = DiscussionReference(id="DR1", resourceId="D1",
                                 resource="http://example.com/discussions/D1")
        assert dr.resourceId == "D1"

    def test_discussion_references_on_conclusion(self):
        from gedcomtools.gedcomx.conclusion import Conclusion
        assert "discussionReferences" in Conclusion.model_fields


# ---------------------------------------------------------------------------
# Group types  (fs_types_group)
# ---------------------------------------------------------------------------

class TestGroupTypes:
    def test_group_member_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_group import GroupMember
        m = GroupMember(groupId="G1", cisId="CIS-123", contactName="Alice", status="active")
        assert m.contactName == "Alice"

    def test_group_with_members(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_group import Group, GroupMember
        g = Group(
            id="G1",
            name="Smith Family",
            treeIds=["T1", "T2"],
            members=[GroupMember(contactName="Alice"), GroupMember(contactName="Bob")],
        )
        assert g.name == "Smith Family"
        assert len(g.members) == 2
        assert g.treeIds == ["T1", "T2"]

    def test_group_empty_lists_default(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_group import Group
        g = Group()
        assert g.members == []
        assert g.treeIds == []


# ---------------------------------------------------------------------------
# Link type  (fs_types_link)
# ---------------------------------------------------------------------------

class TestLinkType:
    def test_link_all_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_link import Link
        lnk = Link(
            href="http://api.familysearch.org/platform/tree/persons/P1",
            title="Person P1",
            type="application/x-gedcomx-v1+json",
            allow="GET,POST",
            count=10,
            offset=0,
            results=42,
        )
        assert lnk.href == "http://api.familysearch.org/platform/tree/persons/P1"
        assert lnk.results == 42

    def test_link_empty(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_link import Link
        lnk = Link()
        assert lnk.href is None
        assert lnk.count is None


# ---------------------------------------------------------------------------
# Merge types  (fs_types_merge)
# ---------------------------------------------------------------------------

class TestMergeTypes:
    def test_merge_conflict_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_merge import MergeConflict
        from gedcomtools.gedcomx.resource import Resource
        mc = MergeConflict(survivorResource=Resource(resourceId="P1"),
                           duplicateResource=Resource(resourceId="P2"))
        assert mc.survivorResource is not None
        assert mc.survivorResource.resourceId == "P1"

    def test_merge_analysis_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_merge import MergeAnalysis, MergeConflict
        from gedcomtools.gedcomx.resource import Resource
        ma = MergeAnalysis(
            survivor=Resource(resourceId="P1"),
            duplicate=Resource(resourceId="P2"),
            conflictingResources=[MergeConflict(survivorResource=Resource(resourceId="P1"))],
        )
        assert ma.survivor is not None
        assert ma.survivor.resourceId == "P1"
        assert len(ma.conflictingResources) == 1

    def test_merge_resources(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_merge import Merge
        from gedcomtools.gedcomx.resource import Resource
        m = Merge(
            resourcesToDelete=[Resource(resourceId="OLD-1")],
            resourcesToCopy=[Resource(resourceId="KEEP-1")],
        )
        assert len(m.resourcesToDelete) == 1
        assert len(m.resourcesToCopy) == 1


# ---------------------------------------------------------------------------
# Node / navigation types  (fs_types_node)
# ---------------------------------------------------------------------------

class TestNodeTypes:
    def test_template_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_node import Template
        t = Template(name="self", template="http://api.fs.org/persons/{pid}")
        assert t.name == "self"

    def test_templates_list(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_node import Templates, Template
        ts = Templates(templates=[Template(name="person", template="/persons/{pid}")])
        assert len(ts.templates) == 1

    def test_name_form_info(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_node import NameFormInfo, NameFormOrder
        nfi = NameFormInfo(order=NameFormOrder.Eurotypic)
        assert nfi.order == NameFormOrder.Eurotypic

    def test_name_form_info_registered_on_name_form(self):
        from gedcomtools.gedcomx.name import NameForm
        assert "nameFormInfo" in NameForm.model_fields

    def test_name_form_order_enum(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_node import NameFormOrder
        assert NameFormOrder.Eurotypic.value == "http://familysearch.org/v1/Eurotypic"
        assert NameFormOrder.Sinotypic.value == "http://familysearch.org/v1/Sinotypic"

    def test_name_search_info(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_node import NameSearchInfo
        n = NameSearchInfo(text="Smith", nameId="N1", weight=0.92)
        assert n.text == "Smith"
        assert n.weight == pytest.approx(0.92)

    def test_child_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_node import Child
        c = Child(name="Jane Smith", apid="LT7S-TST", order=2)
        assert c.name == "Jane Smith"
        assert c.order == 2

    def test_children_data(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_node import ChildrenData, Child
        cd = ChildrenData(
            position=0,
            children=[Child(name="Alice"), Child(name="Bob")],
            baseUrl="http://api.fs.org",
        )
        assert len(cd.children) == 2
        assert cd.children[0].name == "Alice"

    def test_node_data(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_node import NodeData, Template
        nd = NodeData(name="John Smith", apid="LT7S-TST",
                      childCount=3, streamCount=1, lastMod=1700000000000,
                      templates=[Template(name="self", template="/tree/{apid}")])
        assert nd.name == "John Smith"
        assert nd.childCount == 3

    def test_facet_nested(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_node import Facet
        f = Facet(
            displayName="Birth Year",
            count=150,
            facets=[Facet(displayName="1850-1860", count=42)],
        )
        assert f.displayName == "Birth Year"
        assert len(f.facets) == 1

    def test_search_info(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_node import SearchInfo
        s = SearchInfo(totalHits=500, closeHits=12)
        assert s.totalHits == 500

    def test_person_deserializes_person_info_and_name_form_info(self):
        from gedcomtools.gedcomx.person import Person

        person = Person.model_validate(
            {
                "id": "P-1",
                "living": False,
                "personInfo": [
                    {
                        "canUserEdit": True,
                        "visibleToAll": True,
                        "visibleToAllWhenUsingFamilySearchApps": True,
                    }
                ],
                "names": [
                    {
                        "type": "http://gedcomx.org/BirthName",
                        "nameForms": [
                            {
                                "fullText": "Gerald F. Cartwright",
                                "nameFormInfo": [
                                    {"order": "http://familysearch.org/v1/Eurotypic"}
                                ],
                                "parts": [
                                    {
                                        "type": "http://gedcomx.org/Given",
                                        "value": "Gerald F.",
                                    },
                                    {
                                        "type": "http://gedcomx.org/Surname",
                                        "value": "Cartwright",
                                    },
                                ],
                            }
                        ],
                    }
                ],
            }
        )

        assert len(person.personInfo) == 1
        assert person.personInfo[0].canUserEdit is True
        assert len(person.names[0].nameForms[0].nameFormInfo) == 1
        assert (
            person.names[0].nameForms[0].nameFormInfo[0].order
            == "http://familysearch.org/v1/Eurotypic"
        )

    def test_person_deserializes_display_to_typed_display_properties(self):
        from gedcomtools.gedcomx.person import Person
        from gedcomtools.gedcomx.extensions.fs.fs_types_rs import DisplayProperties

        person = Person.model_validate(
            {
                "id": "P-1",
                "display": {
                    "name": "Gerald F. Cartwright",
                    "gender": "Male",
                    "birthDate": "12 August 1917",
                    "deathDate": "19 July 1996",
                    "lifespan": "1917-1996",
                },
            }
        )

        assert isinstance(person.displayProperties, DisplayProperties)
        assert person.displayProperties.birthDate == "12 August 1917"
        assert person.display()["deathDate"] == "19 July 1996"

    def test_person_display_falls_back_to_computed_values(self):
        from gedcomtools.gedcomx.person import Person

        person = Person.model_validate(
            {
                "id": "P-1",
                "names": [
                    {
                        "type": "http://gedcomx.org/BirthName",
                        "nameForms": [{"fullText": "Gerald F. Cartwright"}],
                    }
                ],
                "gender": {"type": "http://gedcomx.org/Male"},
                "facts": [
                    {
                        "type": "http://gedcomx.org/Birth",
                        "date": {"original": "12 August 1917"},
                        "place": {"original": "New York, United States"},
                    },
                    {
                        "type": "http://gedcomx.org/Death",
                        "date": {"original": "19 July 1996"},
                        "place": {"original": "Hunt, Livingston, New York, United States"},
                    },
                ],
            }
        )

        display = person.display()
        assert display["name"] == "Gerald F. Cartwright"
        assert display["gender"] == "Male"
        assert display["birthDate"] == "12 August 1917"
        assert display["deathDate"] == "19 July 1996"
        assert display["birthPlace"] == "New York, United States"
        assert display["deathPlace"] == "Hunt, Livingston, New York, United States"

    def test_person_display_prefers_deserialized_values_and_fills_missing_fields(self):
        from gedcomtools.gedcomx.person import Person

        person = Person.model_validate(
            {
                "id": "P-1",
                "display": {
                    "name": "Gerald F. Cartwright",
                    "lifespan": "1917-1996",
                },
                "gender": {"type": "http://gedcomx.org/Male"},
                "facts": [
                    {
                        "type": "http://gedcomx.org/Birth",
                        "date": {"original": "12 August 1917"},
                    }
                ],
            }
        )

        display = person.display()
        assert display["name"] == "Gerald F. Cartwright"
        assert display["lifespan"] == "1917-1996"
        assert display["gender"] == "Male"
        assert display["birthDate"] == "12 August 1917"


# ---------------------------------------------------------------------------
# Ordinance types  (fs_types_ordinance)
# ---------------------------------------------------------------------------

class TestOrdinanceEnums:
    def test_ordinance_type_uris(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_ordinance import OrdinanceType
        assert OrdinanceType.Baptism.value == "http://churchofjesuschrist.org/Baptism"
        assert OrdinanceType.SealingChildToParents.value == "http://churchofjesuschrist.org/SealingChildToParents"

    def test_ordinance_status_values(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_ordinance import OrdinanceStatus
        assert OrdinanceStatus.Ready.value == "http://familysearch.org/v1/Ready"
        assert OrdinanceStatus.ReservedSharedReady.value == "http://familysearch.org/v1/ReservedSharedReady"
        assert OrdinanceStatus.BornInCovenant.value == "http://familysearch.org/v1/BornInCovenant"

    def test_ordinance_status_reason_values(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_ordinance import OrdinanceStatusReason
        assert OrdinanceStatusReason.UnknownGender.value == "http://familysearch.org/v1/UnknownGender"
        assert OrdinanceStatusReason.SameSex.value == "http://familysearch.org/v1/SameSex"

    def test_ordinance_sex_type(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_ordinance import OrdinanceSexType
        assert OrdinanceSexType.Male.value == "http://familysearch.org/v1/Male"
        assert OrdinanceSexType.Female.value == "http://familysearch.org/v1/Female"

    def test_ordinance_role_type(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_ordinance import OrdinanceRoleType
        assert OrdinanceRoleType.Parent.value == "http://familysearch.org/v1/Parent"
        assert OrdinanceRoleType.Spouse.value == "http://familysearch.org/v1/Spouse"

    def test_ordinance_reservation_assignee_type(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_ordinance import OrdinanceReservationAssigneeType
        assert OrdinanceReservationAssigneeType.Church.value == "http://churchofjesuschrist.org/Church"
        assert OrdinanceReservationAssigneeType.Personal.value == "http://churchofjesuschrist.org/Personal"

    def test_ordinance_reservation_claim_type(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_ordinance import OrdinanceReservationClaimType
        assert OrdinanceReservationClaimType.Default.value == "http://familysearch.org/v1/Default"
        assert OrdinanceReservationClaimType.SharedReady.value == "http://familysearch.org/v1/SharedReady"

    def test_ordinance_rollup_status(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_ordinance import OrdinanceRollupStatus
        assert OrdinanceRollupStatus.RolledUpReady.value == "http://familysearch.org/v1/RolledUpReady"
        assert OrdinanceRollupStatus.RolledUpCompleted.value == "http://familysearch.org/v1/RolledUpCompleted"


class TestOrdinanceModels:
    def test_ordinance_actions_all_bools(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_ordinance import OrdinanceActions
        oa = OrdinanceActions(reservable=True, unReservable=False, shareable=True,
                              unShareable=False, printable=True)
        assert oa.reservable is True
        assert oa.printable is True

    def test_ordinance_participant_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_ordinance import (
            OrdinanceParticipant, OrdinanceRoleType, OrdinanceSexType
        )
        from gedcomtools.gedcomx.resource import Resource
        p = OrdinanceParticipant(
            roleType=OrdinanceRoleType.Parent,
            sexType=OrdinanceSexType.Male,
            participant=Resource(resourceId="P1"),
            fullName="John Smith",
        )
        assert p.fullName == "John Smith"
        assert p.roleType == OrdinanceRoleType.Parent

    def test_ordinance_reservation_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_ordinance import (
            OrdinanceReservation, OrdinanceReservationAssigneeType
        )
        from gedcomtools.gedcomx.resource import Resource
        r = OrdinanceReservation(
            owner=Resource(resourceId="U1"),
            reserveDate=1700000000000,
            assigneeType=OrdinanceReservationAssigneeType.Personal,
        )
        assert r.owner is not None
        assert r.owner.resourceId == "U1"

    def test_ordinance_summary_counts(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_ordinance import OrdinanceSummary
        s = OrdinanceSummary(notSharedReservationCount=3, notSharedReservationLimit=10,
                             sharedReservationCount=1)
        assert s.notSharedReservationCount == 3

    def test_ordinance_rollup_extends_conclusion(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_ordinance import OrdinanceRollup
        from gedcomtools.gedcomx.conclusion import Conclusion
        assert issubclass(OrdinanceRollup, Conclusion)

    def test_ordinance_rollup_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_ordinance import (
            OrdinanceRollup, OrdinanceType, OrdinanceRollupStatus
        )
        r = OrdinanceRollup(type=OrdinanceType.Baptism, rollupStatus=OrdinanceRollupStatus.RolledUpReady)
        assert r.type == OrdinanceType.Baptism

    def test_ordinance_extends_conclusion(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_ordinance import Ordinance
        from gedcomtools.gedcomx.conclusion import Conclusion
        assert issubclass(Ordinance, Conclusion)

    def test_ordinance_full_construction(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_ordinance import (
            Ordinance, OrdinanceType, OrdinanceStatus, OrdinanceActions,
            OrdinanceParticipant, OrdinanceRoleType
        )
        from gedcomtools.gedcomx.resource import Resource
        o = Ordinance(
            type=OrdinanceType.Endowment,
            status=OrdinanceStatus.Ready,
            actions=OrdinanceActions(reservable=True),
            person=Resource(resourceId="P1"),
            participants=[OrdinanceParticipant(roleType=OrdinanceRoleType.Spouse)],
            fullName="Jane Smith",
            templeCode="SLAKE",
        )
        assert o.type == OrdinanceType.Endowment
        assert o.status == OrdinanceStatus.Ready
        assert len(o.participants) == 1
        assert o.templeCode == "SLAKE"

    def test_ordinance_inherits_conclusion_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_ordinance import Ordinance
        assert "attribution" in Ordinance.model_fields
        assert "notes" in Ordinance.model_fields
        assert "sources" in Ordinance.model_fields


# ---------------------------------------------------------------------------
# Place extension types  (fs_types_place_ext)
# ---------------------------------------------------------------------------

class TestPlaceExtTypes:
    def test_place_attribute_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_place_ext import PlaceAttribute
        pa = PlaceAttribute(attributeId="A1", typeName="County", value="Salt Lake",
                            year=1880, locale="en")
        assert pa.typeName == "County"
        assert pa.year == 1880

    def test_place_description_info_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_place_ext import PlaceDescriptionInfo
        pdi = PlaceDescriptionInfo(zoomLevel=8, relatedType="county", relatedSubType="civil")
        assert pdi.zoomLevel == 8
        assert pdi.relatedType == "county"


# ---------------------------------------------------------------------------
# Platform types  (fs_types_platform)
# ---------------------------------------------------------------------------

class TestPlatformTypes:
    def test_third_party_access_enum(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_platform import ThirdPartyAccess
        assert ThirdPartyAccess.AnyApps.value == "http://familysearch.org/v1/AnyApps"
        assert ThirdPartyAccess.CompanyApps.value == "http://familysearch.org/v1/CompanyApps"

    def test_match_status_enum(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_platform import MatchStatus
        assert MatchStatus.Pending.value == "http://familysearch.org/v1/Pending"
        assert MatchStatus.Accepted.value == "http://familysearch.org/v1/Accepted"

    def test_match_info_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_platform import MatchInfo, MatchStatus
        mi = MatchInfo(collection="pedigree", status=MatchStatus.Pending,
                       addsBirth=True, addsDeath=False)
        assert mi.collection == "pedigree"
        assert mi.addsBirth is True

    def test_tree_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_platform import Tree
        t = Tree(id="T1", name="Smith Family Tree", private=False,
                 groupIds=["G1"], startingPersonId="P1")
        assert t.name == "Smith Family Tree"
        assert t.groupIds == ["G1"]

    def test_tree_person_reference_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_platform import TreePersonReference
        from gedcomtools.gedcomx.resource import Resource
        tpr = TreePersonReference(id="TPR1", treePerson=Resource(resourceId="P1"),
                                   tree=Resource(resourceId="T1"))
        assert tpr.id == "TPR1"

    def test_user_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_platform import User
        u = User(id="U1", contactName="jsmith", fullName="John Smith",
                 email="jsmith@example.com", preferredLanguage="en")
        assert u.fullName == "John Smith"
        assert u.preferredLanguage == "en"

    def test_family_search_platform_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_platform import FamilySearchPlatform, Tree, User
        fsp = FamilySearchPlatform(
            trees=[Tree(id="T1", name="Tree 1")],
            users=[User(id="U1", fullName="Alice")],
        )
        assert len(fsp.trees) == 1
        assert fsp.trees[0].name == "Tree 1"

    def test_family_search_platform_deserializes_persons_places_relationships_and_sources(self):
        from gedcomtools.gedcomx.date import DateNormalization
        from gedcomtools.gedcomx.extensions.fs.fs_types_platform import FamilySearchPlatform

        platform = FamilySearchPlatform.model_validate(
            {
                "links": ["person", "collection", "portrait"],
                "childAndParentsRelationships": [
                    {
                        "id": "CAPR-1",
                        "child": {"resource": "#CHILD", "resourceId": "CHILD"},
                        "parent1": {"resource": "#P1", "resourceId": "P1"},
                        "parent2": {"resource": "#P2", "resourceId": "P2"},
                    }
                ],
                "persons": [
                    {
                        "id": "P1",
                        "living": False,
                        "personInfo": [{"canUserEdit": True}],
                        "names": [
                            {
                                "type": "http://gedcomx.org/BirthName",
                                "nameForms": [
                                    {
                                        "fullText": "Gerald F. Cartwright",
                                        "nameFormInfo": [
                                            {
                                                "order": "http://familysearch.org/v1/Eurotypic"
                                            }
                                        ],
                                    }
                                ],
                            }
                        ],
                        "facts": [
                            {
                                "type": "http://gedcomx.org/Birth",
                                "date": {
                                    "formal": "+1917-08-12",
                                    "normalized": [
                                        {
                                            "lang": "en-US",
                                            "value": "12 August 1917",
                                        }
                                    ],
                                },
                            }
                        ],
                    }
                ],
                "places": [
                    {
                        "id": "339",
                        "names": [{"lang": "en-US", "value": "New York, United States"}],
                    }
                ],
                "relationships": [
                    {
                        "id": "R-1",
                        "type": "http://gedcomx.org/Couple",
                        "person1": {"resource": "#P1", "resourceId": "P1"},
                        "person2": {"resource": "#P2", "resourceId": "P2"},
                    }
                ],
                "sourceDescriptions": [
                    {
                        "id": "SD-1",
                        "resourceType": "http://familysearch.org/FamilyTree",
                    }
                ],
            }
        )

        assert platform.links == ["person", "collection", "portrait"]
        assert len(platform.childAndParentsRelationships) == 1
        assert len(platform.persons) == 1
        assert platform.persons[0].facts[0].date is not None
        assert isinstance(platform.persons[0].facts[0].date.normalized[0], DateNormalization)
        assert len(platform.places) == 1
        assert len(platform.relationships) == 1
        assert platform.sourceDescriptions[0].resourceType is not None
        assert platform.sourceDescriptions[0].resourceType.value == "http://familysearch.org/FamilyTree"

    def test_family_search_person_envelope_deserializes_observed_wrapper(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_platform import (
            FamilySearchPersonEnvelope,
            FamilySearchPlatform,
        )

        envelope = FamilySearchPersonEnvelope.model_validate(
            {
                "data": {
                    "persons": [
                        {
                            "id": "LRX2-TYY",
                            "display": {
                                "name": "Gerald F. Cartwright",
                                "lifespan": "1917-1996",
                            },
                        }
                    ]
                },
                "display": "Gerald F. Cartwright",
                "id": "LRX2-TYY",
                "lifespan": "1917-1996",
                "person": {
                    "id": "LRX2-TYY",
                    "display": {
                        "name": "Gerald F. Cartwright",
                        "lifespan": "1917-1996",
                    },
                },
                "personId": "LRX2-TYY",
                "summary": "Male · 1917-1996",
                "title": "Gerald F. Cartwright",
            }
        )

        assert isinstance(envelope.data, FamilySearchPlatform)
        assert envelope.data.persons[0].displayProperties is not None
        assert envelope.data.persons[0].displayProperties.name == "Gerald F. Cartwright"
        assert envelope.person is not None
        assert envelope.person.displayProperties is not None
        assert envelope.person.displayProperties.lifespan == "1917-1996"
        assert envelope.personId == "LRX2-TYY"

    def test_fs_package_reexports_envelope_and_display_types(self):
        from gedcomtools.gedcomx.extensions.fs import (
            DisplayProperties,
            FamilySearchPersonEnvelope,
            FamilySearchPlatform,
        )

        assert FamilySearchPersonEnvelope is not None
        assert FamilySearchPlatform is not None
        assert DisplayProperties is not None


# ---------------------------------------------------------------------------
# Relationship types  (fs_types_relationship)
# ---------------------------------------------------------------------------

class TestRelationshipTypes:
    def test_relationship_type_enum(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_relationship import RelationshipType
        assert RelationshipType.Couple.value == "http://gedcomx.org/Couple"
        assert RelationshipType.AncestorDescendant.value == "http://gedcomx.org/AncestorDescendant"
        assert RelationshipType.EnslavedBy.value == "http://gedcomx.org/EnslavedBy"

    def test_fs_relationship_type_alias_preserved(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_relationship import RelationshipType, FsRelationshipType
        assert FsRelationshipType is RelationshipType

    def test_child_and_parents_extends_subject(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_relationship import ChildAndParentsRelationship
        from gedcomtools.gedcomx.subject import Subject
        assert issubclass(ChildAndParentsRelationship, Subject)

    def test_child_and_parents_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_relationship import ChildAndParentsRelationship
        from gedcomtools.gedcomx.resource import Resource
        r = ChildAndParentsRelationship(
            parent1=Resource(resourceId="P1"),
            parent2=Resource(resourceId="P2"),
            child=Resource(resourceId="P3"),
        )
        assert r.parent1 is not None
        assert r.child is not None
        assert r.parent1.resourceId == "P1"
        assert r.child.resourceId == "P3"

    def test_child_and_parents_with_facts(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_relationship import ChildAndParentsRelationship
        from gedcomtools.gedcomx.fact import Fact, FactType
        from gedcomtools.gedcomx.resource import Resource
        r = ChildAndParentsRelationship(
            parent1=Resource(resourceId="P1"),
            child=Resource(resourceId="P3"),
            parent1Facts=[Fact(type=FactType.Birth)],
        )
        assert len(r.parent1Facts) == 1
        assert r.parent1Facts[0].type == FactType.Birth

    def test_child_and_parents_identifier(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_relationship import ChildAndParentsRelationship
        assert ChildAndParentsRelationship.identifier == "http://familysearch.org/v1/ChildAndParentsRelationship"

    def test_child_and_parents_fact_lists_default_empty(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_relationship import ChildAndParentsRelationship
        r = ChildAndParentsRelationship()
        assert r.parent1Facts == []
        assert r.parent2Facts == []

    def test_child_and_parents_deserializes_with_links_map(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_relationship import ChildAndParentsRelationship
        payload = {
            "id": "9T52-9XM",
            "child": {"resource": "https://beta.familysearch.org/platform/tree/persons/GKTD-24B", "resourceId": "GKTD-24B"},
            "parent1": {"resource": "#9NBF-M6D", "resourceId": "9NBF-M6D"},
            "parent2": {"resource": "https://beta.familysearch.org/platform/tree/persons/GKT6-MPZ", "resourceId": "GKT6-MPZ"},
            "links": {
                "child": {"href": "https://beta.familysearch.org/platform/tree/persons/GKTD-24B?flag=fsh"},
                "relationship": {"href": "https://beta.familysearch.org/platform/tree/child-and-parents-relationships/9T52-9XM?flag=fsh"},
            },
        }
        r = ChildAndParentsRelationship.model_validate(payload)
        assert r.child is not None
        assert r.child.resourceId == "GKTD-24B"
        links = getattr(r, "links", None)
        assert links is not None
        assert links.get("child") is not None


# ---------------------------------------------------------------------------
# Vocabulary types  (fs_types_vocab)
# ---------------------------------------------------------------------------

class TestVocabTypes:
    def test_vocab_concept_attribute_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_vocab import VocabConceptAttribute
        a = VocabConceptAttribute(id="A1", name="category", value="event")
        assert a.name == "category"
        assert a.value == "event"

    def test_vocab_translation_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_vocab import VocabTranslation
        t = VocabTranslation(id="T1", lang="en", text="Birth")
        assert t.lang == "en"
        assert t.text == "Birth"

    def test_vocab_term_with_values(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_vocab import VocabTerm
        from gedcomtools.gedcomx.textvalue import TextValue
        vt = VocabTerm(
            id="VT1",
            typeUri="http://familysearch.org/v1/VocabTerm",
            sublistPosition=1,
            values=[TextValue(value="Birth", lang="en")],
        )
        assert vt.sublistPosition == 1
        assert len(vt.values) == 1

    def test_vocab_concept_fields(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_vocab import VocabConcept, VocabTerm, VocabConceptAttribute
        from gedcomtools.gedcomx.textvalue import TextValue
        vc = VocabConcept(
            id="VC1",
            description="Birth event type",
            gedcomxUri="http://gedcomx.org/Birth",
            vocabTerms=[VocabTerm(id="VT1")],
            attributes=[VocabConceptAttribute(name="category", value="vital")],
            definitions=[TextValue(value="The birth of a person", lang="en")],
        )
        assert vc.gedcomxUri == "http://gedcomx.org/Birth"
        assert len(vc.vocabTerms) == 1
        assert len(vc.definitions) == 1

    def test_vocab_concepts_container(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_vocab import VocabConcepts, VocabConcept
        vcs = VocabConcepts(vocabConcepts=[VocabConcept(id="VC1"), VocabConcept(id="VC2")])
        assert len(vcs.vocabConcepts) == 2


# ---------------------------------------------------------------------------
# Serialization smoke tests
# ---------------------------------------------------------------------------

class TestFsTypesSerialization:
    def test_ordinance_model_dump(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_ordinance import Ordinance, OrdinanceType
        from gedcomtools.gedcomx.resource import Resource
        o = Ordinance(type=OrdinanceType.Baptism, person=Resource(resourceId="P1"), fullName="John")
        d = o.model_dump(exclude_none=True)
        assert d["fullName"] == "John"

    def test_group_model_dump(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_group import Group, GroupMember
        g = Group(id="G1", name="Test", members=[GroupMember(contactName="Alice")])
        d = g.model_dump(exclude_none=True)
        assert d["name"] == "Test"
        assert d["members"][0]["contactName"] == "Alice"

    def test_vocab_concept_round_trip(self):
        from gedcomtools.gedcomx.extensions.fs.fs_types_vocab import VocabConcept
        vc = VocabConcept(id="VC1", description="Test concept")
        d = vc.model_dump(exclude_none=True)
        assert d["id"] == "VC1"
        assert d["description"] == "Test concept"
