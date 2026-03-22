# Code Review TODO

Reviewed on 2026-03-21.

What I verified during review:
- `pytest -q` -> 878 passed, 9 xfailed, 1 warning
- `python3 -m build --sdist --wheel` -> succeeded

## Highest Priority

- [ ] Fix GEDCOM X relationship cross-reference validation for `Resource` references.
  Evidence: [`src/gedcomtools/gedcomx/gedcomx.py:489`](/home/a33/Projects/gedcomtools/src/gedcomtools/gedcomx/gedcomx.py#L489) only checks `pfield.id` and `pfield.resourceId`, but `Resource(resource=URI(fragment='P2'))` stores the id in `resource.fragment`.
  Impact: missing `person1` / `person2` targets can pass validation silently.
  Repro confirmed locally: a relationship pointing at `#P2` validated with no errors even when `P2` was absent.
  Do next: extract ids from `Resource.resource.fragment` as well, then add a regression test in the GedcomX validation suite.

- [ ] Make `GedcomX.from_dict()` lossless for root-level fields.
  Evidence: [`src/gedcomtools/gedcomx/gedcomx.py:579`](/home/a33/Projects/gedcomtools/src/gedcomtools/gedcomx/gedcomx.py#L579) restores `id` and `description`, but drops serialized `attribution` and `groups`.
  Impact: `Serialization.deserialize(..., GedcomX)` can silently lose data during round-trip.
  Repro confirmed locally: `attribution` serialized, then came back as `None`; serialized `groups` also came back empty.
  Do next: deserialize every field emitted by [`GedcomX._serializer`](/home/a33/Projects/gedcomtools/src/gedcomtools/gedcomx/gedcomx.py#L545), then add explicit round-trip tests for root attribution and groups.

- [ ] Harden CLI source sniffing so valid JSON and GEDCOM 7 files are not misclassified.
  Evidence: [`src/gedcomtools/cli.py:41`](/home/a33/Projects/gedcomtools/src/gedcomtools/cli.py#L41) treats JSON as GedcomX only if the very first byte is `{`, and reads GEDCOM text only as `utf-8-sig`.
  Impact: pretty-printed JSON, BOM-prefixed JSON, and UTF-16 GEDCOM 7 inputs can be rejected or downgraded to `g5`.
  Repro confirmed locally:
  `leading_space.json`, `newline.json`, and BOM-prefixed JSON all raised `ValueError`.
  A UTF-16 GEDCOM 7 sample was detected as `g5`.
  Do next: skip leading whitespace/BOM for JSON, and use more robust GEDCOM sniffing that can survive non-UTF-8 encodings.

## Medium Priority

- [ ] Stop `Serialization.serialize(dict)` from leaking `None` placeholders into output.
  Evidence: [`src/gedcomtools/gedcomx/serialization.py:121`](/home/a33/Projects/gedcomtools/src/gedcomtools/gedcomx/serialization.py#L121) keeps keys even when the serialized value became `None`.
  Impact: empty lists and absent nested values become `"key": null` instead of being pruned, which makes output noisier and can break assumptions about omitted-empty fields.
  Repro confirmed locally: `Serialization.serialize({'a': Attribution(...), 'b': None, 'c': []})` returned `{'a': {...}, 'b': None, 'c': None}`.
  Do next: filter out `None` values after recursive dict serialization and add coverage for dicts containing empty lists / nested empty models.

- [ ] Make `GedcomZip` resource naming collision-safe.
  Evidence: [`src/gedcomtools/gedcomx/zip.py:127`](/home/a33/Projects/gedcomtools/src/gedcomtools/gedcomx/zip.py#L127) always writes `GedcomX` objects as `tree.json`.
  Impact: adding multiple GEDCOM X resources produces duplicate zip entries and currently emits the warning seen in the test run.
  Repro confirmed by the existing test warning in `tests/test_zip.py`.
  Do next: decide on overwrite vs unique names vs manifest-backed naming, then update tests so duplicate entries are either prevented or explicitly intentional.

- [ ] Tighten root-object round-trip coverage around `Serialization.deserialize(..., GedcomX)`.
  Evidence: [`src/gedcomtools/gedcomx/serialization.py:371`](/home/a33/Projects/gedcomtools/src/gedcomtools/gedcomx/serialization.py#L371) delegates GedcomX deserialization to `from_dict()`, so any omission there bypasses model-level validation and can escape current tests.
  Impact: regressions in root metadata are easy to miss even with a large suite.
  Do next: add tests that assert full root preservation for `id`, `description`, `attribution`, `groups`, and mixed top-level collections.

## Cleanup And Maintainability

- [ ] Rationalize the extension/plugin story and remove dead-looking legacy paths.
  Evidence: the repo mixes the new Pydantic model system with legacy extension machinery, and [`src/gedcomtools/gedcomx/extensions/module/mod12.7.2025.py`](/home/a33/Projects/gedcomtools/src/gedcomtools/gedcomx/extensions/module/mod12.7.2025.py) uses a filename that is awkward to import as a normal Python module.
  Impact: extension loading becomes fragile and hard to reason about for users and future contributors.
  Do next: define one supported plugin registration path, move oddly named modules to import-safe filenames, and add a small integration test for plugin discovery/import.

- [ ] Re-enable automated static checks in CI.
  Evidence: the worktree currently shows `.github/workflows/pylint.yml` deleted, and the current review found issues the test suite does not cover.
  Impact: serialization and validation regressions can land even when tests stay green.
  Do next: restore or replace the lint workflow with a minimal CI pass for tests plus one static checker (`ruff`, `pylint`, or `pyright`).
