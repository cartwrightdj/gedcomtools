"""
Example: deserialize FamilySearch JSON fixtures into typed gedcomtools models.

Run with:

    PYTHONPATH=src python3 examples/familysearch_deserialize.py

Updated: 2026-04-08 — demonstrate typed FamilySearchPlatform and
FamilySearchPersonEnvelope deserialization from sample_data fixtures
"""
from __future__ import annotations

import json
from pathlib import Path

from gedcomtools.gedcomx.extensible import import_plugins


ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = ROOT / ".sample_data" / "familysearch"
PLATFORM_JSON = SAMPLE_DIR / "familysearch_platform_lrx2-tyy.json"
ENVELOPE_JSON = SAMPLE_DIR / "familysearch_person_envelope_lrx2-tyy.json"


def load_json(path: Path) -> dict:
    """Read one sample JSON file from disk."""
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def main() -> None:
    # Load the FamilySearch extension plugin so the FS-specific fields
    # like PersonInfo, NameFormInfo, DisplayProperties, and the platform
    # envelope are registered before we deserialize the JSON.
    import_plugins("gedcomx")

    # Import the typed models after plugin registration.
    from gedcomtools.gedcomx.extensions.fs import (
        FamilySearchPersonEnvelope,
        FamilySearchPlatform,
    )

    # The first fixture is the documented FamilySearchPlatform payload.
    platform_payload = load_json(PLATFORM_JSON)
    platform = FamilySearchPlatform.model_validate(platform_payload)

    # The second fixture is the observed outer wrapper used by FamilySearch
    # web payloads around the platform data and primary person.
    envelope_payload = load_json(ENVELOPE_JSON)
    envelope = FamilySearchPersonEnvelope.model_validate(envelope_payload)

    # Once deserialized, FamilySearch-specific fields are strongly typed.
    primary_person = platform.persons[0]
    assert primary_person.displayProperties is not None
    assert primary_person.facts[0].date is not None
    assert envelope.person is not None
    print("Platform persons:", len(platform.persons))
    print("Primary person name:", primary_person.displayProperties.name)
    print("Primary person birth date:", primary_person.displayProperties.birthDate)
    print("Primary person edit flag:", primary_person.personInfo[0].canUserEdit)
    print("Primary name form order:", primary_person.names[0].nameForms[0].nameFormInfo[0].order)
    print("First normalized date type:", type(primary_person.facts[0].date.normalized[0]).__name__)

    # The display() helper prefers deserialized FamilySearch display data and
    # fills any missing fields from the underlying person facts and names.
    print("Envelope title:", envelope.title)
    print("Envelope summary:", envelope.summary)
    print("Envelope display dict:", envelope.person.display())


if __name__ == "__main__":
    main()
