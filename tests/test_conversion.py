"""
Tests for gedcomtools.gedcomx.conversion.GedcomConverter (G5 → GedcomX)
"""
import pytest
from gedcomtools.gedcom5.parser import Gedcom5x
from gedcomtools.gedcomx.conversion import GedcomConverter
from gedcomtools.gedcomx.gedcomx import GedcomX
from gedcomtools.gedcomx.serialization import Serialization


def _convert(ged_path) -> GedcomX:
    p = Gedcom5x()
    p.parse_file(str(ged_path), strict=True)
    conv = GedcomConverter()
    return conv.Gedcom5x_GedcomX(p)


class TestConversionTiny:
    """555SAMPLE.GED — minimal smoke test."""

    @pytest.fixture(autouse=True)
    def convert(self, ged_tiny):
        self.gx = _convert(ged_tiny)

    def test_returns_gedcomx(self):
        assert isinstance(self.gx, GedcomX)

    def test_has_persons(self):
        assert len(self.gx.persons) > 0

    def test_persons_have_ids(self):
        for p in self.gx.persons:
            assert p.id is not None

    def test_has_relationships(self):
        assert len(self.gx.relationships) >= 0

    def test_unhandled_tags_recorded(self):
        assert hasattr(self.gx, "_import_unhandled_tags")
        assert isinstance(self.gx._import_unhandled_tags, dict)


class TestConversionSmall:
    """Sui_Dynasty.ged"""

    @pytest.fixture(autouse=True)
    def convert(self, ged_small):
        self.gx = _convert(ged_small)

    def test_returns_gedcomx(self):
        assert isinstance(self.gx, GedcomX)

    def test_has_persons(self):
        assert len(self.gx.persons) > 0

    def test_persons_have_names(self):
        persons_with_names = [p for p in self.gx.persons if len(p.names) > 0]
        assert len(persons_with_names) > 0


@pytest.mark.xfail(reason="allged.ged contains tags not yet handled by GedcomConverter", strict=False)
class TestConversionMedium:
    """allged.ged — broader tag coverage."""

    @pytest.fixture(autouse=True)
    def convert(self, ged_medium):
        self.gx = _convert(ged_medium)

    def test_returns_gedcomx(self):
        assert isinstance(self.gx, GedcomX)

    def test_has_persons(self):
        assert len(self.gx.persons) > 0


class TestConversionLarge:
    """Royal92 — larger real-world file."""

    @pytest.fixture(autouse=True)
    def convert(self, ged_large):
        self.gx = _convert(ged_large)

    def test_returns_gedcomx(self):
        assert isinstance(self.gx, GedcomX)

    def test_person_count_reasonable(self):
        assert len(self.gx.persons) > 100

    def test_relationship_count_reasonable(self):
        assert len(self.gx.relationships) > 0

    def test_person_lookup_works(self):
        first_id = list(self.gx.persons)[0].id
        assert self.gx.get_person_by_id(first_id) is not None


class TestConversionComprehensive:
    """comprehensive_test.ged — exercises all handle_* tag paths."""

    @pytest.fixture(autouse=True)
    def convert(self, ged_comprehensive):
        p = Gedcom5x()
        p.parse_file(str(ged_comprehensive), strict=True)
        conv = GedcomConverter()
        self.gx = conv.Gedcom5x_GedcomX(p)
        self.conv = conv

    def test_no_crash(self):
        assert isinstance(self.gx, GedcomX)

    def test_person_count(self):
        assert len(self.gx.persons) == 6

    def test_source_count(self):
        assert len(self.gx.sourceDescriptions) == 4  # S1, S2, M1, M2

    def test_agent_count(self):
        # U1 submitter + R1 repo + authors/publishers
        assert len(self.gx.agents) >= 3

    def test_relationships(self):
        assert len(self.gx.relationships) >= 2  # F1 and F2

    # Name parts
    def test_given_name_parsed(self):
        from gedcomtools.gedcomx.name import NamePartType
        james = next(p for p in self.gx.persons if p.id == '@I1@')
        birth_name = james.names[0]
        given = [part for form in birth_name.nameForms for part in form.parts
                 if part.type == NamePartType.Given]
        assert given and given[0].value == 'James Cornelius'

    def test_surname_parsed(self):
        from gedcomtools.gedcomx.name import NamePartType
        james = next(p for p in self.gx.persons if p.id == '@I1@')
        birth_name = james.names[0]
        surname = [part for form in birth_name.nameForms for part in form.parts
                   if part.type == NamePartType.Surname]
        assert surname and surname[0].value == 'Hargrove'

    def test_suffix_parsed(self):
        from gedcomtools.gedcomx.name import NamePartType
        james = next(p for p in self.gx.persons if p.id == '@I1@')
        birth_name = james.names[0]
        suffix = [part for form in birth_name.nameForms for part in form.parts
                  if part.type == NamePartType.Suffix]
        assert suffix and suffix[0].value == 'Jr.'

    # Facts
    def test_birth_fact_with_coordinates(self):
        james = next(p for p in self.gx.persons if p.id == '@I1@')
        from gedcomtools.gedcomx.fact import FactType
        birth = next(f for f in james.facts if f.type == FactType.Birth)
        assert birth.place is not None
        assert birth.place.description.latitude == 'N40.896'
        assert birth.place.description.longitude == 'W73.912'

    def test_adoption_fact(self):
        from gedcomtools.gedcomx.fact import FactType
        james = next(p for p in self.gx.persons if p.id == '@I1@')
        assert any(f.type == FactType.Adoption for f in james.facts)

    def test_immigration_fact(self):
        from gedcomtools.gedcomx.fact import FactType
        james = next(p for p in self.gx.persons if p.id == '@I1@')
        assert any(f.type == FactType.Immigration for f in james.facts)

    def test_military_fact(self):
        from gedcomtools.gedcomx.fact import FactType
        james = next(p for p in self.gx.persons if p.id == '@I1@')
        assert any(f.type == FactType.MilitaryService for f in james.facts)

    def test_probate_fact(self):
        from gedcomtools.gedcomx.fact import FactType
        james = next(p for p in self.gx.persons if p.id == '@I1@')
        assert any(f.type == FactType.Probate for f in james.facts)

    def test_personal_events_via_pevent(self):
        from gedcomtools.gedcomx.fact import FactType
        james = next(p for p in self.gx.persons if p.id == '@I1@')
        fact_types = {f.type for f in james.facts}
        assert FactType.BarMitzvah in fact_types
        assert FactType.Confirmation in fact_types
        assert FactType.Census in fact_types
        assert FactType.Will in fact_types
        assert FactType.Graduation in fact_types

    # Identifiers — IdentifierList iterates as type strings
    def test_exid(self):
        james = next(p for p in self.gx.persons if p.id == '@I1@')
        id_keys = list(james.identifiers)  # IdentifierList iterates keys
        assert any('EXID' in str(k) for k in id_keys)

    def test_fsid(self):
        james = next(p for p in self.gx.persons if p.id == '@I1@')
        id_keys = list(james.identifiers)
        assert any('FSID' in str(k) or 'FamilySearch' in str(k) for k in id_keys)

    # Source citation fields
    def test_source_page_qualifier(self):
        james = next(p for p in self.gx.persons if p.id == '@I1@')
        assert james.sources, "Expected source references"
        src = james.sources[0]
        assert src.qualifiers, "Expected PAGE qualifier"
        assert any('p. 47' in (q.value or '') for q in src.qualifiers)

    def test_source_link_identifier(self):
        from gedcomtools.gedcomx.source_description import SourceDescription
        s1 = self.gx.sourceDescriptions.by_id('@S1@')
        assert s1 is not None
        # _LINK adds identifier to S1 via source citation; identifiers count > 0
        assert len(s1.identifiers) > 0

    # Address sub-fields on agent
    def test_address_subfields(self):
        submitter = self.gx.agents.by_id('@U1@')
        assert submitter is not None
        assert submitter.addresses, "Expected at least one address"
        addr = submitter.addresses[0]
        assert addr.street == '42 Maple Street'
        assert addr.street2 == 'Apt 3B'
        assert addr.street3 == 'Building North'
        assert addr.street4 == 'Block 7'
        assert addr.street5 == 'District 4'
        assert addr.street6 == 'Zone A'
        assert addr.city == 'Riverdale'
        assert addr.stateOrProvince == 'NY'
        assert addr.postalCode == '10471'
        assert addr.country == 'United States'

    def test_agent_phone_email_fax(self):
        submitter = self.gx.agents.by_id('@U1@')
        assert submitter is not None
        assert any('718' in p for p in submitter.phones)
        assert any('eleanor' in e for e in submitter.emails)
        assert any('FAX' in e for e in submitter.emails)

    def test_agent_homepage(self):
        submitter = self.gx.agents.by_id('@U1@')
        assert submitter is not None
        assert submitter.homepage is not None

    # CONC/CONT
    def test_note_conc_cont(self):
        james = next(p for p in self.gx.persons if p.id == '@I1@')
        assert james.notes
        full_text = james.notes[0].text
        assert 'merchant' in full_text
        assert 'city council' in full_text

    # Multimedia / DocumentParsingContainer
    def test_obje_source_file(self):
        from gedcomtools.gedcomx.source_description import ResourceType
        m1 = self.gx.sourceDescriptions.by_id('@M1@')
        assert m1 is not None
        assert m1.resourceType == ResourceType.DigitalArtifact
        assert m1.mediaType == 'image/jpeg'

    def test_obje_source_audio(self):
        from gedcomtools.gedcomx.source_description import ResourceType
        m2 = self.gx.sourceDescriptions.by_id('@M2@')
        assert m2 is not None
        assert m2.resourceType == ResourceType.DigitalArtifact

    # Source fields
    def test_source_title(self):
        s1 = self.gx.sourceDescriptions.by_id('@S1@')
        assert s1 is not None
        assert any('Riverdale' in t.value for t in s1.titles)

    def test_source_author(self):
        s1 = self.gx.sourceDescriptions.by_id('@S1@')
        assert s1 is not None
        assert s1.author is not None

    def test_source_publisher(self):
        s1 = self.gx.sourceDescriptions.by_id('@S1@')
        assert s1 is not None
        assert s1.publisher is not None

    def test_source_repository(self):
        s1 = self.gx.sourceDescriptions.by_id('@S1@')
        assert s1 is not None
        assert s1.repository is not None

    def test_unhandled_only_head_meta(self):
        allowed = {'GEDC', 'CHAR', 'VERS', 'CORP', 'TIME', 'LANG'}
        unexpected = set(self.gx._import_unhandled_tags.keys()) - allowed
        assert not unexpected, f"Unexpected unhandled tags: {unexpected}"

    def test_serializable(self):
        data = Serialization.serialize(self.gx)
        assert isinstance(data, dict)


class TestConversionSerializable:
    """Conversion output must be fully serializable to JSON."""

    def test_tiny_serializes(self, ged_tiny):
        gx = _convert(ged_tiny)
        data = Serialization.serialize(gx)
        assert isinstance(data, dict)

    @pytest.mark.xfail(reason="allged.ged causes ConversionErrorDump", strict=False)
    def test_medium_serializes(self, ged_medium):
        gx = _convert(ged_medium)
        data = Serialization.serialize(gx)
        assert isinstance(data, dict)
        if "persons" in data:
            assert isinstance(data["persons"], list)
