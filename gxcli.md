# GEDCOM-X Inspector CLI — User Handbook

A friendly, practical guide to exploring GEDCOM‑X data from the command line. This manual explains how to **load**, **navigate**, **inspect**, and **interact** with your data using a shell-style interface.

---

## Table of Contents
- [1. What is it?](#1-what-is-it)
- [2. Requirements](#2-requirements)
- [3. Installation](#3-installation)
- [4. Launching the CLI](#4-launching-the-cli)
- [5. Core Concepts](#5-core-concepts)
- [6. Quick Start Walkthrough](#6-quick-start-walkthrough)
- [7. Commands (Detailed)](#7-commands-detailed)
  - [7.1 load / ld](#71-load--ld)
  - [7.2 ls](#72-ls)
  - [7.3 cd](#73-cd)
  - [7.4 pwd](#74-pwd)
  - [7.5 show](#75-show)
  - [7.6 type](#76-type)
  - [7.7 schema](#77-schema)
  - [7.8 extras](#78-extras)
  - [7.9 props](#79-props)
  - [7.10 methods](#710-methods)
  - [7.11 call](#711-call)
  - [7.12 getattr / getprop](#712-getattr--getprop)
  - [7.13 resolve](#713-resolve)
  - [7.14 write](#714-write)
  - [7.15 quit / exit](#715-quit--exit)
- [8. Paths & Navigation (Cheats)](#8-paths--navigation-cheats)
- [9. Working With Collections](#9-working-with-collections)
- [10. Examples](#10-examples)
- [11. Tips & Best Practices](#11-tips--best-practices)
- [12. Troubleshooting](#12-troubleshooting)
- [13. Command Cheat Sheet](#13-command-cheat-sheet)

---

## 1. What is it?
The GEDCOM‑X Inspector is an interactive REPL (read–eval–print loop) that lets you **browse** and **examine** GEDCOM‑X data. It is **schema‑aware**: it knows the expected types from your project’s `SCHEMA` and highlights mismatches. It also supports calling methods and reading properties on your model objects.

Typical uses:
- Inspect a tree converted from GEDCOM 5.x.
- Verify fields and data types.
- Resolve references.
- Explore model objects: see properties, list methods, and call them.

---

## 2. Requirements
- Python **3.10+** (3.11+ recommended)
- Your project modules available on `PYTHONPATH` (e.g., `gedcomx`, converters, schema, etc.)

**Optional but recommended**
- `orjson` (faster JSON I/O)
- `colorama` (Windows terminal colors)

---

## 3. Installation
Install optional packages (recommended):
```bash
pip install orjson colorama
```

Make sure your project imports resolve in Python (e.g., run from repo root or set `PYTHONPATH`).

---

## 4. Launching the CLI
Start empty:
```bash
python gxcli.py
```

Start and load a file immediately:
```bash
python gxcli.py path/to/tree.json      # GEDCOM-X JSON
python gxcli.py path/to/tree.ged       # GEDCOM 5.x (auto-converts to GEDCOM-X)
```

---

## 5. Core Concepts

**Prompt** shows current location:
```
gx:/persons/0/names>
```

**Paths** are filesystem‑like:
- `/` = root
- `.` = current
- `..` = parent
- numeric indices (e.g., `0`, `-1`) select items in collections
- Quote path segments with spaces: `cd "given name"`

**Collections**:
- Any `TypeCollection[T]`, `list`, `tuple`, or `set` is indexable.

**Schema awareness**:
- `ls` displays **runtime** vs **schema** types. Mismatches are shown in **red** (if colors available).
- Types are printed without long module prefixes: e.g., `TypeCollection[Person]`.

---

## 6. Quick Start Walkthrough

1) **Load data**
```text
ld data/tree.json
```

2) **List the current node**
```text
ls
```

3) **Navigate**
```text
cd persons
ls
cd 0
pwd
```

4) **Inspect a node**
```text
type
show
```

5) **Explore object features**
```text
props
methods
call fullName
```

6) **Resolve references (optional)**
```text
resolve
```

7) **Save to GEDCOM-X JSON**
```text
write gx out.json
```

---

## 7. Commands (Detailed)

### 7.1 load / ld
Load a file (GEDCOM‑X JSON or GEDCOM 5.x):
```text
load path/to/file.json
ld path/to/file.ged
```
- `.ged` files are parsed and converted to GEDCOM‑X.
- After loading, the root (`/`) is the loaded data.

### 7.2 ls
List fields/items under a node, showing **runtime** vs **schema** type and a brief **preview**:
```text
ls
ls /persons/0
```
Columns:
- **name**: field name or index
- **type**: runtime type
- **schema**: declared schema type
- **preview**: short summary (e.g., `<dict len=3>`, `<TypeCollection len=12>`)

### 7.3 cd
Change the current node:
```text
cd /persons
cd 0/names
cd ..
cd /
```
- You can chain indices and names: `cd persons/0/names/1`.
- If a segment has spaces, quote it: `cd "given name"`.

### 7.4 pwd
Print the current path:
```text
pwd
```

### 7.5 show
Pretty print the target node as JSON (non‑destructive):
```text
show
show /persons/0/names
```

### 7.6 type
Show the runtime type and inferred schema details for a node or field:
```text
type
type names
type /persons/0/names
type class Person --fields --mro
```
- `type class <ClassName>`: inspect schema class directly.
- `--fields`: list class fields.
- `--mro`: show Python method resolution order (advanced).

### 7.7 schema
Interrogate the schema registry:
```text
schema help
schema here
schema class Person
schema extras [ClassName] [--all|--direct]
schema find uri
schema where TypeCollection
schema bases Name
schema toplevel
schema json
schema diff /persons/0
```
- `schema here`: fields for the current node’s class.
- `schema class X`: fields for class `X`.
- `schema extras`: show extra (non‑core) fields (direct vs inherited).
- `schema find <field>`: which classes define this field.
- `schema where <TypeExpr>`: fields whose type string contains `<TypeExpr>`.
- `schema bases <ClassName>`: base classes and subclasses.
- `schema toplevel`: classes marked as top‑level.
- `schema json`: dump schema mapping as JSON.
- `schema diff [PATH]`: compare runtime vs schema for a node; highlights mismatches.

### 7.8 extras
List extras across all classes:
```text
extras --all
extras --direct
extras --filter Note
```

### 7.9 props
List `@property` values for the current object:
```text
props
props --private
props --match name
```
Columns:
- **scope**: `class` (declared on a class)
- **name**: property name
- **value**: computed value
- **defined in**: declaring class

### 7.10 methods
List callable methods on the current object:
```text
methods
methods --private
methods --own
methods --match fact
```
Columns:
- **name**: method name
- **signature**: parameters and (if known) return annotation
- **defined in**: declaring class
- **doc**: first line of the docstring (if any)

### 7.11 call
Call a method with typed arguments:
```text
call NAME [args...] [key=value ...]
```
- Positional and keyword arguments are auto‑typed using safe rules:
  - `true` → `True`, `false` → `False`, `none` → `None`
  - Numbers become `int`/`float` where possible
  - JSON‑like tokens (e.g., `{"a": 1}`) become dict/list
  - Other values remain strings
- Examples:
```text
call fullName
call addFact {"type": "http://gedcomx.org/Birth"} date="1901-01-01"
call age 1950
```

### 7.12 getattr / getprop
- `getattr NAME [...]`: report values and whether they’re **instance**, **class_attr**, **property**, or **missing**.
- `getprop NAME [...]`: print values of `@property` attributes (or explain if not a property).

Examples:
```text
getattr id lang
getprop displayName
```

### 7.13 resolve
Resolve `Resource`/`URI` references across the data and print resolver stats:
```text
resolve
```
Prints counts for total references, hits/misses, ok/fail, and timing.

### 7.14 write
Serialize the current root to GEDCOM‑X JSON:
```text
write gx out.json
```

### 7.15 quit / exit
Leave the REPL:
```text
quit
exit
```

---

## 8. Paths & Navigation (Cheats)

- Absolute path: `/persons/0/names/2`
- Relative path: `names/2`
- Parent: `..`
- Root: `/`
- Indexing into collections works with integers: `0`, `1`, `-1`

Examples:
```text
cd /persons
cd 0/names
cd ..
pwd
```

---

## 9. Working With Collections
The CLI treats `TypeCollection[T]`, `list`, `tuple`, and `set` as collections:
- `ls` displays their elements as indexed rows.
- `cd <index>` moves to a specific element.
- The **schema** column in `ls` displays the **element type** for collections.

Example:
```text
cd /persons/0/names
ls
cd 1
show
```

---

## 10. Examples

### Explore the first person’s names
```text
ld data/tree.json
cd /persons/0/names
ls
type
show
```

### Add a fact via a method call (example signature may vary)
```text
cd /persons/0
methods --match fact
call addFact {"type": "http://gedcomx.org/Birth"} date="1901-01-01"
```

### Find all classes with a field containing `uri`
```text
schema where uri
```

### Compare runtime vs schema for a specific node
```text
schema diff /persons/0
```

### Save the dataset
```text
write gx out.json
```

---

## 11. Tips & Best Practices

- **Quote arguments with spaces**: `cd "given name"`
- **Prefer `ls` before `cd`** to understand structure.
- **Use `type` to confirm** runtime type or check field types.
- **Use `methods` before `call`** to see the expected parameters.
- For Windows color support, install `colorama` and use a fresh terminal.
- If output looks truncated, resize your terminal or redirect to a file.

---

## 12. Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `cd` fails into a value | Target is not a container | Use `show` to view the value; use `cd` only on objects/collections |
| `ls` shows red **type** | Runtime type differs from schema | Verify conversion/import logic; check `schema diff` for details |
| `call` argument error | Argument types/arity mismatch | Check `methods` signature; pass `key=value` for keywords; strings with spaces must be quoted |
| No colors in Windows | Terminal lacks ANSI or `colorama` | `pip install colorama`, then reopen the terminal |
| `schema class X` says unknown | Class not registered in `SCHEMA` | Use `schema toplevel` or `schema json` to inspect available classes |
| `resolve` prints 0 refs | Root is not a GEDCOM‑X object or no refs | Ensure you loaded a proper GEDCOM‑X graph |

---

## 13. Command Cheat Sheet

### Basic
| Command | Description |
|---|---|
| `help` | Show help |
| `quit` / `exit` | Leave CLI |
| `pwd` | Print current path |
| `cd [PATH]` | Change current node |
| `ls [PATH]` | List fields/items |
| `show [PATH]` | Pretty print JSON |
| `type [...]` | Describe types |

### Files
| Command | Description |
|---|---|
| `load PATH` / `ld PATH` | Load GEDCOM‑X JSON or GEDCOM 5.x (converted) |
| `write gx PATH` | Save GEDCOM‑X JSON |

### Schema
| Command | Description |
|---|---|
| `schema here` | Show current class fields |
| `schema class <Name>` | Show specific class fields |
| `schema extras [--all|--direct]` | Show extras |
| `schema find <field>` | Which classes define this field |
| `schema where <TypeExpr>` | Fields whose type contains text |
| `schema bases <Class>` | Base/subclasses |
| `schema toplevel` | Top‑level classes |
| `schema json [Class]` | Dump schema mapping as JSON |
| `schema diff [PATH]` | Compare runtime vs schema |

### Introspection
| Command | Description |
|---|---|
| `props [--private] [--match s]` | List @property values |
| `methods [--private] [--own] [--match s]` | List callable methods |
| `call NAME [args] [k=v ...]` | Call method with typed args |
| `getattr NAME [...]` | Value + kind (instance/property/class_attr/missing) |
| `getprop NAME [...]` | Print @property values |

### Resolution
| Command | Description |
|---|---|
| `resolve` | Resolve references and print stats |

---

**End of Handbook**
