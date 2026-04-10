#!/usr/bin/env python3
"""
Compare the live gedcom.io GEDCOM 7 term definitions against this project's
specification.py and g7interop.py.

Fetches all structure term YAMLs from GitHub (FamilySearch/GEDCOM.io),
caches them locally in --cache (default: .spec_cache/), then reports:

  1. Spec structure URIs missing from our g7interop.G7_TAG_TO_URI
  2. Per-structure substructure mismatches (missing, extra, or wrong cardinality)
  3. g7interop URIs that have no matching spec structure entry

Prefix notation used in output (per the GEDCOM 7 spec):
  g7:   = https://gedcom.io/terms/v7/
  xsd:  = http://www.w3.org/2001/XMLSchema#
  dcat: = http://www.w3.org/ns/dcat#

Usage:
    python check_g7spec.py [--cache DIR] [--no-cache] [--verbose]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required: pip install pyyaml  (or: .venv/bin/pip install pyyaml)")

# ---------------------------------------------------------------------------
# URI helpers
# ---------------------------------------------------------------------------
G7_URI_PREFIX = "https://gedcom.io/terms/v7/"

PREFIX_MAP: dict[str, str] = {
    "g7":   "https://gedcom.io/terms/v7/",
    "xsd":  "http://www.w3.org/2001/XMLSchema#",
    "dcat": "http://www.w3.org/ns/dcat#",
}


def shorten_uri(uri: str) -> str:
    for prefix, full in PREFIX_MAP.items():
        if uri.startswith(full):
            return f"{prefix}:{uri[len(full):]}"
    return uri


# ---------------------------------------------------------------------------
# Network helpers
# ---------------------------------------------------------------------------
GITHUB_API      = "https://api.github.com/repos/FamilySearch/GEDCOM.io/contents/_pages/tag-def/v7"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/FamilySearch/GEDCOM.io/main/_pages/tag-def/v7"
FETCH_DELAY     = 0.25  # seconds between requests


def _fetch(url: str, accept: str = "") -> str:
    headers = {"User-Agent": "gedcomtools-spec-checker/1.0"}
    if accept:
        headers["Accept"] = accept
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8")
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Fetch failed [{url}]: {exc}") from exc


def _list_term_names(cache_dir: Path) -> list[str]:
    cache_file = cache_dir / "_index.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    print("  Fetching term index from GitHub API …", flush=True)
    data = json.loads(_fetch(GITHUB_API, accept="application/vnd.github+json"))
    names = [e["name"].removesuffix(".md") for e in data if e["name"].endswith(".md")]
    names.sort()
    cache_file.write_text(json.dumps(names))
    return names


def _clean_yaml_body(raw: str) -> str:
    """Remove trailing YAML doc-end marker and closing fenced-block delimiter."""
    # Strip trailing whitespace, closing ```, and YAML document end (...)
    s = raw.strip()
    if s.endswith("```"):
        s = s[:-3].strip()
    if s.endswith("..."):
        s = s[:-3].strip()
    return s


def _extract_yaml_from_md(md: str) -> str:
    """Pull the YAML content out of a Jekyll .md file.

    The file has Jekyll frontmatter (--- … ...) followed by the term YAML
    inside a plain fenced ``` … ``` block (no language tag).
    """
    # Match a fenced block with or without language tag, non-greedy
    match = re.search(r"```(?:ya?ml)?\r?\n(.+?)```", md, re.DOTALL)
    if match:
        return _clean_yaml_body(match.group(1))
    # Fallback: strip Jekyll frontmatter by splitting on "---" twice
    # The content after the second "---" is the YAML body.
    parts = md.split("---", 2)
    return _clean_yaml_body(parts[2]) if len(parts) >= 3 else md


def _fetch_term_yaml(name: str, cache_dir: Path) -> str | None:
    cache_file = cache_dir / f"{name}.yaml"
    if cache_file.exists():
        return cache_file.read_text()
    try:
        md = _fetch(f"{GITHUB_RAW_BASE}/{name}.md")
    except RuntimeError as exc:
        print(f"    [warn] {name}: {exc}", file=sys.stderr)
        return None
    time.sleep(FETCH_DELAY)
    raw = _extract_yaml_from_md(md)
    cache_file.write_text(raw)
    return raw


def load_all_terms(cache_dir: Path, verbose: bool = False) -> dict[str, dict]:
    """Return {term_name: parsed_yaml_dict} for every term in the spec."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    names      = _list_term_names(cache_dir)
    uncached   = [n for n in names if not (cache_dir / f"{n}.yaml").exists()]

    if uncached:
        print(f"  Fetching {len(uncached)} uncached terms (may take a minute) …",
              flush=True)

    terms: dict[str, dict] = {}
    for i, name in enumerate(names, 1):
        raw = _fetch_term_yaml(name, cache_dir)
        if raw is None:
            if verbose:
                print(f"    [skip] {name}: fetch failed")
            continue
        # Apply cleaning in case the cache file was written with delimiters still present
        raw = _clean_yaml_body(raw)
        try:
            parsed = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            if verbose:
                print(f"    [skip] {name}: YAML error: {exc}")
            continue
        if isinstance(parsed, dict):
            terms[name] = parsed
        if uncached and i % 25 == 0:
            print(f"    … {i}/{len(names)}", flush=True)

    return terms


# ---------------------------------------------------------------------------
# Spec-side parsing
# ---------------------------------------------------------------------------
def _parse_card(s: str) -> tuple[int, int | None]:
    """'{0:M}' → (0, None);  '{1:1}' → (1, 1)."""
    m = re.match(r"\{(\d+):([0-9]+|M)\}", s.strip())
    if not m:
        return (0, None)
    return (int(m.group(1)), None if m.group(2) == "M" else int(m.group(2)))


def _card_str(card: tuple[int, int | None]) -> str:
    lo, hi = card
    return f"{{{lo}:{'M' if hi is None else hi}}}"


def build_spec_structures(terms: dict[str, dict]) -> dict[str, dict]:
    """Filter to structure-type terms and normalise into a flat dict.

    Returns:
        {term_name: {
            uri, standard_tag, payload,
            substructures:  {uri: (min, max)},
            superstructures: {uri: (min, max)},
        }}
    """
    out: dict[str, dict] = {}
    for name, term in terms.items():
        if term.get("type") != "structure":
            continue
        subs_raw   = term.get("substructures")   or {}
        supers_raw = term.get("superstructures") or {}
        out[name] = {
            "uri":          term.get("uri", G7_URI_PREFIX + name),
            "standard_tag": str(term.get("standard tag", "") or ""),
            "payload":      term.get("payload"),
            "substructures": {
                uri: _parse_card(str(card))
                for uri, card in subs_raw.items()
            },
            "superstructures": {
                uri: _parse_card(str(card))
                for uri, card in supers_raw.items()
            },
        }
    return out


# ---------------------------------------------------------------------------
# Local-spec loading
# ---------------------------------------------------------------------------
def load_local_spec() -> tuple:
    """Import specification.py and g7interop.py without requiring an install.

    specification.py uses relative imports so we must add the src tree to
    sys.path and import via the full package path.
    """
    src_root = Path(__file__).parent / "src"
    if str(src_root) not in sys.path:
        sys.path.insert(0, str(src_root))

    # Standard import now works because src/ is on the path.
    import importlib
    interop    = importlib.import_module("gedcomtools.gedcom7.g7interop")
    local_spec = importlib.import_module("gedcomtools.gedcom7.specification")
    return local_spec, interop


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------
def _std_tag_for_uri(uri: str, spec_structures: dict[str, dict]) -> str:
    """Return the standard tag for a substructure URI.

    Looks up in the spec first; falls back to stripping context prefixes
    (e.g. 'INDI-NAME' → 'NAME').
    """
    name = uri.replace(G7_URI_PREFIX, "")
    if name in spec_structures:
        return spec_structures[name]["standard_tag"].upper()
    # Strip leading context qualifier: INDI-NAME → NAME, FAM-CENS → CENS
    return re.sub(r"^[A-Z]+-", "", name).upper()


def compare(
    spec_structures: dict[str, dict],
    local_spec,
    interop,
    verbose: bool = False,
) -> list[str]:
    lines: list[str] = []

    # Reverse map: full URI → local tag key used in G7_TAG_TO_URI
    uri_to_local: dict[str, str] = {
        uri: tag for tag, uri in interop.G7_TAG_TO_URI.items()
    }
    all_spec_uris = {s["uri"] for s in spec_structures.values()}
    local_rules: dict = local_spec._CORE_RULES

    # ── 1. Spec structure URIs missing from g7interop ─────────────────────
    missing_uris = [
        (name, s["uri"], s["standard_tag"])
        for name, s in sorted(spec_structures.items())
        if s["uri"] not in uri_to_local
    ]
    lines.append("=" * 66)
    lines.append("1. SPEC STRUCTURE URIs MISSING FROM g7interop.G7_TAG_TO_URI")
    lines.append("=" * 66)
    if missing_uris:
        for name, uri, tag in missing_uris:
            lines.append(f"  {name:<30} tag={tag!r:<12} {shorten_uri(uri)}")
    else:
        lines.append("  All spec structure URIs are present ✓")

    # ── 2. Substructure / cardinality mismatches ──────────────────────────
    lines.append("")
    lines.append("=" * 66)
    lines.append("2. SUBSTRUCTURE MISMATCHES (per spec structure term)")
    lines.append("=" * 66)
    any_mismatch = False

    for name, s in sorted(spec_structures.items()):
        local_key = s["standard_tag"].upper()  # e.g. "INDI", "NAME", "BIRT"

        # Translate spec substructure URIs → {std_tag: card}
        spec_subs: dict[str, tuple] = {}
        for uri, card in s["substructures"].items():
            std = _std_tag_for_uri(uri, spec_structures)
            if std:
                spec_subs[std] = card   # last writer wins if collision

        local_entry = local_rules.get(local_key)
        if local_entry is None:
            # Not in _CORE_RULES at all
            if spec_subs and verbose:
                lines.append(
                    f"\n  [{name}] tag={local_key!r} absent from _CORE_RULES "
                    f"(spec lists {len(spec_subs)} subs)"
                )
                any_mismatch = True
            continue

        local_subs = {t.upper() for t in local_entry.get("substructures", {})}
        spec_tags  = set(spec_subs)

        entry_lines: list[str] = []

        for tag in sorted(spec_tags - local_subs):
            entry_lines.append(
                f"    MISSING locally : {tag:<10} spec={_card_str(spec_subs[tag])}"
            )

        for tag in sorted(local_subs - spec_tags):
            local_card = local_entry.get("cardinality", {}).get(
                tag, local_entry.get("cardinality", {}).get(tag.lower())
            )
            lc = _card_str(local_card) if local_card else "?"
            entry_lines.append(
                f"    EXTRA locally   : {tag:<10} local={lc}"
            )

        for tag in sorted(spec_tags & local_subs):
            spec_card  = spec_subs[tag]
            local_card = local_entry.get("cardinality", {}).get(tag)
            if local_card and local_card != spec_card:
                entry_lines.append(
                    f"    CARD MISMATCH   : {tag:<10} "
                    f"spec={_card_str(spec_card)}  local={_card_str(local_card)}"
                )

        if entry_lines:
            any_mismatch = True
            lines.append(f"\n  [{name}]  tag={local_key!r}")
            lines.extend(entry_lines)

    if not any_mismatch:
        lines.append("  No substructure mismatches found ✓")

    # ── 3. g7interop URIs with no matching spec structure ─────────────────
    lines.append("")
    lines.append("=" * 66)
    lines.append("3. g7interop URIs WITH NO MATCHING SPEC STRUCTURE TERM")
    lines.append("=" * 66)
    orphans = [
        (tag, uri)
        for tag, uri in sorted(interop.G7_TAG_TO_URI.items())
        if uri.startswith(G7_URI_PREFIX) and uri not in all_spec_uris
    ]
    if orphans:
        for tag, uri in orphans:
            lines.append(f"  {tag:<20} {shorten_uri(uri)}")
    else:
        lines.append("  All g7interop URIs match a spec structure term ✓")

    # ── Summary ───────────────────────────────────────────────────────────
    lines.append("")
    lines.append("=" * 66)
    lines.append(
        f"Spec structure terms  : {len(spec_structures)}\n"
        f"Missing from interop  : {len(missing_uris)}\n"
        f"Orphan interop URIs   : {len(orphans)}"
    )

    return lines


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--cache", default=".spec_cache",
        metavar="DIR",
        help="Directory to cache fetched term YAMLs (default: .spec_cache)",
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Delete existing cache and re-fetch everything",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Also report tags absent from _CORE_RULES",
    )
    args = parser.parse_args()

    cache_dir = Path(args.cache)
    if args.no_cache and cache_dir.exists():
        import shutil
        shutil.rmtree(cache_dir)

    print("Loading spec terms from gedcom.io / GitHub …", flush=True)
    terms = load_all_terms(cache_dir, verbose=args.verbose)
    print(f"  Loaded {len(terms)} terms total.")

    structures = build_spec_structures(terms)
    print(f"  Found {len(structures)} structure-type terms.")

    print("Loading local specification …", flush=True)
    local_spec, interop = load_local_spec()

    print("Comparing …\n", flush=True)
    report = compare(structures, local_spec, interop, verbose=args.verbose)
    print("\n".join(report))


if __name__ == "__main__":
    main()
