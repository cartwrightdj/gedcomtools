"""
======================================================================
 Project: gedcomtools
 File:    gedcom5/specification5.py
 Purpose: Structural rules for GEDCOM 5.5.1.

 Created: 2026-03-22
======================================================================

Defines the allowed substructures, cardinalities, payload types, and
pointer targets for GEDCOM 5.5.1 tag/context combinations.

Rule structure
--------------
Each entry in ``_RULES`` is keyed by a *context key* — either a bare
tag (used when that tag appears as a child node) or a ``TAG_RECORD``
key (used when the tag is a top-level xref-bearing record at level 0).

Entry dict fields
~~~~~~~~~~~~~~~~~
substructures   set[str]                Allowed child tag names.
cardinality     dict[str, (int,int|N)]  (min, max) per child tag;
                                        None max means unlimited.
payload_type    str                     "text" | "pointer" | "none" |
                                        "date" | "age" | "sex" |
                                        "lang" | "name" | "any"
pointer_target  set[str] | None         Allowed target record tag(s)
                                        for pointer payloads.
required_at_root bool                   True if the record must appear
                                        in every valid file.
"""

from __future__ import annotations

from typing import Any, Dict, FrozenSet, Optional, Set, Tuple

# Cardinality shorthand
_M = None  # unbounded

# ---------------------------------------------------------------------------
# Shared sub-rule fragments (composed into record/inline rules below)
# ---------------------------------------------------------------------------

# Substructures common to every individual or family event detail
_EVENT_DETAIL_SUBS: Set[str] = {
    "TYPE", "DATE", "PLAC", "ADDR", "PHON",
    "AGE", "AGNC", "CAUS", "SOUR", "OBJE", "NOTE", "RESN",
}
_EVENT_DETAIL_CARD: Dict[str, Tuple[int, Optional[int]]] = {
    "TYPE": (0, 1), "DATE": (0, 1), "PLAC": (0, 1), "ADDR": (0, 1),
    "PHON": (0, 3), "AGE": (0, 1), "AGNC": (0, 1), "CAUS": (0, 1),
    "SOUR": (0, _M), "OBJE": (0, _M), "NOTE": (0, _M), "RESN": (0, 1),
}

# LDS ordinance detail (BAPL, CONL, ENDL)
_LDS_ORD_SUBS: Set[str] = {"DATE", "TEMP", "PLAC", "STAT", "SOUR", "NOTE"}
_LDS_ORD_CARD: Dict[str, Tuple[int, Optional[int]]] = {
    "DATE": (0, 1), "TEMP": (0, 1), "PLAC": (0, 1), "STAT": (0, 1),
    "SOUR": (0, _M), "NOTE": (0, _M),
}

# Common trailer fields shared by most records
_RECORD_TRAIL_SUBS: Set[str] = {"REFN", "RIN", "CHAN", "NOTE", "SOUR"}
_RECORD_TRAIL_CARD: Dict[str, Tuple[int, Optional[int]]] = {
    "REFN": (0, _M), "RIN": (0, 1), "CHAN": (0, 1),
    "NOTE": (0, _M), "SOUR": (0, _M),
}

# ---------------------------------------------------------------------------
# Main rule table
# ---------------------------------------------------------------------------

_RULES: Dict[str, Dict[str, Any]] = {

    # ── Top-level records ────────────────────────────────────────────────

    "HEAD": {
        "payload_type": "none",
        "substructures": {
            "SOUR", "DEST", "DATE", "SUBM", "SUBN",
            "FILE", "COPR", "GEDC", "CHAR", "LANG", "PLAC", "NOTE",
        },
        "cardinality": {
            "SOUR": (1, 1), "DEST": (0, 1), "DATE": (0, 1),
            "SUBM": (1, 1), "SUBN": (0, 1), "FILE": (0, 1),
            "COPR": (0, 1), "GEDC": (1, 1), "CHAR": (1, 1),
            "LANG": (0, 1), "PLAC": (0, 1), "NOTE": (0, 1),
        },
    },

    "INDI_RECORD": {
        "payload_type": "none",
        "substructures": {
            "RESN",
            # names
            "NAME",
            # attributes
            "SEX", "CAST", "DSCR", "EDUC", "IDNO", "NATI", "NCHI",
            "NMR", "OCCU", "PROP", "RELI", "RESI", "SSN", "TITL", "FACT",
            # individual events
            "BIRT", "CHR", "DEAT", "BURI", "CREM", "ADOP",
            "BAPM", "BARM", "BASM", "BLES", "CHRA", "CONF", "FCOM",
            "ORDN", "NATU", "EMIG", "IMMI", "CENS", "PROB", "WILL",
            "GRAD", "RETI", "EVEN",
            # LDS ordinances
            "BAPL", "CONL", "ENDL", "SLGC",
            # family links
            "FAMC", "FAMS",
            # associations / references
            "SUBM", "ASSO", "ALIA", "ANCI", "DESI",
            # identifiers
            "RFN", "AFN", "REFN", "RIN",
            # meta
            "CHAN", "NOTE", "SOUR", "OBJE",
        },
        "cardinality": {
            "RESN": (0, 1), "NAME": (0, _M), "SEX": (0, 1),
            "CAST": (0, _M), "DSCR": (0, 1), "EDUC": (0, _M),
            "IDNO": (0, _M), "NATI": (0, _M), "NCHI": (0, 1),
            "NMR": (0, 1), "OCCU": (0, _M), "PROP": (0, _M),
            "RELI": (0, _M), "RESI": (0, _M), "SSN": (0, 1),
            "TITL": (0, _M), "FACT": (0, _M),
            "BIRT": (0, _M), "CHR": (0, _M), "DEAT": (0, _M),
            "BURI": (0, _M), "CREM": (0, _M), "ADOP": (0, _M),
            "BAPM": (0, _M), "BARM": (0, _M), "BASM": (0, _M),
            "BLES": (0, _M), "CHRA": (0, _M), "CONF": (0, _M),
            "FCOM": (0, _M), "ORDN": (0, _M), "NATU": (0, _M),
            "EMIG": (0, _M), "IMMI": (0, _M), "CENS": (0, _M),
            "PROB": (0, _M), "WILL": (0, _M), "GRAD": (0, _M),
            "RETI": (0, _M), "EVEN": (0, _M),
            "BAPL": (0, _M), "CONL": (0, _M), "ENDL": (0, _M), "SLGC": (0, _M),
            "FAMC": (0, _M), "FAMS": (0, _M),
            "SUBM": (0, _M), "ASSO": (0, _M), "ALIA": (0, _M),
            "ANCI": (0, _M), "DESI": (0, _M),
            "RFN": (0, 1), "AFN": (0, 1),
            "REFN": (0, _M), "RIN": (0, 1), "CHAN": (0, 1),
            "NOTE": (0, _M), "SOUR": (0, _M), "OBJE": (0, _M),
        },
    },

    "FAM_RECORD": {
        "payload_type": "none",
        "substructures": {
            "RESN",
            # family events
            "MARR", "MARB", "MARC", "MARL", "MARS", "DIV", "DIVF",
            "CENS", "ENGA", "EVEN",
            # LDS
            "SLGS",
            # participants
            "HUSB", "WIFE", "CHIL",
            # counts / cross-refs
            "NCHI", "SUBM",
            "REFN", "RIN", "CHAN", "NOTE", "SOUR", "OBJE",
        },
        "cardinality": {
            "RESN": (0, 1),
            "MARR": (0, _M), "MARB": (0, _M), "MARC": (0, _M),
            "MARL": (0, _M), "MARS": (0, _M), "DIV": (0, _M),
            "DIVF": (0, _M), "CENS": (0, _M), "ENGA": (0, _M),
            "EVEN": (0, _M), "SLGS": (0, _M),
            "HUSB": (0, 1), "WIFE": (0, 1), "CHIL": (0, _M),
            "NCHI": (0, 1), "SUBM": (0, _M),
            "REFN": (0, _M), "RIN": (0, 1), "CHAN": (0, 1),
            "NOTE": (0, _M), "SOUR": (0, _M), "OBJE": (0, _M),
        },
    },

    "SOUR_RECORD": {
        "payload_type": "none",
        "substructures": {
            "DATA", "AUTH", "TITL", "ABBR", "PUBL", "TEXT",
            "REPO", "NOTE", "OBJE", "REFN", "RIN", "CHAN",
        },
        "cardinality": {
            "DATA": (0, 1), "AUTH": (0, 1), "TITL": (0, 1),
            "ABBR": (0, 1), "PUBL": (0, 1), "TEXT": (0, 1),
            "REPO": (0, _M), "NOTE": (0, _M), "OBJE": (0, _M),
            "REFN": (0, _M), "RIN": (0, 1), "CHAN": (0, 1),
        },
    },

    "REPO_RECORD": {
        "payload_type": "none",
        "substructures": {"NAME", "ADDR", "PHON", "NOTE", "REFN", "RIN", "CHAN"},
        "cardinality": {
            "NAME": (0, 1), "ADDR": (0, 1), "PHON": (0, 3),
            "NOTE": (0, _M), "REFN": (0, _M), "RIN": (0, 1), "CHAN": (0, 1),
        },
    },

    "OBJE_RECORD": {
        "payload_type": "none",
        "substructures": {"FORM", "TITL", "FILE", "NOTE", "SOUR", "REFN", "RIN", "CHAN"},
        "cardinality": {
            "FORM": (1, 1), "TITL": (0, 1), "FILE": (0, 1),
            "NOTE": (0, _M), "SOUR": (0, _M),
            "REFN": (0, _M), "RIN": (0, 1), "CHAN": (0, 1),
        },
    },

    "NOTE_RECORD": {
        "payload_type": "text",
        "substructures": {"SOUR", "REFN", "RIN", "CHAN"},
        "cardinality": {
            "SOUR": (0, _M), "REFN": (0, _M), "RIN": (0, 1), "CHAN": (0, 1),
        },
    },

    "SUBM_RECORD": {
        "payload_type": "none",
        "substructures": {"NAME", "ADDR", "PHON", "OBJE", "LANG", "RFN", "RIN", "CHAN"},
        "cardinality": {
            "NAME": (1, 1), "ADDR": (0, 1), "PHON": (0, 3),
            "OBJE": (0, _M), "LANG": (0, 3), "RFN": (0, 1),
            "RIN": (0, 1), "CHAN": (0, 1),
        },
    },

    "SUBN_RECORD": {
        "payload_type": "none",
        "substructures": {"SUBM", "FAMF", "TEMP", "ANCE", "DESC", "ORDI", "RIN"},
        "cardinality": {
            "SUBM": (0, 1), "FAMF": (0, 1), "TEMP": (0, 1),
            "ANCE": (0, 1), "DESC": (0, 1), "ORDI": (0, 1), "RIN": (0, 1),
        },
    },

    # ── Inline / child structures ────────────────────────────────────────

    "NAME": {
        "payload_type": "name",
        "substructures": {
            "NPFX", "GIVN", "NICK", "SPFX", "SURN", "NSFX",
            "TYPE", "FONE", "ROMN", "SOUR", "NOTE",
        },
        "cardinality": {
            "NPFX": (0, 1), "GIVN": (0, 1), "NICK": (0, 1),
            "SPFX": (0, 1), "SURN": (0, 1), "NSFX": (0, 1),
            "TYPE": (0, 1), "FONE": (0, _M), "ROMN": (0, _M),
            "SOUR": (0, _M), "NOTE": (0, _M),
        },
    },

    # Individual events (inherit _EVENT_DETAIL)
    "BIRT": {
        "payload_type": "any",
        "substructures": _EVENT_DETAIL_SUBS | {"FAMC"},
        "cardinality": {**_EVENT_DETAIL_CARD, "FAMC": (0, 1)},
    },
    "CHR": {
        "payload_type": "any",
        "substructures": _EVENT_DETAIL_SUBS | {"FAMC"},
        "cardinality": {**_EVENT_DETAIL_CARD, "FAMC": (0, 1)},
    },
    "ADOP": {
        "payload_type": "any",
        "substructures": _EVENT_DETAIL_SUBS | {"FAMC"},
        "cardinality": {**_EVENT_DETAIL_CARD, "FAMC": (0, 1)},
    },
}

# Individual events that share plain event-detail rules
for _evt in (
    "DEAT", "BURI", "CREM", "BAPM", "BARM", "BASM", "BLES", "CHRA",
    "CONF", "FCOM", "ORDN", "NATU", "EMIG", "IMMI", "CENS", "PROB",
    "WILL", "GRAD", "RETI",
):
    _RULES[_evt] = {
        "payload_type": "any",
        "substructures": set(_EVENT_DETAIL_SUBS),
        "cardinality": dict(_EVENT_DETAIL_CARD),
    }

# General EVEN (individual or family) — adds ROLE
_RULES["EVEN"] = {
    "payload_type": "text",
    "substructures": _EVENT_DETAIL_SUBS | {"ROLE"},
    "cardinality": {**_EVENT_DETAIL_CARD, "ROLE": (0, 1)},
}

# Family events (same as individual events but with HUSB/WIFE age sub-records)
_FAM_EVT_SUBS = _EVENT_DETAIL_SUBS | {"HUSB", "WIFE"}
_FAM_EVT_CARD = {**_EVENT_DETAIL_CARD, "HUSB": (0, 1), "WIFE": (0, 1)}
for _evt in ("MARR", "MARB", "MARC", "MARL", "MARS", "DIV", "DIVF", "ENGA"):
    _RULES[_evt] = {
        "payload_type": "any",
        "substructures": set(_FAM_EVT_SUBS),
        "cardinality": dict(_FAM_EVT_CARD),
    }

# LDS ordinances
for _lds in ("BAPL", "CONL", "ENDL"):
    _RULES[_lds] = {
        "payload_type": "none",
        "substructures": set(_LDS_ORD_SUBS),
        "cardinality": dict(_LDS_ORD_CARD),
    }
_RULES["SLGC"] = {
    "payload_type": "none",
    "substructures": _LDS_ORD_SUBS | {"FAMC"},
    "cardinality": {**_LDS_ORD_CARD, "FAMC": (1, 1)},
}
_RULES["SLGS"] = {
    "payload_type": "none",
    "substructures": _LDS_ORD_SUBS,
    "cardinality": dict(_LDS_ORD_CARD),
}

_RULES.update({

    # ── Individual child-link ──────────────────────────────────────────
    "FAMC": {
        "payload_type": "pointer",
        "pointer_target": {"FAM"},
        "substructures": {"PEDI", "NOTE", "STAT"},
        "cardinality": {"PEDI": (0, 1), "NOTE": (0, _M), "STAT": (0, 1)},
    },
    "FAMS": {
        "payload_type": "pointer",
        "pointer_target": {"FAM"},
        "substructures": {"NOTE"},
        "cardinality": {"NOTE": (0, _M)},
    },
    "HUSB": {
        "payload_type": "pointer",
        "pointer_target": {"INDI"},
        "substructures": {"AGE"},
        "cardinality": {"AGE": (0, 1)},
    },
    "WIFE": {
        "payload_type": "pointer",
        "pointer_target": {"INDI"},
        "substructures": {"AGE"},
        "cardinality": {"AGE": (0, 1)},
    },
    "CHIL": {
        "payload_type": "pointer",
        "pointer_target": {"INDI"},
        "substructures": {},
        "cardinality": {},
    },
    "ALIA": {
        "payload_type": "pointer",
        "pointer_target": {"INDI"},
        "substructures": {},
        "cardinality": {},
    },
    "ANCI": {
        "payload_type": "pointer",
        "pointer_target": {"SUBM"},
        "substructures": {},
        "cardinality": {},
    },
    "DESI": {
        "payload_type": "pointer",
        "pointer_target": {"SUBM"},
        "substructures": {},
        "cardinality": {},
    },
    "SUBM": {
        "payload_type": "pointer",
        "pointer_target": {"SUBM"},
        "substructures": {},
        "cardinality": {},
    },

    # ── Source citation (inline SOUR child) ────────────────────────────
    "SOUR": {
        "payload_type": "any",   # pointer when citing a record, text when inline
        "pointer_target": {"SOUR"},
        "substructures": {"PAGE", "EVEN", "DATA", "QUAY", "NOTE", "OBJE", "TEXT"},
        "cardinality": {
            "PAGE": (0, 1), "EVEN": (0, 1), "DATA": (0, 1),
            "QUAY": (0, 1), "NOTE": (0, _M), "OBJE": (0, _M), "TEXT": (0, _M),
        },
    },

    # ── Source record DATA sub ─────────────────────────────────────────
    "DATA": {
        "payload_type": "none",
        "substructures": {"EVEN", "AGNC", "NOTE"},
        "cardinality": {"EVEN": (0, _M), "AGNC": (0, 1), "NOTE": (0, _M)},
    },

    # ── Repository citation ────────────────────────────────────────────
    "REPO": {
        "payload_type": "pointer",
        "pointer_target": {"REPO"},
        "substructures": {"CALN", "NOTE"},
        "cardinality": {"CALN": (0, _M), "NOTE": (0, _M)},
    },

    # ── Inline OBJE ────────────────────────────────────────────────────
    "OBJE": {
        "payload_type": "any",   # pointer or inline
        "pointer_target": {"OBJE"},
        "substructures": {"FORM", "TITL", "FILE", "NOTE"},
        "cardinality": {"FORM": (0, 1), "TITL": (0, 1), "FILE": (0, 1), "NOTE": (0, _M)},
    },

    # ── Inline NOTE ────────────────────────────────────────────────────
    "NOTE": {
        "payload_type": "any",   # pointer or free text
        "pointer_target": {"NOTE"},
        "substructures": {"SOUR"},
        "cardinality": {"SOUR": (0, _M)},
    },

    # ── ASSO ───────────────────────────────────────────────────────────
    "ASSO": {
        "payload_type": "pointer",
        "pointer_target": {"INDI"},
        "substructures": {"TYPE", "RELA", "NOTE", "SOUR"},
        "cardinality": {"TYPE": (0, 1), "RELA": (1, 1), "NOTE": (0, _M), "SOUR": (0, _M)},
    },

    # ── Address ────────────────────────────────────────────────────────
    "ADDR": {
        "payload_type": "text",
        "substructures": {"CONT", "ADR1", "ADR2", "CITY", "STAE", "POST", "CTRY"},
        "cardinality": {
            "CONT": (0, _M), "ADR1": (0, 1), "ADR2": (0, 1),
            "CITY": (0, 1), "STAE": (0, 1), "POST": (0, 1), "CTRY": (0, 1),
        },
    },

    # ── Place ──────────────────────────────────────────────────────────
    "PLAC": {
        "payload_type": "text",
        "substructures": {"FORM", "SOUR", "NOTE", "FONE", "ROMN"},
        "cardinality": {
            "FORM": (0, 1), "SOUR": (0, _M), "NOTE": (0, _M),
            "FONE": (0, _M), "ROMN": (0, _M),
        },
    },

    # ── CHAN ────────────────────────────────────────────────────────────
    "CHAN": {
        "payload_type": "none",
        "substructures": {"DATE", "NOTE"},
        "cardinality": {"DATE": (1, 1), "NOTE": (0, _M)},
    },

    # ── CHAN.DATE ──────────────────────────────────────────────────────
    "DATE": {
        "payload_type": "date",
        "substructures": {"TIME"},
        "cardinality": {"TIME": (0, 1)},
    },

    # ── HEAD children ─────────────────────────────────────────────────
    "GEDC": {
        "payload_type": "none",
        "substructures": {"VERS", "FORM"},
        "cardinality": {"VERS": (1, 1), "FORM": (0, 1)},
    },
    "CHAR": {
        "payload_type": "text",
        "substructures": {"VERS"},
        "cardinality": {"VERS": (0, 1)},
    },

    # ── REFN ───────────────────────────────────────────────────────────
    "REFN": {
        "payload_type": "text",
        "substructures": {"TYPE"},
        "cardinality": {"TYPE": (0, 1)},
    },

    # ── CALN ───────────────────────────────────────────────────────────
    "CALN": {
        "payload_type": "text",
        "substructures": {"MEDI"},
        "cardinality": {"MEDI": (0, 1)},
    },

    # ── FONE / ROMN ────────────────────────────────────────────────────
    "FONE": {
        "payload_type": "text",
        "substructures": {"TYPE"},
        "cardinality": {"TYPE": (0, 1)},
    },
    "ROMN": {
        "payload_type": "text",
        "substructures": {"TYPE"},
        "cardinality": {"TYPE": (0, 1)},
    },

    # ── SOUR.DATA inside source citation ──────────────────────────────
    # (re-used key — validator uses context to distinguish SOUR_RECORD.DATA
    # which is a separate record sub from SOUR citation data)
    # Generic DATA entry covers both usages adequately.

    # ── Leaf / scalar tags ─────────────────────────────────────────────
    **{tag: {"payload_type": "text", "substructures": set(), "cardinality": {}}
       for tag in (
           "TYPE", "TITL", "AUTH", "ABBR", "PUBL", "TEXT", "PAGE",
           "QUAY", "AGE", "AGNC", "CAUS", "RESN", "DEST", "FILE",
           "COPR", "LANG", "AFN", "RFN", "RIN", "VERS", "FORM",
           "FAMF", "TEMP", "ANCE", "DESC", "ORDI", "PEDI", "STAT",
           "RELA", "ROLE", "MEDI", "NICK", "NPFX", "NSFX", "SPFX",
           "GIVN", "SURN", "NCHI", "NMR", "SSN", "PHON", "EMAIL",
           "FAX", "WWW", "ADR1", "ADR2", "CITY", "STAE", "POST",
           "CTRY", "TIME", "FACT",
       )},

    "SEX": {"payload_type": "sex", "substructures": set(), "cardinality": {}},
    "CONT": {"payload_type": "text", "substructures": set(), "cardinality": {}},
    "CONC": {"payload_type": "text", "substructures": set(), "cardinality": {}},
    "NAME": _RULES.get("NAME", {"payload_type": "name", "substructures": set(), "cardinality": {}}),
})

# ---------------------------------------------------------------------------
# Top-level record context map
# ---------------------------------------------------------------------------

# Maps GEDCOM tag at level 0 → rule key in _RULES
TOP_LEVEL_TAG_TO_RULE: Dict[str, str] = {
    "HEAD":  "HEAD",
    "INDI":  "INDI_RECORD",
    "FAM":   "FAM_RECORD",
    "SOUR":  "SOUR_RECORD",
    "REPO":  "REPO_RECORD",
    "OBJE":  "OBJE_RECORD",
    "NOTE":  "NOTE_RECORD",
    "SUBM":  "SUBM_RECORD",
    "SUBN":  "SUBN_RECORD",
    "TRLR":  None,          # trailer — no children
}

# Required top-level records (must appear at least once)
REQUIRED_RECORDS: FrozenSet[str] = frozenset({"HEAD", "TRLR"})

# ---------------------------------------------------------------------------
# Valid enumerated values
# ---------------------------------------------------------------------------

SEX_VALUES:  FrozenSet[str] = frozenset({"M", "F", "U", "X", "N"})
PEDI_VALUES: FrozenSet[str] = frozenset({"ADOPTED", "BIRTH", "FOSTER", "SEALING"})
QUAY_VALUES: FrozenSet[str] = frozenset({"0", "1", "2", "3"})
RESN_VALUES: FrozenSet[str] = frozenset({"CONFIDENTIAL", "LOCKED", "PRIVACY"})
MEDI_VALUES: FrozenSet[str] = frozenset({
    "AUDIO", "BOOK", "CARD", "ELECTRONIC", "FICHE", "FILM",
    "MAGAZINE", "MANUSCRIPT", "MAP", "NEWSPAPER", "PHOTO",
    "TOMBSTONE", "VIDEO",
})
LDS_STAT_CHILD: FrozenSet[str] = frozenset({
    "CHALLENGED", "DISPROVEN", "PROVEN",
})
LDS_STAT_ORD: FrozenSet[str] = frozenset({
    "BIC", "CANCELED", "CHILD", "COMPLETED", "DNS", "DNS/CAN",
    "EXCLUDED", "INFANT", "PRE-1970", "STILLBORN",
    "SUBMITTED", "UNCLEARED",
})

# ---------------------------------------------------------------------------
# Date patterns (GEDCOM 5.5.1 §2.5 calendar grammar)
# ---------------------------------------------------------------------------

import re as _re

# Simple year patterns
_YEAR        = r"\d{1,4}(/\d{2})?"        # 1900 or 1900/01 (dual dating)
_MONTH       = r"(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)"
_DAY         = r"\d{1,2}"
_DATE_SIMPLE = (
    rf"(?:(?:{_DAY}\s+)?{_MONTH}\s+)?{_YEAR}"  # [D] [MMM] YYYY
)
_MODIFIER    = r"(?:ABT|CAL|EST|AFT|BEF)"
_DATE_VAL    = rf"(?:{_MODIFIER}\s+)?{_DATE_SIMPLE}"
_DATE_PERIOD = rf"FROM\s+{_DATE_SIMPLE}(?:\s+TO\s+{_DATE_SIMPLE})?"
_DATE_RANGE  = rf"BET\s+{_DATE_SIMPLE}\s+AND\s+{_DATE_SIMPLE}"
_DATE_INT    = rf"INT\s+{_DATE_SIMPLE}\s+\(.*?\)"
_DATE_PHRASE = r"\(.*?\)"

DATE_RE = _re.compile(
    rf"^(?:{_DATE_PERIOD}|{_DATE_RANGE}|{_DATE_INT}|{_DATE_VAL}|{_DATE_PHRASE})$",
    _re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Public API helpers
# ---------------------------------------------------------------------------

def rule_for(tag: str, *, is_record: bool = False) -> Optional[Dict[str, Any]]:
    """Return the spec rule dict for *tag*.

    *is_record* should be True when the tag is a level-0 xref-bearing node
    so that ``SOUR`` → ``SOUR_RECORD`` etc. is resolved correctly.
    """
    if is_record:
        record_key = f"{tag}_RECORD"
        if record_key in _RULES:
            return _RULES[record_key]
        return _RULES.get(tag)
    return _RULES.get(tag)


def allowed_children(tag: str, *, is_record: bool = False) -> Set[str]:
    """Return the set of allowed child tags for *tag*."""
    r = rule_for(tag, is_record=is_record)
    if r is None:
        return set()
    return set(r.get("substructures") or set())


def get_cardinality(
    tag: str, child_tag: str, *, is_record: bool = False
) -> Optional[Tuple[int, Optional[int]]]:
    """Return ``(min, max)`` cardinality for *child_tag* under *tag*, or None."""
    r = rule_for(tag, is_record=is_record)
    if r is None:
        return None
    return r.get("cardinality", {}).get(child_tag)


def is_valid_date(value: str) -> bool:
    """Return True if *value* matches the GEDCOM 5.5.1 date grammar."""
    return bool(DATE_RE.match(value.strip()))
