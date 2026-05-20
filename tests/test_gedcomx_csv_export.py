"""Tests for GedcomX CSV export helpers and gxcli integration."""
from __future__ import annotations

import csv
import json

from gedcomtools.gedcomx.csv_export import export_gedcomx_csv
from gedcomtools.gedcomx.fact import Fact, FactType
from gedcomtools.gedcomx.gedcomx import GedcomX
from gedcomtools.gedcomx.gxcli import Shell, main as gxcli_main
from gedcomtools.gedcomx.person import QuickPerson
from gedcomtools.gedcomx.relationship import Relationship, RelationshipType


def _make_gx() -> GedcomX:
    gx = GedcomX()
    parent = QuickPerson("Alex Parent", dob="1970")
    child = QuickPerson("Casey Child", dob="2000")
    child.add_fact(Fact(type=FactType.Occupation, value="Archivist"))
    gx.add_person(parent)
    gx.add_person(child)
    gx.add_relationship(Relationship(type=RelationshipType.ParentChild, person1=parent, person2=child))
    return gx


def _read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.reader(fh))


def test_export_gedcomx_csv_writes_top_level_collections(tmp_path):
    outputs = export_gedcomx_csv(_make_gx(), tmp_path / "family")

    assert set(outputs) == {
        "persons", "relationships", "source_descriptions", "agents",
        "events", "documents", "places", "groups",
    }
    persons_csv = tmp_path / "family_persons.csv"
    relationships_csv = tmp_path / "family_relationships.csv"
    assert persons_csv.exists()
    assert relationships_csv.exists()

    persons_rows = _read_csv(persons_csv)
    assert persons_rows[0][:4] == ["id", "name", "gender", "living"]
    assert any(row[1] == "Casey Child" and "Occupation" in row[9] for row in persons_rows[1:])

    relationship_rows = _read_csv(relationships_csv)
    assert relationship_rows[0][:4] == ["id", "type", "person1", "person2"]
    assert relationship_rows[1][1] == "ParentChild"


def test_gxcli_write_csv_command(tmp_path):
    shell = Shell(_make_gx())
    shell.gedcomx = shell.root

    shell._cmd_write(["csv", str(tmp_path / "cli_family")])

    assert (tmp_path / "cli_family_persons.csv").exists()
    assert (tmp_path / "cli_family_relationships.csv").exists()


def test_gxcli_csv_option_exports_and_exits(tmp_path):
    gx_path = tmp_path / "tree.json"
    gx_path.write_text(json.dumps(_make_gx()._to_dict()), encoding="utf-8")

    rc = gxcli_main([str(gx_path), "--csv", str(tmp_path / "option_family")])

    assert rc == 0
    assert (tmp_path / "option_family_persons.csv").exists()
    assert (tmp_path / "option_family_relationships.csv").exists()
