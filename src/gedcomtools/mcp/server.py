from __future__ import annotations

import json
import logging
import sys
from collections import Counter
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from dataclasses import asdict, is_dataclass
from functools import lru_cache
from io import StringIO
from pathlib import Path
from typing import Any

import orjson

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - exercised by optional installs
    raise ImportError(
        "The gedcomtools MCP server requires the optional 'mcp' dependency. "
        "Install it with: pip install 'gedcomtools[mcp]'"
    ) from exc


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    if hasattr(value, "value"):
        return value.value
    return str(value)


def _dump_json_bytes(value: Any) -> bytes:
    return orjson.dumps(
        value,
        default=_json_default,
        option=orjson.OPT_INDENT_2 | orjson.OPT_APPEND_NEWLINE,
    )


@contextmanager
def _quiet_gedcomtools() -> Any:
    previous_disable_level = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            yield
    finally:
        logging.disable(previous_disable_level)


def _ensure_input_file(file_path: str) -> Path:
    path = Path(file_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"File does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")
    return path


def _ensure_output_file(output_path: str, *, overwrite: bool) -> Path:
    path = Path(output_path).expanduser()
    if path.exists() and not overwrite:
        raise FileExistsError(f"Output file exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _load_gedcom5x(file_path: str, *, strict: bool) -> Any:
    return _load_gedcom5x_cached(str(_ensure_input_file(file_path).resolve()), strict)


@lru_cache(maxsize=8)
def _load_gedcom5x_cached(file_path: str, strict: bool) -> Any:
    from gedcomtools.gedcom5.parser import Gedcom5x

    parser = Gedcom5x()
    with _quiet_gedcomtools():
        parser.parse_file(file_path, strict)
    return parser


def _convert_gedcom5x(file_path: str, *, strict: bool) -> tuple[Any, Any]:
    from gedcomtools.gedcomx import GedcomConverter

    parser = _load_gedcom5x(file_path, strict=strict)
    converter = GedcomConverter()
    with _quiet_gedcomtools():
        gedcomx = converter.Gedcom5x_GedcomX(parser)
    return gedcomx, converter


def _detect_gedcom_version(file_path: str) -> str | None:
    path = _ensure_input_file(file_path)
    context: dict[int, str] = {}
    with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.strip("\r\n")
            if not line:
                continue
            parts = line.split(maxsplit=3)
            if len(parts) < 2:
                continue
            try:
                level = int(parts[0])
            except ValueError:
                continue
            if parts[1].startswith("@") and parts[1].endswith("@"):
                if len(parts) < 3:
                    continue
                tag = parts[2].upper()
                value = parts[3] if len(parts) > 3 else ""
            else:
                tag = parts[1].upper()
                value = " ".join(parts[2:]) if len(parts) > 2 else ""
            context[level] = tag
            for stale in [k for k in context if k > level]:
                del context[stale]
            if tag == "VERS" and context.get(level - 1) == "GEDC" and context.get(level - 2) == "HEAD":
                return value.strip() or None
    return None


def _classify_gedcom_version(version: str | None) -> str:
    if not version:
        return "unknown"
    stripped = version.strip()
    if stripped.startswith("7"):
        return "GEDCOM 7"
    if stripped.startswith("5"):
        return "GEDCOM 5.x"
    return f"GEDCOM {stripped}"


def _load_gedcomx_json(file_path: str) -> Any:
    return _load_gedcomx_json_cached(str(_ensure_input_file(file_path).resolve()))


@lru_cache(maxsize=8)
def _load_gedcomx_json_cached(file_path: str) -> Any:
    from gedcomtools.gedcomx import GedcomX
    from gedcomtools.gedcomx.serialization import Serialization

    data = orjson.loads(Path(file_path).read_bytes())
    if not isinstance(data, dict):
        return data
    with _quiet_gedcomtools():
        try:
            return Serialization.deserialize(data=data, class_type=GedcomX)
        except Exception:
            try:
                return GedcomX(**data)
            except Exception:
                return data


def _collection_len(obj: Any, attr: str) -> int:
    value = getattr(obj, attr, None)
    if value is None:
        return 0
    try:
        return len(value)
    except TypeError:
        return sum(1 for _ in value)


def _top_level_records(parser: Any) -> list[Any]:
    return list(parser.get_root_child_elements())


def _all_records(parser: Any) -> list[Any]:
    records: list[Any] = []

    def visit(record: Any) -> None:
        records.append(record)
        for child in _child_records(record):
            visit(child)

    for record in _top_level_records(parser):
        visit(record)
    return records


def _top_level_tag_counts(parser: Any) -> dict[str, int]:
    return dict(Counter(record.tag for record in _top_level_records(parser)))


def _sample_records(records: list[Any], limit: int) -> list[dict[str, Any]]:
    sample = []
    for record in records[: max(0, limit)]:
        sample.append(
            {
                "line_num": getattr(record, "_line_num", None),
                "level": getattr(record, "level", None),
                "xref": getattr(record, "xref", None),
                "tag": getattr(record, "tag", None),
                "value": getattr(record, "value", None),
                "children": len(_child_records(record)),
            }
        )
    return sample


def _gedcomx_counts(gedcomx: Any) -> dict[str, int]:
    return {
        "persons": _collection_len(gedcomx, "persons"),
        "relationships": _collection_len(gedcomx, "relationships"),
        "source_descriptions": _collection_len(gedcomx, "sourceDescriptions"),
        "agents": _collection_len(gedcomx, "agents"),
        "events": _collection_len(gedcomx, "events"),
        "documents": _collection_len(gedcomx, "documents"),
        "places": _collection_len(gedcomx, "places"),
        "groups": _collection_len(gedcomx, "groups"),
    }


def _normalize_xref(xref: str | None) -> str:
    if not xref:
        return ""
    xref = xref.strip()
    return xref if xref.startswith("@") and xref.endswith("@") else f"@{xref.strip('@')}@"


def _element_dict(parser: Any) -> dict[str, Any]:
    return parser.get_element_dictionary()


def _find_element(parser: Any, xref: str) -> Any:
    normalized = _normalize_xref(xref)
    element = _element_dict(parser).get(normalized)
    if element is None:
        raise KeyError(f"No GEDCOM record found for xref {normalized!r}")
    return element


def _find_individual(parser: Any, xref: str) -> Any:
    individual = _find_element(parser, xref)
    if getattr(individual, "tag", None) != "INDI":
        raise TypeError(f"{_normalize_xref(xref)} is a {individual.tag} record, not an INDI record")
    return individual


def _child_records(element: Any, tag: str | None = None) -> list[Any]:
    records = element.sub_records(tag) if tag else element.sub_records()
    return list(records or [])


def _first_child_value(element: Any, tag: str) -> str | None:
    child = element.sub_record(tag)
    if child is None:
        return None
    value = child.get_multi_line_value()
    return value if value != "" else None


def _record_summary(element: Any) -> dict[str, Any]:
    return {
        "xref": getattr(element, "xref", ""),
        "tag": getattr(element, "tag", ""),
        "line_num": getattr(element, "_line_num", None),
        "value": getattr(element, "value", ""),
        "child_count": len(_child_records(element)),
    }


def _source_record_summary(parser: Any, xref: str) -> dict[str, Any]:
    source = _element_dict(parser).get(_normalize_xref(xref))
    if source is None:
        return {"xref": _normalize_xref(xref), "missing": True}
    return {
        **_record_summary(source),
        "title": _first_child_value(source, "TITL"),
        "author": _first_child_value(source, "AUTH"),
        "publication": _first_child_value(source, "PUBL"),
        "repository": _first_child_value(source, "REPO"),
        "text": _first_child_value(source, "TEXT"),
    }


def _source_citation(parser: Any, source_element: Any) -> dict[str, Any]:
    citation = {
        "xref": source_element.value,
        "page": _first_child_value(source_element, "PAGE"),
        "text": None,
        "quality": _first_child_value(source_element, "QUAY"),
        "record": None,
    }
    data = source_element.sub_record("DATA")
    if data is not None:
        text = data.sub_record("TEXT")
        if text is not None:
            citation["text"] = text.get_multi_line_value()
    if source_element.value:
        citation["record"] = _source_record_summary(parser, source_element.value)
    return citation


def _sources_for_element(parser: Any, element: Any, *, recursive: bool) -> list[dict[str, Any]]:
    citations = [_source_citation(parser, source) for source in _child_records(element, "SOUR")]
    if recursive:
        for child in _child_records(element):
            citations.extend(_sources_for_element(parser, child, recursive=True))
    return citations


def _event_summary(parser: Any, event: Any) -> dict[str, Any]:
    return {
        "tag": event.tag,
        "value": event.get_multi_line_value(),
        "date": _first_child_value(event, "DATE"),
        "place": _first_child_value(event, "PLAC"),
        "age": _first_child_value(event, "AGE"),
        "cause": _first_child_value(event, "CAUS"),
        "type": _first_child_value(event, "TYPE"),
        "sources": _sources_for_element(parser, event, recursive=False),
        "notes": [_note_summary(note) for note in _child_records(event, "NOTE")],
    }


def _note_summary(note: Any) -> dict[str, Any]:
    return {
        "xref": note.value if str(note.value).startswith("@") else None,
        "text": note.get_multi_line_value(),
    }


def _individual_summary(parser: Any, individual: Any, *, include_facts: bool = True) -> dict[str, Any]:
    given, surname = individual.get_name()
    birth_date, birth_place, birth_sources = individual.get_birth_data()
    death_date, death_place, death_sources = individual.get_death_data()
    facts = []
    if include_facts:
        skip_tags = {"NAME", "SEX", "FAMC", "FAMS", "SOUR", "NOTE", "OBJE", "CHAN", "REFN", "UID"}
        for child in _child_records(individual):
            if child.tag not in skip_tags:
                facts.append(_event_summary(parser, child))

    return {
        "xref": individual.xref,
        "line_num": getattr(individual, "_line_num", None),
        "name": " ".join(part for part in [given, surname] if part).strip() or None,
        "names": individual.get_all_names(),
        "given_name": given or None,
        "surname": surname or None,
        "gender": individual.get_gender() or None,
        "birth": {
            "date": birth_date or None,
            "place": birth_place or None,
            "source_xrefs": birth_sources,
        },
        "death": {
            "date": death_date or None,
            "place": death_place or None,
            "source_xrefs": death_sources,
        },
        "occupation": individual.get_occupation() or None,
        "is_deceased": individual.is_deceased(),
        "is_private": individual.is_private(),
        "family_as_child": [child.value for child in _child_records(individual, "FAMC")],
        "family_as_spouse": [child.value for child in _child_records(individual, "FAMS")],
        "notes": [_note_summary(note) for note in _child_records(individual, "NOTE")],
        "sources": _sources_for_element(parser, individual, recursive=False),
        "facts": facts,
    }


def _family_summary(parser: Any, family: Any) -> dict[str, Any]:
    husbands = _family_members(parser, family, "HUSB")
    wives = _family_members(parser, family, "WIFE")
    children = _family_members(parser, family, "CHIL")
    marriages = []
    for child in _child_records(family, "MARR"):
        marriages.append(_event_summary(parser, child))
    return {
        "xref": family.xref,
        "line_num": getattr(family, "_line_num", None),
        "husbands": [_individual_summary(parser, person, include_facts=False) for person in husbands],
        "wives": [_individual_summary(parser, person, include_facts=False) for person in wives],
        "children": [_individual_summary(parser, person, include_facts=False) for person in children],
        "marriages": marriages,
        "sources": _sources_for_element(parser, family, recursive=False),
        "notes": [_note_summary(note) for note in _child_records(family, "NOTE")],
    }


def _child_link_is_natural(family: Any, child_xref: str) -> bool | None:
    normalized = _normalize_xref(child_xref)
    for child_link in _child_records(family, "CHIL"):
        if _normalize_xref(child_link.value) != normalized:
            continue
        result: bool | None = None
        for sub in _child_records(child_link):
            if sub.tag == "PEDI":
                result = sub.value.strip().casefold() in {"birth", "natural"}
            elif sub.tag in {"_MREL", "_FREL"} and sub.value.strip().casefold() == "natural":
                result = True
        return result
    return None


def _families_for_individual(parser: Any, individual: Any, family_link_tag: str) -> list[Any]:
    families = []
    for link in _child_records(individual, family_link_tag):
        if not link.value:
            continue
        family = _element_dict(parser).get(_normalize_xref(link.value))
        if family is not None and getattr(family, "tag", None) == "FAM":
            families.append(family)
    return families


def _family_members(parser: Any, family: Any, member_tag: str) -> list[Any]:
    members = []
    for link in _child_records(family, member_tag):
        if not link.value:
            continue
        person = _element_dict(parser).get(_normalize_xref(link.value))
        if person is not None and getattr(person, "tag", None) == "INDI":
            members.append(person)
    return members


def _family_parents(parser: Any, family: Any) -> list[Any]:
    return [
        *_family_members(parser, family, "HUSB"),
        *_family_members(parser, family, "WIFE"),
    ]


def _parents_for_individual(parser: Any, individual: Any, *, natural_only: bool) -> list[Any]:
    from gedcomtools.gedcom5.tags import GEDCOM_TAG_FAMILY_CHILD

    parents = []
    seen: set[str] = set()
    for family in _families_for_individual(parser, individual, GEDCOM_TAG_FAMILY_CHILD):
        natural_status = _child_link_is_natural(family, individual.xref)
        if natural_only and natural_status is False:
            continue
        family_parents = _family_parents(parser, family)
        for parent in family_parents:
            if parent.xref not in seen:
                seen.add(parent.xref)
                parents.append(parent)
    return parents


def _ancestor_list(parser: Any, individual: Any, *, natural_only: bool, limit: int) -> list[Any]:
    ancestors = []
    seen: set[str] = set()

    def visit(person: Any) -> None:
        if len(ancestors) >= limit:
            return
        for parent in _parents_for_individual(parser, person, natural_only=natural_only):
            if parent.xref in seen:
                continue
            seen.add(parent.xref)
            ancestors.append(parent)
            visit(parent)

    visit(individual)
    return ancestors


def _path_to_ancestor(parser: Any, descendant: Any, ancestor: Any) -> list[Any] | None:
    def visit(person: Any, path: list[Any], seen: set[str]) -> list[Any] | None:
        if person.xref == ancestor.xref:
            return path
        for parent in _parents_for_individual(parser, person, natural_only=False):
            if parent.xref in seen:
                continue
            found = visit(parent, path + [parent], seen | {parent.xref})
            if found:
                return found
        return None

    return visit(descendant, [descendant], {descendant.xref})


def _record_tree(element: Any, *, max_depth: int, current_depth: int = 0) -> dict[str, Any]:
    node = {
        **_record_summary(element),
        "children": [],
    }
    if current_depth >= max_depth:
        node["children_truncated"] = len(_child_records(element))
        return node
    node["children"] = [
        _record_tree(child, max_depth=max_depth, current_depth=current_depth + 1)
        for child in _child_records(element)
    ]
    return node


def _matches_individual(individual: Any, query: str) -> bool:
    query = query.casefold().strip()
    if not query:
        return True
    values = [individual.xref, *individual.get_all_names(), individual.describe()]
    return any(query in str(value).casefold() for value in values)


def _short_type(value: Any) -> str:
    return getattr(type(value), "__name__", str(type(value)))


def _enum_label(value: Any) -> Any:
    if hasattr(value, "name"):
        return value.name
    if hasattr(value, "value"):
        raw = value.value
        return raw.rsplit("/", 1)[-1] if isinstance(raw, str) else raw
    return value


def _text_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _gx_collection_names(gx: Any) -> list[str]:
    names = [
        "persons",
        "relationships",
        "sourceDescriptions",
        "agents",
        "places",
        "events",
        "documents",
        "groups",
    ]
    return [name for name in names if hasattr(gx, name)]


def _gx_counts(gx: Any) -> dict[str, int]:
    if isinstance(gx, dict):
        return {key: len(value) for key, value in gx.items() if isinstance(value, list)}
    return {name: _collection_len(gx, name) for name in _gx_collection_names(gx)}


def _gx_id(value: Any) -> str | None:
    if isinstance(value, dict):
        return value.get("id")
    return getattr(value, "id", None)


def _gx_ref_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return value.get("resource") or value.get("resourceId") or value.get("value")
    for attr in ("resource", "resourceId", "resourceRef", "value"):
        if hasattr(value, attr):
            attr_value = getattr(value, attr, None)
            if attr_value:
                return str(attr_value)
    if hasattr(value, "id"):
        return f"#{value.id}"
    return None


def _gx_ref_id(value: Any) -> str | None:
    ref = _gx_ref_value(value)
    if not ref:
        return None
    return ref.rsplit("#", 1)[-1] if "#" in ref else ref


def _gx_resolve(gx: Any, value: Any) -> Any | None:
    ref_id = _gx_ref_id(value)
    if not ref_id or isinstance(gx, dict):
        return None
    return getattr(gx, "id_index", {}).get(ref_id)


def _gx_name(person: Any) -> str | None:
    if isinstance(person, dict):
        names = person.get("names") or []
        if names:
            forms = names[0].get("nameForms") or []
            if forms:
                return forms[0].get("fullText")
        return None
    try:
        return person.name
    except Exception:
        pass
    names = getattr(person, "names", None) or []
    if names:
        forms = getattr(names[0], "nameForms", None) or []
        if forms:
            return getattr(forms[0], "fullText", None)
    return None


def _gx_fact_summary(fact: Any) -> dict[str, Any]:
    if isinstance(fact, dict):
        fact_type = fact.get("type")
        date = fact.get("date") or {}
        place = fact.get("place") or {}
        return {
            "type": fact_type.rsplit("/", 1)[-1] if isinstance(fact_type, str) else fact_type,
            "date": date.get("original") if isinstance(date, dict) else date,
            "place": place.get("original") or place.get("description") if isinstance(place, dict) else place,
            "value": fact.get("value"),
        }
    place = getattr(fact, "place", None)
    return {
        "type": _enum_label(getattr(fact, "type", None)),
        "date": getattr(getattr(fact, "date", None), "original", None) or _text_value(getattr(fact, "date", None)),
        "place": getattr(place, "original", None) or _gx_ref_value(getattr(place, "description", None)) or _text_value(place),
        "value": getattr(fact, "value", None),
    }


def _gx_person_summary(person: Any) -> dict[str, Any]:
    if isinstance(person, dict):
        return {
            "id": person.get("id"),
            "type": "Person",
            "name": _gx_name(person),
            "gender": person.get("gender", {}).get("type") if isinstance(person.get("gender"), dict) else person.get("gender"),
            "facts": [_gx_fact_summary(fact) for fact in person.get("facts", [])],
        }
    gender = getattr(person, "gender", None)
    return {
        "id": getattr(person, "id", None),
        "type": "Person",
        "name": _gx_name(person),
        "gender": _enum_label(getattr(gender, "type", None)) if gender else None,
        "facts": [_gx_fact_summary(fact) for fact in getattr(person, "facts", [])],
    }


def _gx_relationship_summary(gx: Any, rel: Any) -> dict[str, Any]:
    if isinstance(rel, dict):
        return {
            "id": rel.get("id"),
            "type": rel.get("type"),
            "person1": rel.get("person1"),
            "person2": rel.get("person2"),
            "facts": [_gx_fact_summary(fact) for fact in rel.get("facts", [])],
        }
    p1 = getattr(rel, "person1", None)
    p2 = getattr(rel, "person2", None)
    p1_obj = p1 if hasattr(p1, "names") else _gx_resolve(gx, p1)
    p2_obj = p2 if hasattr(p2, "names") else _gx_resolve(gx, p2)
    return {
        "id": getattr(rel, "id", None),
        "type": _enum_label(getattr(rel, "type", None)),
        "person1": {
            "ref": _gx_ref_value(p1),
            "id": getattr(p1_obj, "id", None) if p1_obj is not None else _gx_ref_id(p1),
            "name": _gx_name(p1_obj) if p1_obj is not None else None,
        },
        "person2": {
            "ref": _gx_ref_value(p2),
            "id": getattr(p2_obj, "id", None) if p2_obj is not None else _gx_ref_id(p2),
            "name": _gx_name(p2_obj) if p2_obj is not None else None,
        },
        "facts": [_gx_fact_summary(fact) for fact in getattr(rel, "facts", [])],
    }


def _gx_source_summary(source: Any) -> dict[str, Any]:
    if isinstance(source, dict):
        titles = source.get("titles") or []
        return {
            "id": source.get("id"),
            "type": "SourceDescription",
            "resource_type": source.get("resourceType"),
            "title": titles[0].get("value") if titles and isinstance(titles[0], dict) else None,
            "media_type": source.get("mediaType"),
        }
    titles = getattr(source, "titles", []) or []
    return {
        "id": getattr(source, "id", None),
        "type": "SourceDescription",
        "resource_type": _enum_label(getattr(source, "resourceType", None)),
        "title": _text_value(titles[0]) if titles else None,
        "media_type": getattr(source, "mediaType", None),
    }


def _gx_object_summary(gx: Any, obj: Any) -> dict[str, Any]:
    type_name = _short_type(obj)
    if isinstance(obj, dict):
        type_name = "dict"
    if type_name == "Person" or (isinstance(obj, dict) and "names" in obj and "facts" in obj):
        return _gx_person_summary(obj)
    if type_name == "Relationship" or (isinstance(obj, dict) and "person1" in obj and "person2" in obj):
        return _gx_relationship_summary(gx, obj)
    if type_name == "SourceDescription":
        return _gx_source_summary(obj)
    return {
        "id": _gx_id(obj),
        "type": type_name,
        "preview": str(obj)[:300],
    }


def _gx_collection_items(gx: Any, collection: str) -> list[Any]:
    if isinstance(gx, dict):
        value = gx.get(collection)
        return value if isinstance(value, list) else []
    if not hasattr(gx, collection):
        raise KeyError(f"No GEDCOM X collection named {collection!r}")
    return list(getattr(gx, collection) or [])


def _gx_find_by_id(gx: Any, object_id: str) -> Any:
    object_id = object_id.strip().lstrip("#")
    if isinstance(gx, dict):
        for key, value in gx.items():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and item.get("id") == object_id:
                        return item
        raise KeyError(f"No GEDCOM X object found with id {object_id!r}")
    obj = getattr(gx, "id_index", {}).get(object_id)
    if obj is None:
        raise KeyError(f"No GEDCOM X object found with id {object_id!r}")
    return obj


def _gx_matches(obj: Any, query: str) -> bool:
    query = query.casefold().strip()
    if not query:
        return True
    summary = _gx_object_summary({}, obj)
    return query in json.dumps(summary, ensure_ascii=False, default=str).casefold()


STARTUP_GUIDE = """
This MCP server helps clients explore genealogy data in GEDCOM, GEDCOM 7, and GEDCOM X JSON files.

Always call `man` before using a tool for the first time in a session. Use `man()` for the overview,
or `man("tool_name")` for exact parameters, output shape, caveats, and examples.

GEDCOM basics:
- GEDCOM `.ged` files are line-oriented genealogy files. Each line has a level number, a tag, and
  sometimes a value or cross-reference pointer.
- Individuals are `INDI` records, usually identified by xrefs like `@I42@`.
- Families are `FAM` records, usually identified by xrefs like `@F7@`. Family records connect
  spouses/parents (`HUSB`, `WIFE`) and children (`CHIL`).
- Source records are `SOUR`; citations may also appear under people, events, families, and notes.
- Version is normally declared at `HEAD.GEDC.VERS`. Use `load_gedcom` or `get_gedcom_version`
  before choosing GEDCOM 5.x exploration tools vs GEDCOM 7 validation tools.

Workflow guidance:
1. Call `load_gedcom(file_path)` first. It returns detected format/version and summary counts.
2. For GEDCOM 5.x files, use `list_individuals` to find an xref, then use relationship tools such
   as `get_parents`, `get_children`, `get_spouses`, `get_siblings`, `get_ancestors`, and
   `get_descendants`.
3. For detailed evidence, use `get_individual`, `get_family`, `get_sources`, and `get_record_tree`.
4. For GEDCOM 7 files, use `validate_gedcom7` and `inspect_gedcom7`; the genealogy navigation tools
   are currently GEDCOM 5.x parser tools.
5. For GEDCOM X JSON, use `list_gedcomx_collections`, `search_gedcomx_persons`,
   `get_gedcomx_object`, `get_gedcomx_person_relationships`, and schema/reference tools.

Runtime note:
- This is a stdio MCP server. Parsed GEDCOM and GEDCOM X files are cached in-process, so repeated
  calls during a normal MCP session reuse loaded data.
""".strip()


TOOL_MANUAL: dict[str, dict[str, Any]] = {
    "man": {
        "purpose": "Read the server guide and detailed tool manual.",
        "when_to_use": "Call first in every session, and before using any unfamiliar tool.",
        "parameters": {"tool_name": "Optional exact tool name. Omit for overview and tool index."},
        "notes": ["The server instructions also ask clients to consult this manual before first use."],
    },
    "server_info": {
        "purpose": "Return runtime/import information for this MCP server.",
        "when_to_use": "Debugging environment, import path, Python version, or installed package location.",
        "parameters": {},
    },
    "load_gedcom": {
        "purpose": "Detect and summarize a GEDCOM `.ged` or GEDCOM X `.json` file.",
        "when_to_use": "First call for a new file. It returns format and GEDCOM version where available.",
        "parameters": {
            "file_path": "Path to `.ged` or GEDCOM X `.json`.",
            "strict": "GEDCOM 5.x parse strictness.",
            "sample_limit": "Number of raw sample records for GEDCOM 5.x summary.",
            "max_errors": "Maximum GEDCOM 7 validation errors returned.",
        },
        "returns": "Detected format/version plus counts. For GEDCOM 7, includes validation summary.",
    },
    "get_gedcom_version": {
        "purpose": "Read `HEAD.GEDC.VERS` from a GEDCOM `.ged` file.",
        "when_to_use": "When you only need version detection without parsing the whole file.",
        "parameters": {"file_path": "Path to a GEDCOM `.ged` file."},
    },
    "summarize_gedcom5x": {
        "purpose": "Parse a GEDCOM 5.x-style file and return record counts/sample records.",
        "when_to_use": "After `load_gedcom` identifies GEDCOM 5.x, or for quick file inventory.",
        "parameters": {"file_path": "GEDCOM path.", "strict": "Parser strictness.", "sample_limit": "Sample record count."},
    },
    "list_individuals": {
        "purpose": "Search/list GEDCOM 5.x `INDI` people.",
        "when_to_use": "Find a person's xref before calling relationship/profile tools.",
        "parameters": {"file_path": "GEDCOM path.", "query": "Name/xref/description substring.", "limit": "Max people returned.", "strict": "Parser strictness."},
        "example": "list_individuals(file_path, query='George Washington') returns xrefs like `@I33@`.",
    },
    "get_individual": {
        "purpose": "Return a GEDCOM 5.x person profile.",
        "when_to_use": "Inspect names, gender, birth/death, facts, notes, sources, and family links.",
        "parameters": {"file_path": "GEDCOM path.", "xref": "Individual xref like `@I33@`.", "strict": "Parser strictness.", "include_facts": "Include event/fact detail."},
    },
    "get_person_families": {
        "purpose": "Return families where a GEDCOM 5.x person is a child and spouse/parent.",
        "when_to_use": "Understand family context around an individual.",
        "parameters": {"file_path": "GEDCOM path.", "xref": "Individual xref.", "strict": "Parser strictness."},
    },
    "get_parents": {
        "purpose": "Return parents of a GEDCOM 5.x individual.",
        "when_to_use": "Answer questions like 'who are the parents of @I33?'.",
        "parameters": {"file_path": "GEDCOM path.", "xref": "Individual xref.", "strict": "Parser strictness.", "natural_only": "Respect natural/adoptive hints where present."},
    },
    "get_children": {
        "purpose": "Return children of a GEDCOM 5.x individual, grouped by family.",
        "when_to_use": "Answer questions like 'who are their children?' or 'who is the son/daughter of this person?'.",
        "parameters": {"file_path": "GEDCOM path.", "xref": "Individual xref.", "strict": "Parser strictness."},
    },
    "get_spouses": {
        "purpose": "Return spouses/co-parents of a GEDCOM 5.x individual.",
        "when_to_use": "Answer marriage/partner/co-parent questions.",
        "parameters": {"file_path": "GEDCOM path.", "xref": "Individual xref.", "strict": "Parser strictness."},
    },
    "get_siblings": {
        "purpose": "Return siblings based on shared child-family records.",
        "when_to_use": "Answer questions like 'who are this person's siblings?'.",
        "parameters": {"file_path": "GEDCOM path.", "xref": "Individual xref.", "strict": "Parser strictness."},
    },
    "get_ancestors": {
        "purpose": "Return recursive ancestors of a GEDCOM 5.x individual.",
        "when_to_use": "Build an ancestor list or answer lineage questions.",
        "parameters": {"file_path": "GEDCOM path.", "xref": "Individual xref.", "strict": "Parser strictness.", "natural_only": "Use natural/adoptive hints.", "limit": "Max ancestors returned."},
    },
    "get_descendants": {
        "purpose": "Return descendants grouped by generation.",
        "when_to_use": "Trace children, grandchildren, etc.",
        "parameters": {"file_path": "GEDCOM path.", "xref": "Individual xref.", "strict": "Parser strictness.", "generations": "Maximum generations."},
    },
    "get_family": {
        "purpose": "Return a GEDCOM 5.x family with spouses/parents, children, marriage events, notes, and sources.",
        "when_to_use": "Inspect a `FAM` xref returned by person-family tools.",
        "parameters": {"file_path": "GEDCOM path.", "family_xref": "Family xref like `@F18@`.", "strict": "Parser strictness."},
    },
    "get_sources": {
        "purpose": "List source records or citations attached to a record.",
        "when_to_use": "Investigate evidence for a person, family, event, or the source catalog.",
        "parameters": {"file_path": "GEDCOM path.", "xref": "Optional record xref. Omit to list source records.", "strict": "Parser strictness.", "limit": "Max source records returned."},
    },
    "get_record_tree": {
        "purpose": "Return raw GEDCOM tree for any xref.",
        "when_to_use": "Debug vendor-specific tags or inspect details not summarized elsewhere.",
        "parameters": {"file_path": "GEDCOM path.", "xref": "Any xref.", "strict": "Parser strictness.", "max_depth": "Tree depth cap."},
    },
    "find_relationship_path": {
        "purpose": "Find a direct ancestor path between two GEDCOM 5.x people.",
        "when_to_use": "Answer whether one person is an ancestor of another.",
        "parameters": {"file_path": "GEDCOM path.", "from_xref": "Descendant candidate.", "to_xref": "Ancestor candidate.", "strict": "Parser strictness."},
    },
    "convert_gedcom5x_to_gedcomx": {
        "purpose": "Convert GEDCOM 5.x to GEDCOM X JSON.",
        "when_to_use": "Export or normalize GEDCOM 5.x data into GEDCOM X model form.",
        "parameters": {"file_path": "GEDCOM path.", "output_path": "Optional JSON output.", "strict": "Parser strictness.", "overwrite": "Allow replacing output.", "include_json": "Return full JSON in MCP response."},
        "caveats": ["Large `include_json=True` responses may be too big for clients."],
    },
    "export_arango_graph": {
        "purpose": "Convert GEDCOM 5.x and write graph JSONL files.",
        "when_to_use": "Graph database import/export workflows.",
        "parameters": {"file_path": "GEDCOM path.", "output_dir": "Directory for JSONL files.", "strict": "Parser strictness.", "overwrite": "Allow replacing output."},
    },
    "validate_gedcom7": {
        "purpose": "Parse and validate GEDCOM 7 file structure/content.",
        "when_to_use": "After `load_gedcom` identifies GEDCOM 7.",
        "parameters": {"file_path": "GEDCOM 7 path.", "max_errors": "Error sample cap."},
    },
    "inspect_gedcom7": {
        "purpose": "Return compact GEDCOM 7 parsed tree summary.",
        "when_to_use": "Inspect top-level GEDCOM 7 records without using GEDCOM 5.x navigation.",
        "parameters": {"file_path": "GEDCOM 7 path.", "max_records": "Top-level record cap."},
    },
    "summarize_gedcomx_json": {
        "purpose": "Return top-level collection counts from GEDCOM X JSON.",
        "when_to_use": "Quick GEDCOM X JSON inventory without detailed object browsing.",
        "parameters": {"file_path": "GEDCOM X JSON path."},
    },
    "list_gedcomx_collections": {
        "purpose": "List GEDCOM X top-level collections and counts.",
        "when_to_use": "First GEDCOM X JSON browsing step after `load_gedcom`.",
        "parameters": {"file_path": "GEDCOM X JSON path."},
    },
    "list_gedcomx_objects": {
        "purpose": "List objects from a GEDCOM X collection.",
        "when_to_use": "Browse `persons`, `relationships`, `sourceDescriptions`, etc.",
        "parameters": {"file_path": "GEDCOM X JSON path.", "collection": "Collection name.", "query": "Optional summary substring.", "limit": "Max objects returned."},
    },
    "get_gedcomx_object": {
        "purpose": "Return GEDCOM X object by id.",
        "when_to_use": "Inspect a specific GEDCOM X object such as person `P1`.",
        "parameters": {"file_path": "GEDCOM X JSON path.", "object_id": "Object id without or with `#`.", "include_json": "Include serialized object JSON."},
    },
    "search_gedcomx_persons": {
        "purpose": "Search GEDCOM X persons by name/id/gender/fact summary.",
        "when_to_use": "Find a GEDCOM X person id before relationship inspection.",
        "parameters": {"file_path": "GEDCOM X JSON path.", "query": "Search string.", "limit": "Max people returned."},
    },
    "get_gedcomx_person_relationships": {
        "purpose": "Return GEDCOM X relationships that reference a person id.",
        "when_to_use": "Answer GEDCOM X relationship questions for person ids like `P1`.",
        "parameters": {"file_path": "GEDCOM X JSON path.", "person_id": "Person id.", "limit": "Max relationships returned."},
    },
    "resolve_gedcomx_reference": {
        "purpose": "Resolve a GEDCOM X resource/URI reference to an object.",
        "when_to_use": "Follow references like `#P1` or resource wrappers.",
        "parameters": {"file_path": "GEDCOM X JSON path.", "reference": "Reference string such as `#P1`."},
    },
    "get_gedcomx_schema_class": {
        "purpose": "Inspect GEDCOM X schema fields and class relationships.",
        "when_to_use": "Understand model fields before interpreting or constructing objects.",
        "parameters": {"class_name": "Optional class name such as `Person`; omit for top-level schema list."},
    },
    "search_gedcomx_schema": {
        "purpose": "Search GEDCOM X schema by field name or type expression.",
        "when_to_use": "Find which classes contain a field or reference a type.",
        "parameters": {"field_or_type": "Search text.", "mode": "`field` or type-search mode."},
    },
}


mcp = FastMCP(
    "gedcomtools",
    instructions=STARTUP_GUIDE,
)


@mcp.tool()
def man(tool_name: str | None = None) -> dict[str, Any]:
    """Return the startup guide and detailed manual entries for tools."""
    if tool_name:
        entry = TOOL_MANUAL.get(tool_name)
        if entry is None:
            return {
                "error": f"Unknown tool {tool_name!r}",
                "available_tools": sorted(TOOL_MANUAL),
                "guidance": "Call man() without a tool name for overview.",
            }
        return {
            "tool": tool_name,
            "manual": entry,
            "first_use_rule": "Consult this manual entry before calling the tool for the first time in a session.",
        }
    return {
        "server": "gedcomtools-mcp",
        "startup_guide": STARTUP_GUIDE,
        "first_use_rule": "Call man('tool_name') before using a tool for the first time in a session.",
        "recommended_first_calls": ["man", "load_gedcom", "list_individuals or list_gedcomx_collections"],
        "tools": {
            name: {
                "purpose": entry.get("purpose"),
                "when_to_use": entry.get("when_to_use"),
            }
            for name, entry in sorted(TOOL_MANUAL.items())
        },
    }


@mcp.tool()
def server_info() -> dict[str, Any]:
    """Return import and runtime information for this gedcomtools MCP server."""
    import gedcomtools

    return {
        "server": "gedcomtools-mcp",
        "gedcomtools_imported_from": getattr(gedcomtools, "__file__", None),
        "python": sys.version,
        "sys_path_prefix": sys.path[:5],
    }


@mcp.tool()
def summarize_gedcom5x(
    file_path: str,
    strict: bool = True,
    sample_limit: int = 10,
) -> dict[str, Any]:
    """Parse a GEDCOM 5.x file and return record counts plus a small sample."""
    parser = _load_gedcom5x(file_path, strict=strict)
    version = _detect_gedcom_version(file_path)
    return {
        "file_path": str(_ensure_input_file(file_path)),
        "format": _classify_gedcom_version(version),
        "gedcom_version": version,
        "strict": strict,
        "records": len(_all_records(parser)),
        "top_level_records": len(_top_level_records(parser)),
        "top_level_tag_counts": _top_level_tag_counts(parser),
        "individuals": len(parser.individuals),
        "families": len(parser.families),
        "sources": len(parser.sources),
        "repositories": len(parser.repositories),
        "objects": len(parser.objects),
        "submitters": len(parser.submitters),
        "sample_records": _sample_records(_all_records(parser), sample_limit),
    }


@mcp.tool()
def get_gedcom_version(file_path: str) -> dict[str, Any]:
    """Return the GEDCOM version declared in HEAD.GEDC.VERS for a .ged file."""
    version = _detect_gedcom_version(file_path)
    return {
        "file_path": str(_ensure_input_file(file_path)),
        "version": version,
        "format": _classify_gedcom_version(version),
    }


@mcp.tool()
def load_gedcom(
    file_path: str,
    strict: bool = True,
    sample_limit: int = 5,
    max_errors: int = 25,
) -> dict[str, Any]:
    """Detect and summarize a GEDCOM/GEDCOM X file, including declared GEDCOM version when available."""
    path = _ensure_input_file(file_path)
    suffix = path.suffix.casefold()
    if suffix == ".json":
        gx = _load_gedcomx_json(str(path))
        return {
            "file_path": str(path),
            "format": "GEDCOM X JSON",
            "gedcom_version": None,
            "gedcomx_version": getattr(gx, "version", None) if not isinstance(gx, dict) else "http://gedcomx.org/conceptual-model/v1",
            "counts": _gx_counts(gx),
            "collections": _gx_collection_names(gx) if not isinstance(gx, dict) else sorted(k for k, v in gx.items() if isinstance(v, list)),
        }

    version = _detect_gedcom_version(str(path))
    kind = _classify_gedcom_version(version)
    if kind == "GEDCOM 7":
        summary = validate_gedcom7(str(path), max_errors=max_errors)
        summary["format"] = kind
        summary["gedcom_version"] = version
        return summary

    summary = summarize_gedcom5x(str(path), strict=strict, sample_limit=sample_limit)
    summary["format"] = kind
    summary["gedcom_version"] = version
    return summary


@mcp.tool()
def list_individuals(
    file_path: str,
    query: str = "",
    limit: int = 50,
    strict: bool = True,
) -> dict[str, Any]:
    """List people in a GEDCOM 5.x file, optionally filtered by name, xref, or description."""
    parser = _load_gedcom5x(file_path, strict=strict)
    matches = [
        _individual_summary(parser, person, include_facts=False)
        for person in parser.individuals
        if _matches_individual(person, query)
    ]
    capped = matches[: max(0, limit)]
    return {
        "file_path": str(_ensure_input_file(file_path)),
        "query": query,
        "total_matches": len(matches),
        "returned": len(capped),
        "individuals": capped,
    }


@mcp.tool()
def get_individual(
    file_path: str,
    xref: str,
    strict: bool = True,
    include_facts: bool = True,
) -> dict[str, Any]:
    """Return a detailed GEDCOM 5.x individual profile by xref, such as @I1@."""
    parser = _load_gedcom5x(file_path, strict=strict)
    individual = _find_individual(parser, xref)
    return _individual_summary(parser, individual, include_facts=include_facts)


@mcp.tool()
def get_person_families(
    file_path: str,
    xref: str,
    strict: bool = True,
) -> dict[str, Any]:
    """Return the families where a person is a child and where they are a spouse/parent."""
    from gedcomtools.gedcom5.tags import GEDCOM_TAG_FAMILY_CHILD, GEDCOM_TAG_FAMILY_SPOUSE

    parser = _load_gedcom5x(file_path, strict=strict)
    individual = _find_individual(parser, xref)
    as_child = _families_for_individual(parser, individual, GEDCOM_TAG_FAMILY_CHILD)
    as_spouse = _families_for_individual(parser, individual, GEDCOM_TAG_FAMILY_SPOUSE)
    return {
        "person": _individual_summary(parser, individual, include_facts=False),
        "families_as_child": [_family_summary(parser, family) for family in as_child],
        "families_as_spouse": [_family_summary(parser, family) for family in as_spouse],
    }


@mcp.tool()
def get_parents(
    file_path: str,
    xref: str,
    strict: bool = True,
    natural_only: bool = False,
) -> dict[str, Any]:
    """Return the parents of an individual."""
    parser = _load_gedcom5x(file_path, strict=strict)
    individual = _find_individual(parser, xref)
    parents = _parents_for_individual(parser, individual, natural_only=natural_only)
    return {
        "person": _individual_summary(parser, individual, include_facts=False),
        "natural_only": natural_only,
        "parents": [_individual_summary(parser, parent, include_facts=False) for parent in parents],
    }


@mcp.tool()
def get_children(
    file_path: str,
    xref: str,
    strict: bool = True,
) -> dict[str, Any]:
    """Return children of an individual, grouped by family."""
    from gedcomtools.gedcom5.tags import GEDCOM_TAG_FAMILY_SPOUSE

    parser = _load_gedcom5x(file_path, strict=strict)
    individual = _find_individual(parser, xref)
    families = _families_for_individual(parser, individual, GEDCOM_TAG_FAMILY_SPOUSE)
    family_results = []
    seen: set[str] = set()
    all_children = []
    for family in families:
        children = _family_members(parser, family, "CHIL")
        for child in children:
            if child.xref not in seen:
                seen.add(child.xref)
                all_children.append(child)
        family_results.append(
            {
                "family_xref": family.xref,
                "children": [_individual_summary(parser, child, include_facts=False) for child in children],
            }
        )
    return {
        "person": _individual_summary(parser, individual, include_facts=False),
        "children": [_individual_summary(parser, child, include_facts=False) for child in all_children],
        "families": family_results,
    }


@mcp.tool()
def get_spouses(
    file_path: str,
    xref: str,
    strict: bool = True,
) -> dict[str, Any]:
    """Return spouses or co-parents for an individual, grouped by family."""
    from gedcomtools.gedcom5.tags import GEDCOM_TAG_FAMILY_SPOUSE

    parser = _load_gedcom5x(file_path, strict=strict)
    individual = _find_individual(parser, xref)
    families = _families_for_individual(parser, individual, GEDCOM_TAG_FAMILY_SPOUSE)
    spouse_results = []
    seen: set[str] = set()
    spouses = []
    for family in families:
        parents = _family_parents(parser, family)
        family_spouses = [person for person in parents if person.xref != individual.xref]
        for spouse in family_spouses:
            if spouse.xref not in seen:
                seen.add(spouse.xref)
                spouses.append(spouse)
        spouse_results.append(
            {
                "family_xref": family.xref,
                "spouses": [_individual_summary(parser, spouse, include_facts=False) for spouse in family_spouses],
                "marriages": [_event_summary(parser, child) for child in _child_records(family, "MARR")],
            }
        )
    return {
        "person": _individual_summary(parser, individual, include_facts=False),
        "spouses": [_individual_summary(parser, spouse, include_facts=False) for spouse in spouses],
        "families": spouse_results,
    }


@mcp.tool()
def get_siblings(
    file_path: str,
    xref: str,
    strict: bool = True,
) -> dict[str, Any]:
    """Return siblings for an individual based on shared child-family records."""
    from gedcomtools.gedcom5.tags import GEDCOM_TAG_FAMILY_CHILD

    parser = _load_gedcom5x(file_path, strict=strict)
    individual = _find_individual(parser, xref)
    families = _families_for_individual(parser, individual, GEDCOM_TAG_FAMILY_CHILD)
    seen: set[str] = set()
    siblings = []
    family_results = []
    for family in families:
        children = _family_members(parser, family, "CHIL")
        family_siblings = [child for child in children if child.xref != individual.xref]
        for sibling in family_siblings:
            if sibling.xref not in seen:
                seen.add(sibling.xref)
                siblings.append(sibling)
        family_results.append(
            {
                "family_xref": family.xref,
                "siblings": [_individual_summary(parser, sibling, include_facts=False) for sibling in family_siblings],
            }
        )
    return {
        "person": _individual_summary(parser, individual, include_facts=False),
        "siblings": [_individual_summary(parser, sibling, include_facts=False) for sibling in siblings],
        "families": family_results,
    }


@mcp.tool()
def get_ancestors(
    file_path: str,
    xref: str,
    strict: bool = True,
    natural_only: bool = False,
    limit: int = 200,
) -> dict[str, Any]:
    """Return ancestors of an individual using GEDCOM family-child links."""
    parser = _load_gedcom5x(file_path, strict=strict)
    individual = _find_individual(parser, xref)
    capped = _ancestor_list(parser, individual, natural_only=natural_only, limit=max(0, limit))
    return {
        "person": _individual_summary(parser, individual, include_facts=False),
        "natural_only": natural_only,
        "total_ancestors": len(capped),
        "returned": len(capped),
        "ancestors": [_individual_summary(parser, ancestor, include_facts=False) for ancestor in capped],
    }


@mcp.tool()
def get_descendants(
    file_path: str,
    xref: str,
    strict: bool = True,
    generations: int = 10,
) -> dict[str, Any]:
    """Return descendants of an individual, grouped by generation."""
    parser = _load_gedcom5x(file_path, strict=strict)
    root = _find_individual(parser, xref)
    generations = max(0, generations)
    seen = {root.xref}
    current = [root]
    result = []
    for generation in range(1, generations + 1):
        next_generation = []
        for person in current:
            children_result = get_children(file_path, person.xref, strict=strict)
            for child_data in children_result["children"]:
                child_xref = child_data["xref"]
                if child_xref not in seen:
                    seen.add(child_xref)
                    next_generation.append(_find_individual(parser, child_xref))
        if not next_generation:
            break
        result.append(
            {
                "generation": generation,
                "people": [_individual_summary(parser, person, include_facts=False) for person in next_generation],
            }
        )
        current = next_generation
    return {
        "person": _individual_summary(parser, root, include_facts=False),
        "generations": result,
    }


@mcp.tool()
def get_family(
    file_path: str,
    family_xref: str,
    strict: bool = True,
) -> dict[str, Any]:
    """Return a GEDCOM family record with spouses/parents, children, marriage events, notes, and sources."""
    parser = _load_gedcom5x(file_path, strict=strict)
    family = _find_element(parser, family_xref)
    if getattr(family, "tag", None) != "FAM":
        raise TypeError(f"{_normalize_xref(family_xref)} is a {family.tag} record, not a FAM record")
    return _family_summary(parser, family)


@mcp.tool()
def get_sources(
    file_path: str,
    xref: str | None = None,
    strict: bool = True,
    limit: int = 100,
) -> dict[str, Any]:
    """List source records, or return citations attached to a specific record xref."""
    parser = _load_gedcom5x(file_path, strict=strict)
    if xref:
        element = _find_element(parser, xref)
        return {
            "record": _record_summary(element),
            "citations": _sources_for_element(parser, element, recursive=True),
        }
    sources = [_source_record_summary(parser, source.xref) for source in parser.sources]
    capped = sources[: max(0, limit)]
    return {
        "total_sources": len(sources),
        "returned": len(capped),
        "sources": capped,
    }


@mcp.tool()
def get_record_tree(
    file_path: str,
    xref: str,
    strict: bool = True,
    max_depth: int = 4,
) -> dict[str, Any]:
    """Return the raw GEDCOM record tree for any xref, capped by depth."""
    parser = _load_gedcom5x(file_path, strict=strict)
    element = _find_element(parser, xref)
    return _record_tree(element, max_depth=max(0, max_depth))


@mcp.tool()
def find_relationship_path(
    file_path: str,
    from_xref: str,
    to_xref: str,
    strict: bool = True,
) -> dict[str, Any]:
    """Find a direct ancestor path from one individual to another, if one exists."""
    parser = _load_gedcom5x(file_path, strict=strict)
    descendant = _find_individual(parser, from_xref)
    ancestor = _find_individual(parser, to_xref)
    path = _path_to_ancestor(parser, descendant, ancestor)
    return {
        "from": _individual_summary(parser, descendant, include_facts=False),
        "to": _individual_summary(parser, ancestor, include_facts=False),
        "relationship": "ancestor" if path else None,
        "path": [_individual_summary(parser, person, include_facts=False) for person in (path or [])],
    }


@mcp.tool()
def convert_gedcom5x_to_gedcomx(
    file_path: str,
    output_path: str | None = None,
    strict: bool = True,
    overwrite: bool = False,
    include_json: bool = False,
) -> dict[str, Any]:
    """Convert GEDCOM 5.x into GEDCOM X JSON, optionally writing it to disk."""
    from gedcomtools.gedcomx.serialization import Serialization

    gedcomx, converter = _convert_gedcom5x(file_path, strict=strict)
    with _quiet_gedcomtools():
        serialized = Serialization.serialize(gedcomx)

    result: dict[str, Any] = {
        "file_path": str(_ensure_input_file(file_path)),
        "strict": strict,
        "counts": _gedcomx_counts(gedcomx),
        "unhandled_tags": converter.ignored_tags or {},
    }

    if output_path:
        out = _ensure_output_file(output_path, overwrite=overwrite)
        out.write_bytes(_dump_json_bytes(serialized))
        result["output_path"] = str(out)

    if include_json:
        result["gedcomx_json"] = serialized

    return result


@mcp.tool()
def export_arango_graph(
    file_path: str,
    output_dir: str,
    strict: bool = True,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Convert GEDCOM 5.x and export persons/relationships JSONL graph files."""
    from gedcomtools.graph import GedcomGraph

    gedcomx, converter = _convert_gedcom5x(file_path, strict=strict)
    with _quiet_gedcomtools():
        graph = GedcomGraph.from_gedcomx(gedcomx)

    out_dir = Path(output_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    nodes_path = out_dir / "persons.jsonl"
    edges_path = out_dir / "person_to_person.jsonl"
    existing = [path for path in (nodes_path, edges_path) if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(f"Output file exists: {existing[0]}")

    graph.to_jsonl(str(nodes_path), str(edges_path))

    return {
        "file_path": str(_ensure_input_file(file_path)),
        "output_dir": str(out_dir),
        "strict": strict,
        "written": {
            "persons": {"path": str(nodes_path)},
            "person_to_person": {"path": str(edges_path)},
        },
        "summary": graph.summary(),
        "unhandled_tags": converter.ignored_tags or {},
    }


@mcp.tool()
def validate_gedcom7(file_path: str, max_errors: int = 100) -> dict[str, Any]:
    """Parse and validate a GEDCOM 7 file."""
    from gedcomtools.gedcom7.gedcom7 import Gedcom7

    path = _ensure_input_file(file_path)
    with _quiet_gedcomtools():
        gedcom = Gedcom7(path)
        errors = gedcom.validate()
    return {
        "file_path": str(path),
        "version": gedcom.detect_gedcom_version(),
        "top_level_records": len(gedcom),
        "valid": len(errors) == 0,
        "error_count": len(errors),
        "errors": [asdict(error) for error in errors[: max(0, max_errors)]],
        "errors_truncated": len(errors) > max(0, max_errors),
    }


@mcp.tool()
def inspect_gedcom7(file_path: str, max_records: int = 20) -> dict[str, Any]:
    """Parse a GEDCOM 7 file and return a compact tree summary."""
    from gedcomtools.gedcom7.gedcom7 import Gedcom7

    path = _ensure_input_file(file_path)
    with _quiet_gedcomtools():
        gedcom = Gedcom7(path)
    records = [record.to_dict() for record in list(gedcom)[: max(0, max_records)]]
    return {
        "file_path": str(path),
        "version": gedcom.detect_gedcom_version(),
        "top_level_records": len(gedcom),
        "parse_errors": [asdict(error) for error in gedcom.errors],
        "records": records,
    }


@mcp.tool()
def summarize_gedcomx_json(file_path: str) -> dict[str, Any]:
    """Return top-level GEDCOM X JSON collection counts for an existing JSON file."""
    path = _ensure_input_file(file_path)
    data = orjson.loads(path.read_bytes())
    if not isinstance(data, dict):
        raise ValueError("GEDCOM X JSON root must be an object")

    collections = {
        key: len(value)
        for key, value in data.items()
        if isinstance(value, list)
    }
    scalar_keys = sorted(key for key, value in data.items() if not isinstance(value, list))
    return {
        "file_path": str(path),
        "format": "GEDCOM X JSON",
        "gedcomx_version": "http://gedcomx.org/conceptual-model/v1",
        "collections": collections,
        "scalar_keys": scalar_keys,
    }


@mcp.tool()
def list_gedcomx_collections(file_path: str) -> dict[str, Any]:
    """List GEDCOM X top-level collections and counts."""
    gx = _load_gedcomx_json(file_path)
    return {
        "file_path": str(_ensure_input_file(file_path)),
        "format": "GEDCOM X JSON",
        "gedcomx_version": getattr(gx, "version", None) if not isinstance(gx, dict) else "http://gedcomx.org/conceptual-model/v1",
        "collections": _gx_counts(gx),
    }


@mcp.tool()
def list_gedcomx_objects(
    file_path: str,
    collection: str,
    query: str = "",
    limit: int = 50,
) -> dict[str, Any]:
    """List objects from a GEDCOM X top-level collection, such as persons or relationships."""
    gx = _load_gedcomx_json(file_path)
    items = [item for item in _gx_collection_items(gx, collection) if _gx_matches(item, query)]
    capped = items[: max(0, limit)]
    return {
        "file_path": str(_ensure_input_file(file_path)),
        "collection": collection,
        "query": query,
        "total_matches": len(items),
        "returned": len(capped),
        "objects": [_gx_object_summary(gx, item) for item in capped],
    }


@mcp.tool()
def get_gedcomx_object(
    file_path: str,
    object_id: str,
    include_json: bool = False,
) -> dict[str, Any]:
    """Return a GEDCOM X object by id, with optional serialized JSON."""
    from gedcomtools.gedcomx.serialization import Serialization

    gx = _load_gedcomx_json(file_path)
    obj = _gx_find_by_id(gx, object_id)
    result = {
        "file_path": str(_ensure_input_file(file_path)),
        "object": _gx_object_summary(gx, obj),
    }
    if include_json:
        if isinstance(obj, dict):
            result["json"] = obj
        else:
            with _quiet_gedcomtools():
                result["json"] = Serialization.serialize(obj)
    return result


@mcp.tool()
def search_gedcomx_persons(
    file_path: str,
    query: str,
    limit: int = 25,
) -> dict[str, Any]:
    """Search GEDCOM X persons by id, name, gender, or fact summary."""
    return list_gedcomx_objects(file_path, "persons", query=query, limit=limit)


@mcp.tool()
def get_gedcomx_person_relationships(
    file_path: str,
    person_id: str,
    limit: int = 100,
) -> dict[str, Any]:
    """Return GEDCOM X relationships that reference a person id."""
    gx = _load_gedcomx_json(file_path)
    person = _gx_find_by_id(gx, person_id)
    normalized = person_id.strip().lstrip("#")
    matches = []
    for rel in _gx_collection_items(gx, "relationships"):
        if isinstance(rel, dict):
            refs = [rel.get("person1"), rel.get("person2")]
            ids = [_gx_ref_id(ref) for ref in refs]
        else:
            ids = [_gx_ref_id(getattr(rel, "person1", None)), _gx_ref_id(getattr(rel, "person2", None))]
            ids = [getattr(getattr(rel, attr, None), "id", None) or id_ for attr, id_ in zip(("person1", "person2"), ids)]
        if normalized in ids:
            matches.append(rel)
    capped = matches[: max(0, limit)]
    return {
        "person": _gx_object_summary(gx, person),
        "total_relationships": len(matches),
        "returned": len(capped),
        "relationships": [_gx_relationship_summary(gx, rel) for rel in capped],
    }


@mcp.tool()
def resolve_gedcomx_reference(file_path: str, reference: str) -> dict[str, Any]:
    """Resolve a GEDCOM X URI/resource reference such as #P1 to an object summary."""
    gx = _load_gedcomx_json(file_path)
    obj = _gx_find_by_id(gx, _gx_ref_id(reference) or reference)
    return {
        "reference": reference,
        "object": _gx_object_summary(gx, obj),
    }


@mcp.tool()
def get_gedcomx_schema_class(class_name: str | None = None) -> dict[str, Any]:
    """Return GEDCOM X schema fields for one class, or all top-level schema classes."""
    from gedcomtools.gedcomx.schemas import SCHEMA, type_repr

    if class_name:
        fields = SCHEMA.get_class_fields(class_name) or {}
        return {
            "class": class_name,
            "fields": {name: type_repr(type_) for name, type_ in sorted(fields.items())},
            "bases": SCHEMA._bases.get(class_name, []),
            "subclasses": sorted(SCHEMA._subclasses.get(class_name, set())),
        }
    return {
        "top_level": sorted(SCHEMA.get_toplevel().keys()),
        "class_count": len(SCHEMA.field_type_table),
    }


@mcp.tool()
def search_gedcomx_schema(
    field_or_type: str,
    mode: str = "field",
) -> dict[str, Any]:
    """Search GEDCOM X schema by field name or by type expression."""
    from gedcomtools.gedcomx.schemas import SCHEMA, type_repr

    needle = field_or_type.casefold()
    matches = []
    for cls_name, fields in sorted(SCHEMA.field_type_table.items()):
        for field_name, field_type in sorted(fields.items()):
            type_text = type_repr(field_type)
            haystack = field_name if mode == "field" else type_text
            if needle in haystack.casefold():
                matches.append({"class": cls_name, "field": field_name, "type": type_text})
    return {
        "mode": mode,
        "query": field_or_type,
        "matches": matches,
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
