"""
======================================================================
 Project: gedcomtools
 File:    gedcom7/specification.py
 Author:  David J. Cartwright
 Purpose: GEDCOM 7 structural specification rule layer used by the
          parser, validator, and writer.

 Created: 2026-03-01
 Updated:
   - 2026-03-15: added full enum_values for MEDI, PEDI, ROLE;
                 FAMC.STAT enum constant; CHIL PHRASE substructure
   - 2026-03-16: added _CONTEXT_ENUM_RULES and get_context_enum_values()
                 for FAMC.STAT context-specific validation;
                 get_label() now returns real human-readable labels via _TAG_LABELS
======================================================================

This module provides a normalized rule layer that sits on top of the raw
GEDCOM 7 tag/URI mapping. It intentionally starts with a practical core rule
set that is enough to parse and validate common GEDCOM 7 files while still
being easy to extend.

The structure registry in this file is used by the parser and validator for:

- top-level legality checks
- parent/child legality checks
- child cardinality checks
- basic payload typing
- selected enumeration checks

The docstrings are written in Google style so they render well with
Sphinx Napoleon.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .g7interop import G7_TAG_TO_URI, get_uri_for_tag, register_tag_uri

HEAD = "HEAD"
TRLR = "TRLR"
GEDC = "GEDC"
SCHMA = "SCHMA"
CONC = "CONC"
CONT = "CONT"

PAYLOAD_TEXT = "text"
PAYLOAD_POINTER = "pointer"
PAYLOAD_NONE = "none"
PAYLOAD_ENUM = "enum"

# Enumeration value sets used by the validator and spec registry.
FAMC_STAT_ENUM = frozenset({"CHALLENGED", "DISPROVEN", "PROVEN"})

# Context-specific enum rules: (tag, parent_tag) → frozenset of valid values.
# Used when the same tag has different allowed values depending on its parent.
_CONTEXT_ENUM_RULES: Dict[tuple, frozenset] = {
    ("STAT", "FAMC"): FAMC_STAT_ENUM,
}

# ---------------------------------------------------------------------------
# Shared substructure building blocks used to construct _CORE_RULES.
# These are only referenced at module load time; callers always use the
# public helper functions below.
# ---------------------------------------------------------------------------

_ADDR_SUBS: Dict[str, str] = {
    "ADR1": "ADR1", "ADR2": "ADR2", "ADR3": "ADR3",
    "CITY": "CITY", "STAE": "STAE", "POST": "POST", "CTRY": "CTRY",
}
_ADDR_CARD: Dict[str, tuple] = {
    "ADR1": (0, 1), "ADR2": (0, 1), "ADR3": (0, 1),
    "CITY": (0, 1), "STAE": (0, 1), "POST": (0, 1), "CTRY": (0, 1),
}

_CONTACT_SUBS: Dict[str, str] = {
    "PHON": "PHON", "EMAIL": "EMAIL", "FAX": "FAX", "WWW": "WWW",
}
_CONTACT_CARD: Dict[str, tuple] = {
    "PHON": (0, 3), "EMAIL": (0, 3), "FAX": (0, 3), "WWW": (0, 3),
}

# Substructures shared by most individual and family events/attributes.
_EVENT_DETAIL_SUBS: Dict[str, str] = {
    **_CONTACT_SUBS,
    "TYPE": "TYPE", "DATE": "DATE", "PLAC": "PLAC", "ADDR": "ADDR",
    "AGNC": "AGNC", "RELI": "RELI", "CAUS": "CAUS", "RESN": "RESN",
    "SDATE": "SDATE", "ASSO": "ASSO",
    "NOTE": "NOTE", "SNOTE": "SNOTE", "SOUR": "SOUR", "OBJE": "OBJE",
    "UID": "UID",
}
_EVENT_DETAIL_CARD: Dict[str, tuple] = {
    **_CONTACT_CARD,
    "TYPE": (0, 1), "DATE": (0, 1), "PLAC": (0, 1), "ADDR": (0, 1),
    "AGNC": (0, 1), "RELI": (0, 1), "CAUS": (0, 1), "RESN": (0, 1),
    "SDATE": (0, 1), "ASSO": (0, None),
    "NOTE": (0, None), "SNOTE": (0, None), "SOUR": (0, None),
    "OBJE": (0, None), "UID": (0, None),
}

# LDS ordinance substructures (BAPL, CONL, ENDL, INIL).
_LDS_ORD_SUBS: Dict[str, str] = {
    "STAT": "STAT", "DATE": "DATE", "TEMP": "TEMP",
    "NOTE": "NOTE", "SNOTE": "SNOTE", "SOUR": "SOUR",
}
_LDS_ORD_CARD: Dict[str, tuple] = {
    "STAT": (0, 1), "DATE": (0, 1), "TEMP": (0, 1),
    "NOTE": (0, None), "SNOTE": (0, None), "SOUR": (0, None),
}

# Standard trailing admin fields present on most top-level records.
_RECORD_TAIL_SUBS: Dict[str, str] = {
    "NOTE": "NOTE", "SNOTE": "SNOTE", "SOUR": "SOUR", "OBJE": "OBJE",
    "REFN": "REFN", "UID": "UID", "EXID": "EXID", "CHAN": "CHAN", "CREA": "CREA",
}
_RECORD_TAIL_CARD: Dict[str, tuple] = {
    "NOTE": (0, None), "SNOTE": (0, None), "SOUR": (0, None), "OBJE": (0, None),
    "REFN": (0, None), "UID": (0, None), "EXID": (0, None),
    "CHAN": (0, 1), "CREA": (0, 1),
}

_CORE_RULES: Dict[str, Dict[str, Any]] = {
    # ── File structure ────────────────────────────────────────────────────────
    "HEAD": {
        "payload_type": PAYLOAD_NONE,
        "substructures": {
            "GEDC": "GEDC", "SCHMA": "SCHMA",
            "SOUR": "SOUR", "DEST": "DEST", "DATE": "DATE",
            "SUBM": "SUBM", "FILE": "FILE", "COPR": "COPR",
            "LANG": "LANG", "PLAC": "PLAC", "NOTE": "NOTE",
        },
        "cardinality": {
            "GEDC": (1, 1), "SCHMA": (0, 1),
            "SOUR": (0, 1), "DEST": (0, 1), "DATE": (0, 1),
            "SUBM": (0, None), "FILE": (0, 1), "COPR": (0, 1),
            "LANG": (0, None), "PLAC": (0, 1), "NOTE": (0, None),
        },
    },
    "GEDC": {
        "payload_type": PAYLOAD_NONE,
        "substructures": {"VERS": "VERS"},
        "cardinality": {"VERS": (1, 1)},
    },
    "SCHMA": {
        "payload_type": PAYLOAD_NONE,
        "substructures": {"TAG": "TAG"},
        "cardinality": {"TAG": (0, None)},
    },
    "TAG":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "TRLR": {"payload_type": PAYLOAD_NONE, "substructures": {}, "cardinality": {}},

    # ── Individual record ─────────────────────────────────────────────────────
    "INDI": {
        "payload_type": PAYLOAD_NONE,
        "substructures": {
            "NAME": "NAME", "SEX": "SEX", "RESN": "RESN",
            # standard individual events
            "ADOP": "ADOP", "BAPM": "BAPM", "BARM": "BARM", "BASM": "BASM",
            "BLES": "BLES", "BIRT": "BIRT", "BURI": "BURI", "CAST": "CAST",
            "CENS": "CENS", "CHR": "CHR",  "CHRA": "CHRA", "CONF": "CONF",
            "CREM": "CREM", "DEAT": "DEAT", "DSCR": "DSCR", "EDUC": "EDUC",
            "EMIG": "EMIG", "EVEN": "EVEN", "FACT": "FACT", "FCOM": "FCOM",
            "GRAD": "GRAD", "IDNO": "IDNO", "IMMI": "IMMI", "NATI": "NATI",
            "NATU": "NATU", "NCHI": "NCHI", "NMR":  "NMR",  "OCCU": "OCCU",
            "ORDN": "ORDN", "PROB": "PROB", "PROP": "PROP", "RELI": "RELI",
            "RESI": "RESI", "RETI": "RETI", "SSN":  "SSN",  "TITL": "TITL",
            "WILL": "WILL",
            # non-event marker
            "NO": "NO",
            # LDS ordinances
            "BAPL": "BAPL", "CONL": "CONL", "ENDL": "ENDL",
            "INIL": "INIL", "SLGC": "SLGC",
            # family links
            "FAMC": "FAMC", "FAMS": "FAMS",
            # associations and cross-references
            "ASSO": "ASSO", "ALIA": "ALIA", "ANCI": "ANCI",
            "DESI": "DESI", "SUBM": "SUBM",
            **_RECORD_TAIL_SUBS,
        },
        "cardinality": {
            "NAME": (0, None), "SEX": (0, 1), "RESN": (0, 1),
            "ADOP": (0, None), "BAPM": (0, None), "BARM": (0, None), "BASM": (0, None),
            "BLES": (0, None), "BIRT": (0, 1),   "BURI": (0, None), "CAST": (0, None),
            "CENS": (0, None), "CHR":  (0, None), "CHRA": (0, None), "CONF": (0, None),
            "CREM": (0, None), "DEAT": (0, 1),   "DSCR": (0, None), "EDUC": (0, None),
            "EMIG": (0, None), "EVEN": (0, None), "FACT": (0, None), "FCOM": (0, None),
            "GRAD": (0, None), "IDNO": (0, None), "IMMI": (0, None), "NATI": (0, None),
            "NATU": (0, None), "NCHI": (0, None), "NMR":  (0, None), "OCCU": (0, None),
            "ORDN": (0, None), "PROB": (0, None), "PROP": (0, None), "RELI": (0, None),
            "RESI": (0, None), "RETI": (0, None), "SSN":  (0, None), "TITL": (0, None),
            "WILL": (0, None),
            "NO":   (0, None),
            "BAPL": (0, None), "CONL": (0, None), "ENDL": (0, None),
            "INIL": (0, None), "SLGC": (0, None),
            "FAMC": (0, None), "FAMS": (0, None),
            "ASSO": (0, None), "ALIA": (0, None), "ANCI": (0, None),
            "DESI": (0, None), "SUBM": (0, None),
            **_RECORD_TAIL_CARD,
        },
    },

    # ── FAM record ───────────────────────────────────────────────────────────
    "FAM": {
        "payload_type": PAYLOAD_NONE,
        "substructures": {
            "RESN": "RESN",
            "ANUL": "ANUL", "CENS": "CENS", "DIV":  "DIV",  "DIVF": "DIVF",
            "ENGA": "ENGA", "EVEN": "EVEN", "FACT": "FACT",
            "MARB": "MARB", "MARC": "MARC", "MARL": "MARL", "MARR": "MARR",
            "MARS": "MARS", "NCHI": "NCHI", "RESI": "RESI",
            "NO":   "NO",
            "SLGS": "SLGS",
            "HUSB": "HUSB", "WIFE": "WIFE", "CHIL": "CHIL",
            "ASSO": "ASSO", "SUBM": "SUBM",
            **_RECORD_TAIL_SUBS,
        },
        "cardinality": {
            "RESN": (0, 1),
            "ANUL": (0, None), "CENS": (0, None), "DIV":  (0, 1),   "DIVF": (0, None),
            "ENGA": (0, None), "EVEN": (0, None), "FACT": (0, None),
            "MARB": (0, None), "MARC": (0, None), "MARL": (0, None), "MARR": (0, 1),
            "MARS": (0, None), "NCHI": (0, None), "RESI": (0, None),
            "NO":   (0, None),
            "SLGS": (0, None),
            "HUSB": (0, 1), "WIFE": (0, 1), "CHIL": (0, None),
            "ASSO": (0, None), "SUBM": (0, None),
            **_RECORD_TAIL_CARD,
        },
    },

    # ── OBJE record & citation (union) ───────────────────────────────────────
    # Top-level record: PAYLOAD_NONE with FILE, REFN, UID, etc.
    # Citation substructure: PAYLOAD_POINTER with CROP, TITL.
    # PAYLOAD_TEXT avoids false pointer_required on the record form.
    "OBJE": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {
            "RESN": "RESN", "FILE": "FILE",
            "CROP": "CROP", "TITL": "TITL",
            **_RECORD_TAIL_SUBS,
        },
        "cardinality": {
            "RESN": (0, 1), "FILE": (0, None),
            "CROP": (0, 1), "TITL": (0, None),
            **_RECORD_TAIL_CARD,
        },
    },

    # ── REPO record ──────────────────────────────────────────────────────────
    # Also used as a citation pointer (e.g. 2 REPO @R1@). PAYLOAD_TEXT and
    # optional NAME avoid false errors on the citation form.
    "REPO": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {
            "NAME": "NAME", "ADDR": "ADDR",
            **_CONTACT_SUBS,
            "NOTE": "NOTE", "SNOTE": "SNOTE",
            "CALN": "CALN",
            **_RECORD_TAIL_SUBS,
        },
        "cardinality": {
            "NAME": (0, 1), "ADDR": (0, 1),
            **_CONTACT_CARD,
            "NOTE": (0, None), "SNOTE": (0, None),
            "CALN": (0, None),
            **_RECORD_TAIL_CARD,
        },
    },

    # ── SNOTE record ─────────────────────────────────────────────────────────
    # As top-level record: payload is the note text.
    # As substructure: payload is a pointer to a SNOTE record.
    "SNOTE": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {
            "MIME": "MIME", "LANG": "LANG", "TRAN": "TRAN", "SOUR": "SOUR",
            **_RECORD_TAIL_SUBS,
        },
        "cardinality": {
            "MIME": (0, 1), "LANG": (0, None), "TRAN": (0, None), "SOUR": (0, None),
            **_RECORD_TAIL_CARD,
        },
    },

    # ── SOUR record, citation, and HEAD.SOUR (union) ─────────────────────────
    # PAYLOAD_TEXT avoids false pointer_required on the record and HEAD forms.
    "SOUR": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {
            # record fields
            "DATA": "DATA", "AUTH": "AUTH", "TITL": "TITL", "ABBR": "ABBR",
            "PUBL": "PUBL", "TEXT": "TEXT", "REPO": "REPO",
            # HEAD.SOUR identification fields
            "VERS": "VERS", "NAME": "NAME", "CORP": "CORP",
            # citation fields
            "PAGE": "PAGE", "EVEN": "EVEN", "QUAY": "QUAY",
            **_RECORD_TAIL_SUBS,
        },
        "cardinality": {
            "DATA": (0, 1), "AUTH": (0, 1), "TITL": (0, None), "ABBR": (0, 1),
            "PUBL": (0, 1), "TEXT": (0, None), "REPO": (0, None),
            "VERS": (0, 1), "NAME": (0, 1), "CORP": (0, 1),
            "PAGE": (0, 1), "EVEN": (0, None), "QUAY": (0, 1),
            **_RECORD_TAIL_CARD,
        },
    },

    # ── SUBM record ──────────────────────────────────────────────────────────
    # Also used as a citation pointer (e.g. 1 SUBM @U1@). PAYLOAD_TEXT and
    # optional NAME avoid false errors on the citation form.
    "SUBM": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {
            "NAME": "NAME", "ADDR": "ADDR",
            **_CONTACT_SUBS,
            "LANG": "LANG", "OBJE": "OBJE",
            **_RECORD_TAIL_SUBS,
        },
        "cardinality": {
            "NAME": (0, 1), "ADDR": (0, 1),
            **_CONTACT_CARD,
            "LANG": (0, None), "OBJE": (0, None),
            **_RECORD_TAIL_CARD,
        },
    },

    # ── Name structure ───────────────────────────────────────────────────────
    "NAME": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {
            "TYPE": "TYPE", "GIVN": "GIVN", "SURN": "SURN", "NPFX": "NPFX",
            "NSFX": "NSFX", "NICK": "NICK", "SPFX": "SPFX",
            "TRAN": "TRAN", "NOTE": "NOTE", "SNOTE": "SNOTE", "SOUR": "SOUR",
        },
        "cardinality": {
            "TYPE": (0, 1), "GIVN": (0, 1), "SURN": (0, 1), "NPFX": (0, 1),
            "NSFX": (0, 1), "NICK": (0, None), "SPFX": (0, 1),
            "TRAN": (0, None), "NOTE": (0, None), "SNOTE": (0, None), "SOUR": (0, None),
        },
    },
    "SEX": {
        "payload_type": PAYLOAD_ENUM,
        "enum_values": {"M", "F", "X", "U"},
        "substructures": {}, "cardinality": {},
    },

    # ── Individual events ─────────────────────────────────────────────────────
    "BIRT": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {**_EVENT_DETAIL_SUBS, "AGE": "AGE", "FAMC": "FAMC"},
        "cardinality":   {**_EVENT_DETAIL_CARD, "AGE": (0, 1), "FAMC": (0, 1)},
    },
    "CHR": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {**_EVENT_DETAIL_SUBS, "AGE": "AGE", "FAMC": "FAMC"},
        "cardinality":   {**_EVENT_DETAIL_CARD, "AGE": (0, 1), "FAMC": (0, 1)},
    },
    "DEAT": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "BURI": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "CREM": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "ADOP": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {**_EVENT_DETAIL_SUBS, "FAMC": "FAMC"},
        "cardinality":   {**_EVENT_DETAIL_CARD, "FAMC": (0, 1)},
    },
    "BAPM": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "BARM": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "BASM": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "BLES": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "CENS": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "CHRA": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "CONF": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "EMIG": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "FCOM": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "GRAD": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "IMMI": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "NATU": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "ORDN": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "PROB": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "RETI": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "WILL": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},

    # ── Individual attributes (text payload, TYPE + event detail) ─────────────
    "CAST": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "DSCR": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "EDUC": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "IDNO": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "NATI": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "NCHI": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {**_EVENT_DETAIL_SUBS, "HUSB": "HUSB", "WIFE": "WIFE"},
        "cardinality":   {**_EVENT_DETAIL_CARD, "HUSB": (0, 1), "WIFE": (0, 1)},
    },
    "NMR":  {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "OCCU": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "PROP": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "RELI": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "RESI": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {**_EVENT_DETAIL_SUBS, "HUSB": "HUSB", "WIFE": "WIFE"},
        "cardinality":   {**_EVENT_DETAIL_CARD, "HUSB": (0, 1), "WIFE": (0, 1)},
    },
    "SSN":  {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},
    "TITL": {"payload_type": PAYLOAD_TEXT, "substructures": _EVENT_DETAIL_SUBS, "cardinality": _EVENT_DETAIL_CARD},

    # ── Generic event and fact (INDI and FAM) ─────────────────────────────────
    "EVEN": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {**_EVENT_DETAIL_SUBS, "HUSB": "HUSB", "WIFE": "WIFE",
                          "ROLE": "ROLE", "PHRASE": "PHRASE"},
        "cardinality":   {**_EVENT_DETAIL_CARD, "HUSB": (0, 1), "WIFE": (0, 1),
                          "ROLE": (0, 1), "PHRASE": (0, 1)},
    },
    "FACT": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {**_EVENT_DETAIL_SUBS, "HUSB": "HUSB", "WIFE": "WIFE"},
        "cardinality":   {**_EVENT_DETAIL_CARD, "HUSB": (0, 1), "WIFE": (0, 1)},
    },

    # ── Non-event ─────────────────────────────────────────────────────────────
    "NO": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {"DATE": "DATE", "NOTE": "NOTE", "SNOTE": "SNOTE", "SOUR": "SOUR"},
        "cardinality":   {"DATE": (0, 1), "NOTE": (0, None), "SNOTE": (0, None), "SOUR": (0, None)},
    },

    # ── LDS ordinances ────────────────────────────────────────────────────────
    "BAPL": {"payload_type": PAYLOAD_TEXT,
             "substructures": {**_LDS_ORD_SUBS, "PLAC": "PLAC"},
             "cardinality":   {**_LDS_ORD_CARD, "PLAC": (0, 1)}},
    "CONL": {"payload_type": PAYLOAD_TEXT,
             "substructures": {**_LDS_ORD_SUBS, "PLAC": "PLAC"},
             "cardinality":   {**_LDS_ORD_CARD, "PLAC": (0, 1)}},
    "ENDL": {"payload_type": PAYLOAD_TEXT,
             "substructures": {**_LDS_ORD_SUBS, "PLAC": "PLAC"},
             "cardinality":   {**_LDS_ORD_CARD, "PLAC": (0, 1)}},
    "INIL": {"payload_type": PAYLOAD_TEXT,
             "substructures": {**_LDS_ORD_SUBS, "PLAC": "PLAC"},
             "cardinality":   {**_LDS_ORD_CARD, "PLAC": (0, 1)}},
    "SLGC": {
        "payload_type": PAYLOAD_NONE,
        "substructures": {**_LDS_ORD_SUBS, "PLAC": "PLAC", "FAMC": "FAMC"},
        "cardinality":   {**_LDS_ORD_CARD, "PLAC": (0, 1), "FAMC": (0, 1)},
    },
    "SLGS": {
        "payload_type": PAYLOAD_NONE,
        "substructures": {**_LDS_ORD_SUBS, "PLAC": "PLAC"},
        "cardinality":   {**_LDS_ORD_CARD, "PLAC": (0, 1)},
    },

    # ── Family events ─────────────────────────────────────────────────────────
    "MARR": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {**_EVENT_DETAIL_SUBS, "HUSB": "HUSB", "WIFE": "WIFE"},
        "cardinality":   {**_EVENT_DETAIL_CARD, "HUSB": (0, 1), "WIFE": (0, 1)},
    },
    "ANUL": {"payload_type": PAYLOAD_TEXT,
             "substructures": {**_EVENT_DETAIL_SUBS, "HUSB": "HUSB", "WIFE": "WIFE"},
             "cardinality":   {**_EVENT_DETAIL_CARD, "HUSB": (0, 1), "WIFE": (0, 1)}},
    "DIV":  {"payload_type": PAYLOAD_TEXT,
             "substructures": {**_EVENT_DETAIL_SUBS, "HUSB": "HUSB", "WIFE": "WIFE"},
             "cardinality":   {**_EVENT_DETAIL_CARD, "HUSB": (0, 1), "WIFE": (0, 1)}},
    "DIVF": {"payload_type": PAYLOAD_TEXT,
             "substructures": {**_EVENT_DETAIL_SUBS, "HUSB": "HUSB", "WIFE": "WIFE"},
             "cardinality":   {**_EVENT_DETAIL_CARD, "HUSB": (0, 1), "WIFE": (0, 1)}},
    "ENGA": {"payload_type": PAYLOAD_TEXT,
             "substructures": {**_EVENT_DETAIL_SUBS, "HUSB": "HUSB", "WIFE": "WIFE"},
             "cardinality":   {**_EVENT_DETAIL_CARD, "HUSB": (0, 1), "WIFE": (0, 1)}},
    "MARB": {"payload_type": PAYLOAD_TEXT,
             "substructures": {**_EVENT_DETAIL_SUBS, "HUSB": "HUSB", "WIFE": "WIFE"},
             "cardinality":   {**_EVENT_DETAIL_CARD, "HUSB": (0, 1), "WIFE": (0, 1)}},
    "MARC": {"payload_type": PAYLOAD_TEXT,
             "substructures": {**_EVENT_DETAIL_SUBS, "HUSB": "HUSB", "WIFE": "WIFE"},
             "cardinality":   {**_EVENT_DETAIL_CARD, "HUSB": (0, 1), "WIFE": (0, 1)}},
    "MARL": {"payload_type": PAYLOAD_TEXT,
             "substructures": {**_EVENT_DETAIL_SUBS, "HUSB": "HUSB", "WIFE": "WIFE"},
             "cardinality":   {**_EVENT_DETAIL_CARD, "HUSB": (0, 1), "WIFE": (0, 1)}},
    "MARS": {"payload_type": PAYLOAD_TEXT,
             "substructures": {**_EVENT_DETAIL_SUBS, "HUSB": "HUSB", "WIFE": "WIFE"},
             "cardinality":   {**_EVENT_DETAIL_CARD, "HUSB": (0, 1), "WIFE": (0, 1)}},

    # ── Family pointer tags ───────────────────────────────────────────────────
    # HUSB/WIFE: pointer under FAM, or no-payload age holder under events.
    # PAYLOAD_TEXT accepts both forms without false pointer_required errors.
    "HUSB": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {"AGE": "AGE", "PHRASE": "PHRASE"},
        "cardinality":   {"AGE": (0, 1), "PHRASE": (0, 1)},
    },
    "WIFE": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {"AGE": "AGE", "PHRASE": "PHRASE"},
        "cardinality":   {"AGE": (0, 1), "PHRASE": (0, 1)},
    },
    "CHIL": {
        "payload_type": PAYLOAD_POINTER,
        "substructures": {"PHRASE": "PHRASE"},
        "cardinality":   {"PHRASE": (0, 1)},
    },
    "FAMC": {
        "payload_type": PAYLOAD_POINTER,
        "substructures": {"PEDI": "PEDI", "STAT": "STAT", "NOTE": "NOTE", "ADOP": "ADOP"},
        "cardinality":   {"PEDI": (0, 1), "STAT": (0, 1), "NOTE": (0, None), "ADOP": (0, 1)},
    },
    "FAMS": {
        "payload_type": PAYLOAD_POINTER,
        "substructures": {"NOTE": "NOTE", "SNOTE": "SNOTE"},
        "cardinality":   {"NOTE": (0, None), "SNOTE": (0, None)},
    },
    "ALIA": {
        "payload_type": PAYLOAD_POINTER,
        "substructures": {"PHRASE": "PHRASE"},
        "cardinality":   {"PHRASE": (0, 1)},
    },
    "ANCI": {"payload_type": PAYLOAD_POINTER, "substructures": {}, "cardinality": {}},
    "DESI": {"payload_type": PAYLOAD_POINTER, "substructures": {}, "cardinality": {}},

    # ── Association ───────────────────────────────────────────────────────────
    "ASSO": {
        "payload_type": PAYLOAD_POINTER,
        "substructures": {
            "PHRASE": "PHRASE", "ROLE": "ROLE",
            "NOTE": "NOTE", "SNOTE": "SNOTE", "SOUR": "SOUR",
        },
        "cardinality": {
            "PHRASE": (0, 1), "ROLE": (0, 1),
            "NOTE": (0, None), "SNOTE": (0, None), "SOUR": (0, None),
        },
    },

    # ── Date, place, note ─────────────────────────────────────────────────────
    "DATE": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {"TIME": "TIME", "PHRASE": "PHRASE"},
        "cardinality":   {"TIME": (0, 1), "PHRASE": (0, 1)},
    },
    "PLAC": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {
            "FORM": "FORM", "LANG": "LANG", "MAP": "MAP",
            "EXID": "EXID", "NOTE": "NOTE", "SNOTE": "SNOTE", "TRAN": "TRAN",
        },
        "cardinality": {
            "FORM": (0, 1), "LANG": (0, 1), "MAP": (0, 1),
            "EXID": (0, None), "NOTE": (0, None), "SNOTE": (0, None), "TRAN": (0, None),
        },
    },
    "MAP": {
        "payload_type": PAYLOAD_NONE,
        "substructures": {"LATI": "LATI", "LONG": "LONG"},
        "cardinality":   {"LATI": (1, 1), "LONG": (1, 1)},
    },
    "NOTE": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {
            "MIME": "MIME", "LANG": "LANG", "TRAN": "TRAN", "SOUR": "SOUR",
        },
        "cardinality": {
            "MIME": (0, 1), "LANG": (0, 1), "TRAN": (0, None), "SOUR": (0, None),
        },
    },

    # ── Source data substructures ─────────────────────────────────────────────
    "PAGE": {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "QUAY": {
        "payload_type": PAYLOAD_ENUM,
        "enum_values": {"0", "1", "2", "3"},
        "substructures": {}, "cardinality": {},
    },
    "DATA": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {
            "DATE": "DATE", "TEXT": "TEXT", "COPR": "COPR",
            "EVEN": "EVEN", "AGNC": "AGNC",
            "NOTE": "NOTE", "SNOTE": "SNOTE",
        },
        "cardinality": {
            "DATE": (0, 1), "TEXT": (0, None), "COPR": (0, 1),
            "EVEN": (0, None), "AGNC": (0, 1),
            "NOTE": (0, None), "SNOTE": (0, None),
        },
    },

    # ── Media and file ────────────────────────────────────────────────────────
    "FILE": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {"FORM": "FORM", "MEDI": "MEDI", "TITL": "TITL", "TRAN": "TRAN"},
        "cardinality":   {"FORM": (0, 1), "MEDI": (0, 1), "TITL": (0, 1), "TRAN": (0, None)},
    },
    "CROP": {
        "payload_type": PAYLOAD_NONE,
        "substructures": {"TOP": "TOP", "LEFT": "LEFT", "HEIGHT": "HEIGHT", "WIDTH": "WIDTH"},
        "cardinality":   {"TOP": (0, 1), "LEFT": (0, 1), "HEIGHT": (0, 1), "WIDTH": (0, 1)},
    },

    # ── Address and contact ───────────────────────────────────────────────────
    "ADDR": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {**_ADDR_SUBS},
        "cardinality":   {**_ADDR_CARD},
    },
    "CORP": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {"ADDR": "ADDR", **_CONTACT_SUBS},
        "cardinality":   {"ADDR": (0, 1), **_CONTACT_CARD},
    },

    # ── Repository citation ───────────────────────────────────────────────────
    "CALN": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {"MEDI": "MEDI"},
        "cardinality":   {"MEDI": (0, 1)},
    },

    # ── Shared admin structures ───────────────────────────────────────────────
    "CHAN": {
        "payload_type": PAYLOAD_NONE,
        "substructures": {"DATE": "DATE", "NOTE": "NOTE"},
        "cardinality":   {"DATE": (1, 1), "NOTE": (0, None)},
    },
    "CREA": {
        "payload_type": PAYLOAD_NONE,
        "substructures": {"DATE": "DATE"},
        "cardinality":   {"DATE": (1, 1)},
    },
    "STAT": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {"DATE": "DATE", "PHRASE": "PHRASE"},
        "cardinality":   {"DATE": (0, 1), "PHRASE": (0, 1)},
    },

    # ── Translation ───────────────────────────────────────────────────────────
    # Used under NOTE, SNOTE, FILE, NAME, PLAC — union of all substructures.
    "TRAN": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {
            "LANG": "LANG", "MIME": "MIME", "FORM": "FORM",
            "GIVN": "GIVN", "SURN": "SURN", "NPFX": "NPFX",
            "NSFX": "NSFX", "NICK": "NICK", "SPFX": "SPFX",
        },
        "cardinality": {
            "LANG": (0, 1), "MIME": (0, 1), "FORM": (0, 1),
            "GIVN": (0, 1), "SURN": (0, 1), "NPFX": (0, 1),
            "NSFX": (0, 1), "NICK": (0, None), "SPFX": (0, 1),
        },
    },

    # ── AGE structure ─────────────────────────────────────────────────────────
    "AGE": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {"PHRASE": "PHRASE"},
        "cardinality":   {"PHRASE": (0, 1)},
    },

    # ── Role ──────────────────────────────────────────────────────────────────
    "ROLE": {
        "payload_type": PAYLOAD_ENUM,
        "enum_values": {
            "CHIL", "HUSB", "WIFE", "MOTH", "FATH", "SPOU",
            "CLERGY", "FRIEND", "GODP", "GODPARENT", "GUARDIAN",
            "MULTIPLE", "NGHBR", "OFFICIATOR", "PARENT",
            "PRIN", "WITN", "OTHER",
        },
        "substructures": {"PHRASE": "PHRASE"},
        "cardinality":   {"PHRASE": (0, 1)},
    },

    # ── Sort date ─────────────────────────────────────────────────────────────
    "SDATE": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {"TIME": "TIME", "PHRASE": "PHRASE"},
        "cardinality":   {"TIME": (0, 1), "PHRASE": (0, 1)},
    },

    # ── Pedigree linkage type ─────────────────────────────────────────────────
    "PEDI": {
        "payload_type": PAYLOAD_ENUM,
        "enum_values": {"ADOPTED", "BIRTH", "FOSTER", "SEALING", "OTHER"},
        "substructures": {"PHRASE": "PHRASE"},
        "cardinality":   {"PHRASE": (0, 1)},
    },

    # ── Adoption (dual role) ─────────────────────────────────────────────────
    # INDI.ADOP: individual adoption event — has TYPE, FAMC, full event subs.
    # FAMC.ADOP: adoption party enum (HUSB/WIFE/BOTH/NONE) — has PHRASE.
    # Union of both:
    "ADOP": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {**_EVENT_DETAIL_SUBS, "FAMC": "FAMC", "PHRASE": "PHRASE"},
        "cardinality":   {**_EVENT_DETAIL_CARD, "FAMC": (0, 1), "PHRASE": (0, 1)},
    },

    # ── Source TEXT ───────────────────────────────────────────────────────────
    "TEXT": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {"MIME": "MIME", "LANG": "LANG"},
        "cardinality":   {"MIME": (0, 1), "LANG": (0, 1)},
    },

    # ── Leaf text tags ────────────────────────────────────────────────────────
    "PHON":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "EMAIL": {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "FAX":   {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "WWW":   {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "MIME":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "LANG":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "UID":   {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "TIME":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "TYPE":  {"payload_type": PAYLOAD_TEXT, "substructures": {"PHRASE": "PHRASE"}, "cardinality": {"PHRASE": (0, 1)}},
    "PHRASE": {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "RESN":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "AGNC":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "CAUS":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "TEMP":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "AUTH":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "ABBR":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "PUBL":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "VERS":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "DEST":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "COPR":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "FORM":  {"payload_type": PAYLOAD_TEXT, "substructures": {"MEDI": "MEDI"}, "cardinality": {"MEDI": (0, 1)}},
    "LATI":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "LONG":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "GIVN":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "SURN":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "NPFX":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "NSFX":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "NICK":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "SPFX":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "PAGE":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "MEDI": {
        "payload_type": PAYLOAD_ENUM,
        "enum_values": {
            "AUDIO", "BOOK", "CARD", "ELECTRONIC", "FICHE", "FILM",
            "MAGAZINE", "MANUSCRIPT", "MAP", "NEWSPAPER", "PHOTO",
            "TOMBSTONE", "VIDEO", "OTHER",
        },
        "substructures": {"PHRASE": "PHRASE"},
        "cardinality":   {"PHRASE": (0, 1)},
    },
    "ADR1":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "ADR2":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "ADR3":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "CITY":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "STAE":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "POST":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "CTRY":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "TOP":   {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "LEFT":  {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "HEIGHT": {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},
    "WIDTH": {"payload_type": PAYLOAD_TEXT, "substructures": {}, "cardinality": {}},

    # ── Identifier structures ─────────────────────────────────────────────────
    "EXID": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {"TYPE": "TYPE"},
        "cardinality":   {"TYPE": (0, 1)},
    },
    "REFN": {
        "payload_type": PAYLOAD_TEXT,
        "substructures": {"TYPE": "TYPE"},
        "cardinality":   {"TYPE": (0, 1)},
    },
}

TOP_LEVEL_TAGS = {
    "HEAD",
    "TRLR",
    "INDI",
    "FAM",
    "OBJE",
    "REPO",
    "SNOTE",
    "SOUR",
    "SUBM",
}


def get_spec(key: Optional[str]) -> Dict[str, Any]:
    """Return a normalized specification entry.

    Args:
        key: GEDCOM tag or URI.

    Returns:
        Normalized specification mapping or an empty dict.
    """
    if not key:
        return {}

    tag = get_tag(key)
    return _CORE_RULES.get(tag, {})


def get_tag(key: str) -> str:
    """Resolve a tag from either a tag or a URI.

    Args:
        key: GEDCOM tag or URI.

    Returns:
        Resolved GEDCOM tag.
    """
    if key in _CORE_RULES or key in G7_TAG_TO_URI:
        return key.upper()
    for tag, uri in G7_TAG_TO_URI.items():
        if uri == key:
            return tag
    return key.upper()


def get_uri(key: str) -> Optional[str]:
    """Resolve a URI from either a tag or a URI.

    Args:
        key: GEDCOM tag or URI.

    Returns:
        URI or ``None`` if unknown.
    """
    if key.startswith("http://") or key.startswith("https://"):
        return key
    return get_uri_for_tag(key)


# Human-readable display labels for standard GEDCOM 7 tags.
# Falls back to the tag itself for anything not listed here.
_TAG_LABELS: Dict[str, str] = {
    "ABBR": "Abbreviation",      "ADDR": "Address",
    "ADOP": "Adoption",          "ADR1": "Address Line 1",
    "ADR2": "Address Line 2",    "ADR3": "Address Line 3",
    "AGE":  "Age",               "AGNC": "Agency",
    "ALIA": "Alias",             "ANCI": "Ancestor Interest",
    "ANUL": "Annulment",         "ASSO": "Association",
    "AUTH": "Author",
    "BAPL": "Baptism (LDS)",     "BAPM": "Baptism",
    "BARM": "Bar Mitzvah",       "BASM": "Bas Mitzvah",
    "BIRT": "Birth",             "BLES": "Blessing",
    "BURI": "Burial",
    "CALN": "Call Number",       "CAST": "Caste",
    "CAUS": "Cause",             "CENS": "Census",
    "CHAN": "Change",            "CHIL": "Child",
    "CHR":  "Christening",       "CHRA": "Adult Christening",
    "CITY": "City",              "CONF": "Confirmation",
    "CONL": "Confirmation (LDS)", "CONT": "Continuation",
    "COPR": "Copyright",         "CORP": "Corporate",
    "CREA": "Creation",          "CTRY": "Country",
    "DATA": "Data",              "DATE": "Date",
    "DEAT": "Death",             "DESI": "Descendant Interest",
    "DEST": "Destination",       "DIV":  "Divorce",
    "DIVF": "Divorce Filed",     "DSCR": "Description",
    "EDUC": "Education",         "EMAIL": "Email",
    "EMIG": "Emigration",        "ENDL": "Endowment (LDS)",
    "ENGA": "Engagement",        "EVEN": "Event",
    "EXID": "External Identifier",
    "FAM":  "Family",            "FAMC": "Family (child)",
    "FAMF": "Family File",       "FAMS": "Family (spouse)",
    "FAX":  "Fax",               "FCOM": "First Communion",
    "FILE": "File",              "FORM": "Format",
    "GEDC": "GEDCOM",            "GIVN": "Given Name",
    "GRAD": "Graduation",
    "HEAD": "Header",            "HUSB": "Husband",
    "IDNO": "ID Number",         "IMMI": "Immigration",
    "INDI": "Individual",        "INIL": "Initiatory (LDS)",
    "LANG": "Language",          "LATI": "Latitude",
    "LONG": "Longitude",
    "MAP":  "Map",               "MARB": "Marriage Banns",
    "MARC": "Marriage Contract", "MARL": "Marriage License",
    "MARR": "Marriage",          "MARS": "Marriage Settlement",
    "MEDI": "Media",             "MIME": "MIME Type",
    "NAME": "Name",              "NATI": "Nationality",
    "NATU": "Naturalization",    "NICK": "Nickname",
    "NO":   "Did Not Happen",    "NOTE": "Note",
    "NPFX": "Name Prefix",       "NSFX": "Name Suffix",
    "OBJE": "Object",            "OCCU": "Occupation",
    "ORDI": "Ordinance",         "ORDN": "Ordination",
    "PAGE": "Page",              "PEDI": "Pedigree",
    "PHON": "Phone",             "PLAC": "Place",
    "POST": "Postal Code",       "PROB": "Probate",
    "PUBL": "Publication",       "QUAY": "Quality",
    "REFN": "Reference Number",  "RELI": "Religion",
    "REPO": "Repository",        "RESI": "Residence",
    "RESN": "Restriction",       "RETI": "Retirement",
    "ROLE": "Role",
    "SCHMA": "Schema",           "SEX":  "Sex",
    "SLGC": "Sealing — Child (LDS)", "SLGS": "Sealing — Spouse (LDS)",
    "SNOTE": "Shared Note",      "SOUR": "Source",
    "SPFX": "Surname Prefix",    "SSN":  "Social Security Number",
    "STAE": "State",             "STAT": "Status",
    "SUBM": "Submitter",         "SURN": "Surname",
    "TAG":  "Tag",               "TEMP": "Temple",
    "TEXT": "Text",              "TIME": "Time",
    "TITL": "Title",             "TRAN": "Translation",
    "TRLR": "Trailer",           "TYPE": "Type",
    "UID":  "Unique Identifier", "VERS": "Version",
    "WIFE": "Wife",              "WILL": "Will",
    "WWW":  "Website",
}


def get_label(key: Optional[str]) -> str:
    """Return a human-readable display label for a GEDCOM tag or URI.

    Args:
        key: GEDCOM tag (e.g. ``"BIRT"``) or URI.

    Returns:
        Human-readable label such as ``"Birth"``, or the tag itself
        if no label is registered.
    """
    if not key:
        return "Unknown"
    tag = get_tag(key)
    return _TAG_LABELS.get(tag.upper(), tag)


def top_level_tags() -> List[str]:
    """Return the known top-level record tags."""
    return sorted(TOP_LEVEL_TAGS)


def allowed_child_map(parent_key: Optional[str]) -> Dict[str, str]:
    """Return the allowed child map for a parent.

    Args:
        parent_key: Parent tag or URI.

    Returns:
        Mapping of child tag to child identifier.
    """
    if not parent_key:
        return {tag: tag for tag in TOP_LEVEL_TAGS}
    spec = get_spec(parent_key)
    subs = spec.get("substructures", {})
    if not isinstance(subs, dict):
        return {}
    return {str(tag).upper(): str(value) for tag, value in subs.items()}


def allowed_child_tags(parent_key: Optional[str]) -> List[str]:
    """Return the allowed child tags for a parent.

    Args:
        parent_key: Parent tag or URI.

    Returns:
        Sorted child tags.
    """
    return sorted(allowed_child_map(parent_key))


def is_allowed_child(parent_key: Optional[str], child_tag: str) -> bool:
    """Return whether a child tag is legal under a parent.

    Args:
        parent_key: Parent tag or URI.
        child_tag: Candidate child tag.

    Returns:
        ``True`` if the child is legal, else ``False``.
    """
    normalized_child = child_tag.upper()

    if normalized_child in {CONC, CONT}:
        return True

    # Extension tags (underscore-prefixed) are allowed under any parent;
    # their declaration is validated separately via validate_extension_usage().
    if child_tag.startswith("_"):
        return True

    if parent_key is None:
        return normalized_child in TOP_LEVEL_TAGS

    return normalized_child in allowed_child_map(parent_key)


def get_cardinality(parent_key: Optional[str], child_tag: str) -> Optional[tuple[int, Optional[int]]]:
    """Return cardinality for a child under a parent.

    Args:
        parent_key: Parent tag or URI.
        child_tag: Child GEDCOM tag.

    Returns:
        ``(min_count, max_count)`` or ``None`` if unspecified.
    """
    if parent_key is None:
        return None
    spec = get_spec(parent_key)
    card = spec.get("cardinality", {})
    if not isinstance(card, dict):
        return None
    value = card.get(child_tag.upper())
    if value is None:
        return None
    min_count, max_count = value
    return int(min_count), (None if max_count is None else int(max_count))


def get_payload_type(key: Optional[str]) -> Optional[str]:
    """Return the normalized payload type for a structure.

    Args:
        key: GEDCOM tag or URI.

    Returns:
        Payload type or ``None``.
    """
    spec = get_spec(key)
    payload_type = spec.get("payload_type")
    return str(payload_type) if payload_type else None


def get_enum_values(key: Optional[str]) -> Optional[set[str]]:
    """Return valid enumeration values for a structure.

    Args:
        key: GEDCOM tag or URI.

    Returns:
        Set of valid values or ``None``.
    """
    spec = get_spec(key)
    values = spec.get("enum_values")
    if values is None:
        return None
    return {str(value) for value in values}


def get_context_enum_values(tag: str, parent_tag: Optional[str]) -> Optional[frozenset]:
    """Return context-specific enumeration values when the same tag has different
    allowed values depending on its parent structure.

    Args:
        tag: GEDCOM tag.
        parent_tag: Tag of the parent structure, or ``None`` for top-level.

    Returns:
        Frozenset of valid values if a context-specific rule exists, otherwise
        ``None`` (meaning fall through to the general enum check).
    """
    if parent_tag is None:
        return None
    return _CONTEXT_ENUM_RULES.get((tag.upper(), parent_tag.upper()))


def register_extension_tag(tag: str, uri: str) -> None:
    """Register an extension tag from ``HEAD.SCHMA.TAG``.

    Args:
        tag: Extension tag such as ``_FOO``.
        uri: Corresponding extension URI.
    """
    register_tag_uri(tag, uri, overwrite=True)
    _CORE_RULES.setdefault(
        tag.upper(),
        {
            "payload_type": PAYLOAD_TEXT,
            "substructures": {},
            "cardinality": {},
        },
    )


__all__ = [
    "HEAD",
    "TRLR",
    "GEDC",
    "SCHMA",
    "CONC",
    "CONT",
    "PAYLOAD_TEXT",
    "PAYLOAD_POINTER",
    "PAYLOAD_NONE",
    "PAYLOAD_ENUM",
    "FAMC_STAT_ENUM",
    "TOP_LEVEL_TAGS",
    "get_spec",
    "get_tag",
    "get_uri",
    "get_label",
    "top_level_tags",
    "allowed_child_map",
    "allowed_child_tags",
    "is_allowed_child",
    "get_cardinality",
    "get_payload_type",
    "get_enum_values",
    "get_context_enum_values",
    "register_extension_tag",
]
