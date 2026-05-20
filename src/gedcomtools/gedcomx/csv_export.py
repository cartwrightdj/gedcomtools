"""CSV export helpers for GedcomX top-level collections."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable

from .fact import Fact, FactType
from .gedcomx import GedcomX
from .person import Person
from .resource import Resource


def _enum_name(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "name"):
        return str(value.name)
    text = str(value)
    return text.rsplit("/", maxsplit=1)[-1]


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Resource):
        if value.resource is not None:
            return str(value.resource)
        return value.resourceId or ""
    if hasattr(value, "target"):
        return str(value.target)
    if hasattr(value, "value"):
        return _text(value.value)
    if hasattr(value, "original") and value.original:
        return str(value.original)
    if hasattr(value, "formal") and value.formal:
        return str(value.formal)
    if hasattr(value, "id") and value.id:
        return str(value.id)
    return str(value)


def _join(values: Iterable[Any]) -> str:
    return ";".join(text for value in values if (text := _text(value)))


def _notes(obj: Any) -> str:
    return ";".join(
        " ".join(note.text.split())
        for note in getattr(obj, "notes", [])
        if getattr(note, "text", None)
    )


def _sources(obj: Any) -> str:
    return ";".join(
        ref
        for source in getattr(obj, "sources", [])
        if (ref := source.descriptionId or _text(source.description))
    )


def _identifiers(obj: Any) -> str:
    identifiers = getattr(obj, "identifiers", None)
    if not identifiers:
        return ""
    values: list[str] = []
    for identifier in identifiers:
        values.extend(_text(value) for value in getattr(identifier, "values", []) if _text(value))
    return _join(values)


def _name(person: Person) -> str:
    try:
        return person.names[0].nameForms[0].fullText or ""
    except (AttributeError, IndexError):
        return ""


def _first_fact(person: Person, fact_type: FactType) -> Fact | None:
    for fact in person.facts:
        if fact.type == fact_type:
            return fact
    return None


def _fact_date(fact: Fact | None) -> str:
    return _text(fact.date) if fact is not None else ""


def _fact_place(fact: Fact | None) -> str:
    return _text(fact.place) if fact is not None else ""


def _fact_types(facts: Iterable[Fact]) -> str:
    return _join(_enum_name(fact.type) for fact in facts)


def _person_ref(value: Any) -> str:
    if isinstance(value, Person):
        return value.id or ""
    return _text(value)


def _write_csv(path: Path, headers: list[str], rows: list[list[Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(["" if value is None else value for value in row])
    return len(rows)


def export_gedcomx_csv(gx: GedcomX, output_base: str | Path) -> dict[str, dict[str, Any]]:
    """Write one CSV for each GedcomX top-level collection.

    ``output_base`` is treated as a filename prefix. For example, ``out/family``
    writes ``out/family_persons.csv``, ``out/family_relationships.csv``, and so on.
    Returns a mapping of collection name to output path and row count.
    """
    base = Path(output_base)
    if not base.name:
        raise ValueError(f"output_base must be a file prefix, not a bare directory: {output_base!r}")

    persons = list(gx.persons)
    relationships = list(gx.relationships)
    source_descriptions = list(gx.sourceDescriptions)
    agents = list(gx.agents)
    events = list(gx.events)
    documents = list(gx.documents)
    places = list(gx.places)
    groups = list(gx.groups)

    specs: dict[str, dict[str, Any]] = {
        "persons": {
            "path": base.parent / f"{base.name}_persons.csv",
            "headers": [
                "id", "name", "gender", "living", "private",
                "birth_date", "birth_place", "death_date", "death_place",
                "fact_types", "source_refs", "note_texts", "media_refs", "identifiers",
            ],
            "rows": [
                [
                    person.id or "", _name(person), _enum_name(getattr(person.gender, "type", None)),
                    person.living if person.living is not None else "",
                    person.private if person.private is not None else "",
                    _fact_date(_first_fact(person, FactType.Birth)),
                    _fact_place(_first_fact(person, FactType.Birth)),
                    _fact_date(_first_fact(person, FactType.Death)),
                    _fact_place(_first_fact(person, FactType.Death)),
                    _fact_types(person.facts),
                    _sources(person),
                    _notes(person),
                    _join(getattr(media, "descriptionId", "") or getattr(media, "description", "") for media in getattr(person, "media", [])),
                    _identifiers(person),
                ]
                for person in persons
            ],
        },
        "relationships": {
            "path": base.parent / f"{base.name}_relationships.csv",
            "headers": ["id", "type", "person1", "person2", "fact_types", "source_refs", "note_texts"],
            "rows": [
                [
                    rel.id or "", _enum_name(rel.type), _person_ref(rel.person1), _person_ref(rel.person2),
                    _fact_types(rel.facts), _sources(rel), _notes(rel),
                ]
                for rel in relationships
            ],
        },
        "source_descriptions": {
            "path": base.parent / f"{base.name}_source_descriptions.csv",
            "headers": [
                "id", "resource_type", "title", "media_type", "about", "created", "modified",
                "published", "repository", "citations", "notes", "identifiers",
            ],
            "rows": [
                [
                    sd.id or "", _enum_name(sd.resourceType),
                    _join(title.value for title in sd.titles), sd.mediaType or "",
                    _text(sd.about), _text(sd.created), _text(sd.modified), _text(sd.published),
                    _text(sd.repository), _join(citation.value for citation in sd.citations),
                    _notes(sd), _identifiers(sd),
                ]
                for sd in source_descriptions
            ],
        },
        "agents": {
            "path": base.parent / f"{base.name}_agents.csv",
            "headers": ["id", "names", "homepage", "openid", "emails", "phones", "addresses", "identifiers"],
            "rows": [
                [
                    agent.id or "", _join(name.value for name in agent.names), _text(agent.homepage),
                    _text(agent.openid), _join(agent.emails), _join(agent.phones),
                    _join(agent.addresses), _identifiers(agent),
                ]
                for agent in agents
            ],
        },
        "events": {
            "path": base.parent / f"{base.name}_events.csv",
            "headers": ["id", "type", "date", "place", "roles", "source_refs", "note_texts"],
            "rows": [
                [
                    event.id or "", _enum_name(event.type), _text(event.date), _text(event.place),
                    _join(f"{_enum_name(role.type)}:{_person_ref(role.person)}" for role in event.roles),
                    _sources(event), _notes(event),
                ]
                for event in events
            ],
        },
        "documents": {
            "path": base.parent / f"{base.name}_documents.csv",
            "headers": ["id", "type", "text_type", "extracted", "text", "source_refs", "note_texts"],
            "rows": [
                [
                    doc.id or "", _enum_name(doc.type), _enum_name(doc.textType),
                    doc.extracted if doc.extracted is not None else "",
                    " ".join((doc.text or "").split()), _sources(doc), _notes(doc),
                ]
                for doc in documents
            ],
        },
        "places": {
            "path": base.parent / f"{base.name}_places.csv",
            "headers": ["id", "names", "type", "place", "latitude", "longitude", "jurisdiction"],
            "rows": [
                [
                    place.id or "", _join(name.value for name in (place.names or [])), place.type or "",
                    _text(place.place), place.latitude or "", place.longitude or "", _text(place.jurisdiction),
                ]
                for place in places
            ],
        },
        "groups": {
            "path": base.parent / f"{base.name}_groups.csv",
            "headers": ["id", "names", "date", "place", "roles", "source_refs", "note_texts"],
            "rows": [
                [
                    group.id or "", _join(name.value for name in group.names), _text(group.date),
                    _text(group.place), _join(f"{_enum_name(role.type)}:{_person_ref(role.person)}" for role in group.roles),
                    _sources(group), _notes(group),
                ]
                for group in groups
            ],
        },
    }

    result: dict[str, dict[str, Any]] = {}
    for name, spec in specs.items():
        rows = spec["rows"]
        row_count = _write_csv(spec["path"], spec["headers"], rows)
        result[name] = {"path": spec["path"], "rows": row_count}
    return result
