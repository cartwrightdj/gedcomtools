# Changes

## v0.7.5b2 - 2026-04-25

- Added typed FamilySearch deserialization support for `PersonInfo`,
  `NameFormInfo`, normalized dates, normalized place text, and the
  FamilySearch-specific `FamilyTree` source-description resource type.
- Expanded `FamilySearchPlatform` to deserialize `persons`,
  `relationships`, `places`, `links`, and `sourceDescriptions`.
- Added `FamilySearchPersonEnvelope` for the observed outer FamilySearch
  web payload wrapper containing `data`, `person`, `personId`, `summary`,
  `title`, and related top-level display fields.
- Updated `Person.display()` behavior to prefer typed deserialized
  FamilySearch display data and compute missing values from person facts.
- Added sample FamilySearch JSON fixtures under
  `.sample_data/familysearch/`.
- Added disk-based tests for the FamilySearch sample data and a commented
  example script in `examples/familysearch_deserialize.py`.
- Added symmetric custom deserialization hooks so `Serialization.deserialize()`
  now checks `_deserializer(data)` and `from_json(data, None)` before generic
  fallback construction.
- Hardened public URL-loading paths with a shared bounded-download helper that
  applies a timeout and response-size limit to remote fetches.
- Tightened repo-level `pyright` and `pylint` configuration so generated build
  output and docs do not hide real source diagnostics.
- Verified the new work with pytest, pylint, and pyright in the project
  virtual environment.
