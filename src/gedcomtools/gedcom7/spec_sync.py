#!/usr/bin/env python3
"""
======================================================================
 Project: gedcomtools
 File:    gedcom7/spec_sync.py
 Purpose: Fetch live GEDCOM 7 spec terms and compare / apply updates.

 Created: 2026-03-22
======================================================================

Internal library used by ``g7spec check`` and ``g7spec update``.
Also imported by the standalone ``check_g7spec.py`` project-root script.

Network access is required only when term YAMLs are not cached locally.
The default cache directory is a ``.spec_cache/`` folder next to the
``spec_rules.json`` data file.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

G7_URI_PREFIX   = "https://gedcom.io/terms/v7/"
GITHUB_API      = (
    "https://api.github.com/repos/FamilySearch/GEDCOM.io"
    "/contents/_pages/tag-def/v7"
)
GITHUB_RAW_BASE = (
    "https://raw.githubusercontent.com"
    "/FamilySearch/GEDCOM.io/main/_pages/tag-def/v7"
)
FETCH_DELAY = 0.20  # seconds between requests

_DEFAULT_CACHE = Path(__file__).parent / ".spec_cache"

# ---------------------------------------------------------------------------
# Network helpers
# ---------------------------------------------------------------------------

def _fetch(url: str, accept: str = "") -> str:
    headers = {"User-Agent": "gedcomtools-spec-sync/1.0"}
    if accept:
        headers["Accept"] = accept
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8")
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Fetch failed [{url}]: {exc}") from exc


def _list_term_names(cache_dir: Path) -> List[str]:
    cache_file = cache_dir / "_index.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    data = json.loads(_fetch(GITHUB_API, accept="application/vnd.github+json"))
    names = sorted(e["name"].removesuffix(".md") for e in data if e["name"].endswith(".md"))
    cache_file.write_text(json.dumps(names))
    return names


def _extract_yaml_from_md(md: str) -> str:
    match = re.search(r"```(?:ya?ml)?\r?\n(.+?)```", md, re.DOTALL)
    if match:
        body = match.group(1)
    else:
        parts = md.split("---", 2)
        body = parts[2] if len(parts) >= 3 else md
    body = body.strip()
    if body.endswith("```"):
        body = body[:-3].strip()
    if body.endswith("..."):
        body = body[:-3].strip()
    return body


def _fetch_term_yaml(name: str, cache_dir: Path) -> Optional[str]:
    cache_file = cache_dir / f"{name}.yaml"
    if cache_file.exists():
        return cache_file.read_text()
    try:
        md = _fetch(f"{GITHUB_RAW_BASE}/{name}.md")
    except RuntimeError:
        return None
    time.sleep(FETCH_DELAY)
    raw = _extract_yaml_from_md(md)
    cache_file.write_text(raw)
    return raw


def load_all_terms(
    cache_dir: Optional[Path] = None,
    *,
    no_cache: bool = False,
    progress: bool = True,
) -> Dict[str, dict]:
    """Return ``{term_name: parsed_yaml_dict}`` for every GEDCOM 7 term.

    Parameters
    ----------
    cache_dir:
        Directory for caching fetched YAMLs.  Defaults to a ``.spec_cache``
        folder alongside the package's ``spec_rules.json``.
    no_cache:
        Wipe ``cache_dir`` and re-fetch everything.
    progress:
        Print progress dots to stdout.
    """
    try:
        import yaml  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "PyYAML is required for spec sync.  "
            "Install it with:  pip install pyyaml"
        ) from exc

    if cache_dir is None:
        cache_dir = _DEFAULT_CACHE
    if no_cache and cache_dir.exists():
        import shutil
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    names    = _list_term_names(cache_dir)
    uncached = [n for n in names if not (cache_dir / f"{n}.yaml").exists()]
    if uncached and progress:
        print(f"  Fetching {len(uncached)} uncached term(s) …", flush=True)

    terms: Dict[str, dict] = {}
    for i, name in enumerate(names, 1):
        raw = _fetch_term_yaml(name, cache_dir)
        if raw is None:
            continue
        raw = raw.strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()
        if raw.endswith("..."):
            raw = raw[:-3].strip()
        try:
            parsed = yaml.safe_load(raw)
        except yaml.YAMLError:
            continue
        if isinstance(parsed, dict):
            terms[name] = parsed
        if progress and uncached and i % 25 == 0:
            print(f"    … {i}/{len(names)}", flush=True)

    return terms


# ---------------------------------------------------------------------------
# Spec-side parsing
# ---------------------------------------------------------------------------

def _parse_card(s: str) -> Tuple[int, Optional[int]]:
    m = re.match(r"\{(\d+):([0-9]+|M)\}", str(s).strip())
    if not m:
        return (0, None)
    return (int(m.group(1)), None if m.group(2) == "M" else int(m.group(2)))


def _card_str(card: Tuple[int, Optional[int]]) -> str:
    lo, hi = card
    return f"{{{lo}:{'M' if hi is None else hi}}}"


def _std_tag_for_uri(uri: str, spec_structures: Dict[str, dict]) -> str:
    name = uri.replace(G7_URI_PREFIX, "")
    if name in spec_structures:
        return spec_structures[name]["standard_tag"].upper()
    return re.sub(r"^[A-Z]+-", "", name).upper()


def build_spec_structures(terms: Dict[str, dict]) -> Dict[str, dict]:
    """Filter to structure-type terms, normalise into a flat dict.

    Returns ``{term_name: {uri, standard_tag, payload, substructures, superstructures}}``.
    """
    out: Dict[str, dict] = {}
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
# Comparison
# ---------------------------------------------------------------------------

def compare(
    spec_structures: Dict[str, dict],
    local_rules: Dict[str, Any],
    verbose: bool = False,
) -> List[str]:
    """Compare live spec against *local_rules* (i.e. ``_CORE_RULES``).

    Returns a list of human-readable report lines.
    """
    lines: List[str] = []
    all_spec_uris = {s["uri"] for s in spec_structures.values()}

    # ── 1. Missing / extra structure terms ──────────────────────────────
    spec_tags  = {s["standard_tag"].upper() for s in spec_structures.values() if s["standard_tag"]}
    local_tags = set(local_rules)

    lines += ["=" * 66,
              "1. TAGS PRESENT IN SPEC BUT ABSENT FROM _CORE_RULES",
              "=" * 66]
    missing = sorted(spec_tags - local_tags)
    if missing:
        for t in missing:
            lines.append(f"  {t}")
    else:
        lines.append("  (none) ✓")

    lines += ["", "=" * 66,
              "2. SUBSTRUCTURE / CARDINALITY MISMATCHES",
              "=" * 66]
    any_mismatch = False
    for name, s in sorted(spec_structures.items()):
        local_key = s["standard_tag"].upper()
        spec_subs: Dict[str, tuple] = {}
        for uri, card in s["substructures"].items():
            std = _std_tag_for_uri(uri, spec_structures)
            if std:
                spec_subs[std] = card

        local_entry = local_rules.get(local_key)
        if local_entry is None:
            if spec_subs and verbose:
                lines.append(
                    f"\n  [{name}] tag={local_key!r} absent from _CORE_RULES "
                    f"(spec lists {len(spec_subs)} subs)"
                )
                any_mismatch = True
            continue

        local_subs = {t.upper() for t in local_entry.get("substructures", {})}
        spec_tags_set = set(spec_subs)
        entry_lines: List[str] = []

        for tag in sorted(spec_tags_set - local_subs):
            entry_lines.append(
                f"    MISSING locally : {tag:<10} spec={_card_str(spec_subs[tag])}"
            )
        if verbose:
            for tag in sorted(local_subs - spec_tags_set):
                local_card = local_entry.get("cardinality", {}).get(tag)
                lc = _card_str(local_card) if local_card else "?"
                entry_lines.append(f"    EXTRA locally   : {tag:<10} local={lc}")
        for tag in sorted(spec_tags_set & local_subs):
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

    lines.append(f"\nSpec structure terms: {len(spec_structures)}")
    return lines


# ---------------------------------------------------------------------------
# Update (apply spec → _CORE_RULES)
# ---------------------------------------------------------------------------

def apply_updates(
    spec_structures: Dict[str, dict],
    local_rules: Dict[str, Any],
) -> Tuple[int, int]:
    """Patch *local_rules* in-place with additions and cardinality corrections.

    Conservative — only **adds** missing substructures and **fixes**
    cardinality mismatches.  Extra locally-defined substructures are kept.

    Returns ``(added, updated)`` counts.
    """
    added = updated = 0
    for s in spec_structures.values():
        local_key = s["standard_tag"].upper()
        if not local_key or local_key not in local_rules:
            continue

        local_entry = local_rules[local_key]
        if "substructures" not in local_entry:
            local_entry["substructures"] = {}
        if "cardinality" not in local_entry:
            local_entry["cardinality"] = {}

        for uri, spec_card in s["substructures"].items():
            tag = _std_tag_for_uri(uri, spec_structures)
            if not tag:
                continue
            upper = tag.upper()
            if upper not in local_entry["substructures"]:
                # Find what payload type the sub-tag has
                sub_payload = None
                sub_name = uri.replace(G7_URI_PREFIX, "")
                if sub_name in spec_structures:
                    sub_payload = spec_structures[sub_name].get("payload")
                local_entry["substructures"][upper] = sub_payload or "Y"
                local_entry["cardinality"][upper]   = spec_card
                added += 1
            else:
                existing_card = local_entry["cardinality"].get(upper)
                if existing_card and existing_card != spec_card:
                    local_entry["cardinality"][upper] = spec_card
                    updated += 1
    return added, updated
