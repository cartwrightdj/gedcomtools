# gedcomtools CLI Manual

This guide starts with the shortest useful commands and gets more detailed as
it goes. Most users should start with `gedcomtools`.

## Quick Start

Show the available commands:

```bash
gedcomtools --help
```

Get a summary of a GEDCOM file:

```bash
gedcomtools info family.ged
```

Validate a file:

```bash
gedcomtools validate family.ged
```

List people:

```bash
gedcomtools list family.ged
```

Show one person or record:

```bash
gedcomtools show family.ged I1
gedcomtools show family.ged @I1@
```

Convert GEDCOM 5 or 7 to GEDCOM X JSON:

```bash
gedcomtools convert family.ged --to gx --out family.json
```

Use JSON output for scripting:

```bash
gedcomtools --json info family.ged
gedcomtools --json list family.ged indi
```

## Commands At A Glance

| Command | What it does |
|---|---|
| `info` | Show format, version, and record counts |
| `validate` | Validate GEDCOM 5.x or GEDCOM 7 |
| `list` | List records such as people, families, sources, repositories |
| `show` | Show details for one record by xref |
| `find` | Search the raw GEDCOM tree by tag and optional payload text |
| `tree` | Print an ancestry and descendant tree for one person |
| `stats` | Show simple completeness statistics |
| `convert` | Convert between supported formats |
| `repair` | Normalize common issues and write a repaired file |
| `export` | Export top-level entities to CSV or raw GEDCOM tree JSON |
| `diff` | Compare two GEDCOM files structurally |
| `merge` | Merge two GEDCOM files |
| `interactive` / `repl` | Open an interactive shell |
| `version` | Print the package version |
| `spec` | Forward GEDCOM 7 spec commands to `g7spec` |

The older `gctool` command is still available as a compatibility alias for the
same GEDCOM 5/7 command set.

## Input Formats

`gedcomtools` auto-detects common genealogy formats:

| Format | Typical extension | Notes |
|---|---|---|
| GEDCOM 5.x | `.ged`, `.gedcom` | Parsed by the GEDCOM 5 facade |
| GEDCOM 7 | `.ged`, `.gedcom`, `.gdz` | `.gdz` is treated as zipped GEDCOM 7 |
| GEDCOM X JSON | `.json`, `.gedcomx` | Used by the converter and `gxcli` |

The main `gedcomtools` inspection commands operate on GEDCOM 5.x and GEDCOM 7.
Use `gxcli` for browsing GEDCOM X JSON interactively.

## Basic Inspection

### File Info

```bash
gedcomtools info family.ged
```

Example use:

```bash
gedcomtools --json info family.ged
```

This is the fastest way to confirm whether the file loads and how many top-level
records it contains.

### Validation

```bash
gedcomtools validate family.ged
```

The command exits with a non-zero status if validation errors are found. That
makes it useful in scripts:

```bash
gedcomtools validate family.ged || echo "validation failed"
```

JSON validation output:

```bash
gedcomtools --json validate family.ged
```

### Listing Records

List individuals:

```bash
gedcomtools list family.ged
gedcomtools list family.ged indi
```

Other record types:

```bash
gedcomtools list family.ged fam
gedcomtools list family.ged sour
gedcomtools list family.ged repo
gedcomtools list family.ged obje
gedcomtools list family.ged subm
gedcomtools list family.ged snote
```

Record type names:

| Type | Meaning |
|---|---|
| `indi` | Individuals |
| `fam` | Families |
| `sour` | Sources |
| `repo` | Repositories |
| `obje` | Media objects |
| `subm` | Submitters |
| `snote` | Shared notes, GEDCOM 7 only |

### Showing One Record

Use the xref from `list`:

```bash
gedcomtools show family.ged @I1@
```

Bare xrefs are accepted too:

```bash
gedcomtools show family.ged I1
```

For scripts:

```bash
gedcomtools --json show family.ged I1
```

## Searching And Trees

### Find GEDCOM Tags

Search every node with a given tag:

```bash
gedcomtools find family.ged NAME
gedcomtools find family.ged DATE
gedcomtools find family.ged SOUR
```

Filter by payload text:

```bash
gedcomtools find family.ged NAME --payload Smith
gedcomtools find family.ged PLAC --payload Connecticut
```

JSON output includes all matches:

```bash
gedcomtools --json find family.ged NAME --payload Smith
```

### Print A Family Tree

```bash
gedcomtools tree family.ged I1
```

Limit generations in each direction:

```bash
gedcomtools tree family.ged I1 --depth 1
gedcomtools tree family.ged I1 --depth 5
```

### File Statistics

```bash
gedcomtools stats family.ged
gedcomtools --json stats family.ged
```

Statistics include counts for individuals, families, birth/death coverage, sex
counts, living count, and birth-year range when available.

## Conversion

The current preferred conversion form is:

```bash
gedcomtools convert SOURCE --to FORMAT --out DEST
```

Supported target formats:

| Target | Meaning |
|---|---|
| `gx` | GEDCOM X JSON |
| `g7` | GEDCOM 7 |
| `g5` | GEDCOM 5.x, only useful as a no-op/same-format target today |

Examples:

```bash
gedcomtools convert family.ged --to gx --out family.json
gedcomtools convert family.ged --to g7 --out family7.ged
```

Use `--out -` when you want the converted data on stdout:

```bash
gedcomtools convert family.ged --to gx --out - > family.gedcomx.json
gedcomtools convert family.ged --to g7 --out - > family7.ged
```

When stdout is used for the converted payload, progress messages are written
to stderr so pipes and redirects receive clean data.

Use `--quiet` to suppress status output, and `--compact` when JSON should be
single-line pipeline-friendly JSON:

```bash
gedcomtools convert family.ged --to gx --out - --quiet --compact > family.json
```

When converting GEDCOM 5.x to GEDCOM 7, decide how to handle known
vendor/non-standard tags:

```bash
gedcomtools convert family.ged --to g7 --out family7.ged --on-unknown drop
gedcomtools convert family.ged --to g7 --out family7.ged --on-unknown convert
```

`drop` discards those tags. `convert` emits them as GEDCOM 7 extension tags.

The older conversion syntax still works for existing scripts:

```bash
gedcomtools convert family.ged family.json -gx
gedcomtools convert family.ged family7.ged -g7
gedcomtools convert family.ged export/family -csv
```

New scripts should use the modern `--to` / `--out` form.

## Repair

Repair applies simple normalizations and writes a new file:

```bash
gedcomtools repair family.ged
gedcomtools repair family.ged --out family_repaired.ged
```

Preview without writing:

```bash
gedcomtools repair family.ged --dry-run
gedcomtools --json repair family.ged --dry-run
```

Current fixes include:

| Fix | Meaning |
|---|---|
| `trim_payload` | Remove leading/trailing whitespace from payloads |
| `norm_sex` | Normalize common sex values to GEDCOM values |
| `norm_date` | Normalize month abbreviations in dates |
| `strip_ctrl` | Remove control characters from payloads |

## Export

### Raw GEDCOM JSON

Raw JSON export preserves the GEDCOM record tree instead of normalizing it
into GEDCOM X. It works for both GEDCOM 5.x and GEDCOM 7 files:

```bash
gedcomtools export family.ged --to raw-json --out family.raw.json
gedcomtools export family7.ged --to raw-json --out family7.raw.json
```

`json` is accepted as an alias for `raw-json`:

```bash
gedcomtools export family.ged --to json --out family.raw.json
```

The output shape is intentionally simple:

```json
{
  "file": "family.ged",
  "format": "GEDCOM 5",
  "version": "5.5.1",
  "records": [
    {
      "level": 0,
      "xref": "@I1@",
      "tag": "INDI",
      "value": "",
      "pointer": false,
      "line": 8,
      "children": []
    }
  ]
}
```

GEDCOM 7 raw JSON nodes also include `uri` and `extension` fields when known.

Write raw JSON to stdout with `--out -` or by omitting `--out`:

```bash
gedcomtools export family.ged --to raw-json --out - | jq '.records[] | .tag'
```

Compact raw JSON is useful for agents and APIs:

```bash
gedcomtools export family.ged --to raw-json --out - --compact
```

### CSV Export

Export top-level GEDCOM entities to one CSV per entity type:

```bash
gedcomtools export family.ged --to csv --out export/family
```

This writes files such as:

```text
export/family_individuals.csv
export/family_families.csv
export/family_sources.csv
export/family_repositories.csv
export/family_media.csv
export/family_submitters.csv
export/family_shared_notes.csv
```

JSON output lists paths and row counts:

```bash
gedcomtools --json export family.ged --to csv --out export/family
```

CSV export can also write to stdout. Because CSV export normally creates
several files, stdout mode emits a JSON envelope whose values contain each CSV
document as a string:

```bash
gedcomtools export family.ged --to csv --out - > family-csvs.json
```

Use `--quiet` to suppress the file summary when writing CSVs to disk:

```bash
gedcomtools export family.ged --to csv --out export/family --quiet
```

## Diff And Merge

### Diff

Compare people and families in two GEDCOM files:

```bash
gedcomtools diff old.ged new.ged
gedcomtools --json diff old.ged new.ged
```

### Merge

Merge two GEDCOM files of the same detected format:

```bash
gedcomtools merge base.ged additions.ged --out merged.ged
```

Non-interactive mode keeps both possible duplicates by default:

```bash
gedcomtools merge base.ged additions.ged --out merged.ged --no-interactive
```

Interactive duplicate prompts can keep the file1 version, keep both, or choose
the file2 version where supported. When keeping the file1 version of a duplicate,
references from copied file2 records are remapped to the file1 survivor.

Merge is intentionally conservative. Always write to a new output file and
review the result.

## Interactive Shell

Open a shell with a file loaded:

```bash
gedcomtools interactive family.ged
gedcomtools repl family.ged
```

Or start empty and load later:

```bash
gedcomtools interactive
```

Common REPL commands:

```text
load FILE
info
validate
list [TYPE]
show XREF
find TAG [TEXT]
tree XREF [DEPTH]
stats
examine [XREF]
edit [XREF]
merge FILE2 [OUT]
diff FILE2
export [csv [OUT]]
repair [OUT]
help
exit
```

Use `examine` to browse the GEDCOM tree read-only. Use `edit` for in-memory
node edits:

```text
ls
cd NAME
cd 0
..
/
pwd
show
raw
set <value>
add <TAG> [value]
del
exit
```

The edit shell is best for inspection and experiments. Use conversion/write
workflows to persist durable output.

## GEDCOM 7 Helper Commands

### validate7

`validate7` is a focused GEDCOM 7 validator:

```bash
validate7 family7.ged
validate7 --lenient family7.ged
```

`--lenient` accepts undeclared extension tags without raising an error.

### g7cli

`g7cli` is an interactive GEDCOM 7 browser/editor:

```bash
g7cli
g7cli family7.ged
g7cli --help
```

Inside `g7cli`, use `help` or `?` for shell commands.

### g7spec

`g7spec` manages the bundled GEDCOM 7 structural rules:

```bash
g7spec info
g7spec export spec_rules.json
g7spec check --verbose
g7spec update --dry-run
```

Most users do not need `g7spec` unless they are validating GEDCOM 7 rule updates
or maintaining the parser.

## GEDCOM X Shell

`gxcli` is the interactive shell for GEDCOM X data:

```bash
gxcli
gxcli family.json
gxcli family.ged
gxcli --csv export/family family.json
```

It can load GEDCOM X JSON and can also convert GEDCOM files into an in-memory
GEDCOM X view. See `gxcli.md` for the full advanced shell manual.

## MCP Server

The MCP server is for agents and MCP-capable clients:

```bash
pip install "gedcomtools[mcp]"
gedcomtools-mcp
```

For Codex:

```bash
codex mcp add gedcomtools -- gedcomtools-mcp
```

For Claude Code:

```bash
claude mcp add gedcomtools -- gedcomtools-mcp
```

See `mcp.rst` and `mcp-agents.rst` for more MCP details.

## Practical Recipes

### Validate Then Convert

```bash
gedcomtools validate family.ged
gedcomtools convert family.ged --to gx --out family.json
```

### Produce CSVs For Spreadsheet Review

```bash
mkdir -p export
gedcomtools export family.ged --to csv --out export/family
```

### Find Every Source Citation

```bash
gedcomtools find family.ged SOUR
gedcomtools --json find family.ged SOUR > sources.json
```

### Inspect A Person And Their Local Tree

```bash
gedcomtools show family.ged I1
gedcomtools tree family.ged I1 --depth 2
```

### Compare Two Versions Of A File

```bash
gedcomtools diff family-old.ged family-new.ged
gedcomtools --json diff family-old.ged family-new.ged > diff.json
```

### Merge Two Files Safely

```bash
gedcomtools merge family.ged additions.ged --out family-merged.ged
gedcomtools validate family-merged.ged
```

## Exit Codes And Scripting

Most commands return `0` for success and non-zero for errors. `validate` returns
non-zero when validation errors are present.

Simple shell pattern:

```bash
if gedcomtools validate family.ged; then
  gedcomtools convert family.ged --to gx --out family.json
else
  echo "Fix validation errors before converting"
fi
```

JSON output is available for most `gedcomtools` inspection commands:

```bash
gedcomtools --json info family.ged
gedcomtools --json list family.ged indi
gedcomtools --json show family.ged I1
gedcomtools --json validate family.ged
gedcomtools --json stats family.ged
gedcomtools --json diff old.ged new.ged
```

## Troubleshooting

### `gedcomtools` is not found

Install the package or run from the source tree:

```bash
pip install -e .
```

From a source checkout without installing:

```bash
PYTHONPATH=src python3 -m gedcomtools.cli --help
```

### A GEDCOM X file is refused by `info` or `list`

The main `gedcomtools` inspection commands operate on GEDCOM 5.x and GEDCOM 7.
Use `gxcli` for GEDCOM X JSON:

```bash
gxcli family.json
```

### Conversion output is noisy

Some conversions print warnings about unhandled tags. Those warnings are useful
when checking conversion completeness. Redirect output if you only need the file:

```bash
gedcomtools convert family.ged --to gx --out family.json > convert.log
```

### I need the old CLI syntax

It is still supported:

```bash
gedcomtools convert family.ged family.json -gx
gedcomtools convert family.ged family7.ged -g7
```
