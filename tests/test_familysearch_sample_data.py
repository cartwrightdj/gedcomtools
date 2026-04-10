"""
Tests for FamilySearch sample JSON fixtures stored in .sample_data/familysearch.

Updated: 2026-04-08 — validate FamilySearchPlatform and the observed
FamilySearchPersonEnvelope wrapper against disk fixtures
"""
from __future__ import annotations

import json
from pathlib import Path

from gedcomtools.gedcomx.extensible import import_plugins


SAMPLE_DIR = Path(__file__).parent.parent / ".sample_data" / "familysearch"
PLATFORM_JSON = SAMPLE_DIR / "familysearch_platform_lrx2-tyy.json"
ENVELOPE_JSON = SAMPLE_DIR / "familysearch_person_envelope_lrx2-tyy.json"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


class TestFamilySearchSampleData:
    def test_platform_fixture_deserializes(self):
        import_plugins("gedcomx")

        from gedcomtools.gedcomx.date import DateNormalization
        from gedcomtools.gedcomx.extensions.fs import FamilySearchPlatform

        payload = _load_json(PLATFORM_JSON)
        platform = FamilySearchPlatform.model_validate(payload)

        assert len(platform.childAndParentsRelationships) == 2
        assert len(platform.persons) == 3
        assert platform.persons[0].displayProperties is not None
        assert platform.persons[0].displayProperties.name == "Gerald F. Cartwright"
        assert platform.persons[0].personInfo[0].canUserEdit is True
        assert platform.persons[0].names[0].nameForms[0].nameFormInfo[0].order == "http://familysearch.org/v1/Eurotypic"
        assert platform.persons[0].facts[0].date is not None
        assert isinstance(platform.persons[0].facts[0].date.normalized[0], DateNormalization)
        assert len(platform.places) == 4
        assert len(platform.relationships) == 3
        assert platform.sourceDescriptions[1].resourceType is not None
        assert platform.sourceDescriptions[1].resourceType.value == "http://familysearch.org/FamilyTree"

    def test_envelope_fixture_deserializes(self):
        import_plugins("gedcomx")

        from gedcomtools.gedcomx.extensions.fs import FamilySearchPersonEnvelope

        payload = _load_json(ENVELOPE_JSON)
        envelope = FamilySearchPersonEnvelope.model_validate(payload)

        assert envelope.id == "LRX2-TYY"
        assert envelope.personId == "LRX2-TYY"
        assert envelope.title == "Gerald F. Cartwright"
        assert envelope.person is not None
        assert envelope.person.displayProperties is not None
        assert envelope.person.displayProperties.birthDate == "12 August 1917"
        assert envelope.person.display()["deathPlace"] == "Hunt, Portage, Livingston, New York, United States"
        assert envelope.data is not None
        assert envelope.data.persons[0].displayProperties is not None
        assert envelope.data.persons[0].displayProperties.lifespan == "1917-1996"
