"""
======================================================================
 Project: gedcomtools
 File:    gedcom7/g7interop.py
 Author:  David J. Cartwright
 Purpose: GEDCOM 7 tag/URI mapping and interoperability helpers.

 Created: 2026-03-01
 Updated:
   - 2026-03-15: exported via package __init__; no logic changes
======================================================================

This module provides normalized GEDCOM 7 tag and URI lookup helpers.

The core mapping is a flat ``G7_TAG_TO_URI`` dict. This module adds:

- normalized lookup helpers
- reverse lookup (URI → tag)
- dynamic extension tag registration
- convenience exports for the GEDCOM 7 parser and validator

The docstrings are written in Google style so they render well with
Sphinx Napoleon.
"""

from __future__ import annotations

import warnings
from typing import Dict, Optional


G7_TAG_TO_URI: Dict[str, str] = {'ABBR': 'https://gedcom.io/terms/v7/ABBR',
 'ADDR': 'https://gedcom.io/terms/v7/ADDR',
 'ADOP': 'https://gedcom.io/terms/v7/ADOP',
 'ADOP-FAMC': 'https://gedcom.io/terms/v7/ADOP-FAMC',
 'ADR1': 'https://gedcom.io/terms/v7/ADR1',
 'ADR2': 'https://gedcom.io/terms/v7/ADR2',
 'ADR3': 'https://gedcom.io/terms/v7/ADR3',
 'AGE': 'https://gedcom.io/terms/v7/AGE',
 'AGNC': 'https://gedcom.io/terms/v7/AGNC',
 'ALIA': 'https://gedcom.io/terms/v7/ALIA',
 'ANCI': 'https://gedcom.io/terms/v7/ANCI',
 'ANUL': 'https://gedcom.io/terms/v7/ANUL',
 'ASSO': 'https://gedcom.io/terms/v7/ASSO',
 'AUTH': 'https://gedcom.io/terms/v7/AUTH',
 'BAPL': 'https://gedcom.io/terms/v7/BAPL',
 'BAPM': 'https://gedcom.io/terms/v7/BAPM',
 'BARM': 'https://gedcom.io/terms/v7/BARM',
 'BASM': 'https://gedcom.io/terms/v7/BASM',
 'BIRT': 'https://gedcom.io/terms/v7/BIRT',
 'BLES': 'https://gedcom.io/terms/v7/BLES',
 'BURI': 'https://gedcom.io/terms/v7/BURI',
 'CALN': 'https://gedcom.io/terms/v7/CALN',
 'CAST': 'https://gedcom.io/terms/v7/CAST',
 'CAUS': 'https://gedcom.io/terms/v7/CAUS',
 'CENS': 'https://gedcom.io/terms/v7/CENS',
 'CHAN': 'https://gedcom.io/terms/v7/CHAN',
 'CHIL': 'https://gedcom.io/terms/v7/CHIL',
 'CHR': 'https://gedcom.io/terms/v7/CHR',
 'CHRA': 'https://gedcom.io/terms/v7/CHRA',
 'CITY': 'https://gedcom.io/terms/v7/CITY',
 'CONF': 'https://gedcom.io/terms/v7/CONF',
 'CONL': 'https://gedcom.io/terms/v7/CONL',
 'CONT': 'https://gedcom.io/terms/v7/CONT',
 'COPR': 'https://gedcom.io/terms/v7/COPR',
 'CORP': 'https://gedcom.io/terms/v7/CORP',
 'CREA': 'https://gedcom.io/terms/v7/CREA',
 'CREM': 'https://gedcom.io/terms/v7/CREM',
 'CROP': 'https://gedcom.io/terms/v7/CROP',
 'CTRY': 'https://gedcom.io/terms/v7/CTRY',
 'DATA': 'https://gedcom.io/terms/v7/DATA',
 'DATA-EVEN': 'https://gedcom.io/terms/v7/DATA-EVEN',
 'DATA-EVEN-DATE': 'https://gedcom.io/terms/v7/DATA-EVEN-DATE',
 'DATE': 'https://gedcom.io/terms/v7/DATE',
 'DATE-exact': 'https://gedcom.io/terms/v7/DATE-exact',
 'DEAT': 'https://gedcom.io/terms/v7/DEAT',
 'DESI': 'https://gedcom.io/terms/v7/DESI',
 'DEST': 'https://gedcom.io/terms/v7/DEST',
 'DIV': 'https://gedcom.io/terms/v7/DIV',
 'DIVF': 'https://gedcom.io/terms/v7/DIVF',
 'DSCR': 'https://gedcom.io/terms/v7/DSCR',
 'EDUC': 'https://gedcom.io/terms/v7/EDUC',
 'EMAIL': 'https://gedcom.io/terms/v7/EMAIL',
 'EMIG': 'https://gedcom.io/terms/v7/EMIG',
 'ENDL': 'https://gedcom.io/terms/v7/ENDL',
 'ENGA': 'https://gedcom.io/terms/v7/ENGA',
 'EVEN': 'https://gedcom.io/terms/v7/EVEN',
 'EXID': 'https://gedcom.io/terms/v7/EXID',
 'EXID-TYPE': 'https://gedcom.io/terms/v7/EXID-TYPE',
 'FACT': 'https://gedcom.io/terms/v7/FACT',
 'FAM': 'https://gedcom.io/terms/v7/FAM',
 'FAM-CENS': 'https://gedcom.io/terms/v7/FAM-CENS',
 'FAM-EVEN': 'https://gedcom.io/terms/v7/FAM-EVEN',
 'FAM-FACT': 'https://gedcom.io/terms/v7/FAM-FACT',
 'FAM-HUSB': 'https://gedcom.io/terms/v7/FAM-HUSB',
 'FAM-NCHI': 'https://gedcom.io/terms/v7/FAM-NCHI',
 'FAM-RESI': 'https://gedcom.io/terms/v7/FAM-RESI',
 'FAM-WIFE': 'https://gedcom.io/terms/v7/FAM-WIFE',
 'FAMC': 'https://gedcom.io/terms/v7/FAMC',
 'FAMC-ADOP': 'https://gedcom.io/terms/v7/FAMC-ADOP',
 'FAMC-STAT': 'https://gedcom.io/terms/v7/FAMC-STAT',
 'FAMS': 'https://gedcom.io/terms/v7/FAMS',
 'FAX': 'https://gedcom.io/terms/v7/FAX',
 'FCOM': 'https://gedcom.io/terms/v7/FCOM',
 'FILE': 'https://gedcom.io/terms/v7/FILE',
 'FILE-TRAN': 'https://gedcom.io/terms/v7/FILE-TRAN',
 'FORM': 'https://gedcom.io/terms/v7/FORM',
 'GEDC': 'https://gedcom.io/terms/v7/GEDC',
 'GEDC-VERS': 'https://gedcom.io/terms/v7/GEDC-VERS',
 'GIVN': 'https://gedcom.io/terms/v7/GIVN',
 'GRAD': 'https://gedcom.io/terms/v7/GRAD',
 'HEAD': 'https://gedcom.io/terms/v7/HEAD',
 'HEAD-DATE': 'https://gedcom.io/terms/v7/HEAD-DATE',
 'HEAD-LANG': 'https://gedcom.io/terms/v7/HEAD-LANG',
 'HEAD-PLAC': 'https://gedcom.io/terms/v7/HEAD-PLAC',
 'HEAD-PLAC-FORM': 'https://gedcom.io/terms/v7/HEAD-PLAC-FORM',
 'HEAD-SOUR': 'https://gedcom.io/terms/v7/HEAD-SOUR',
 'HEAD-SOUR-DATA': 'https://gedcom.io/terms/v7/HEAD-SOUR-DATA',
 'HEIGHT': 'https://gedcom.io/terms/v7/HEIGHT',
 'HUSB': 'https://gedcom.io/terms/v7/HUSB',
 'IDNO': 'https://gedcom.io/terms/v7/IDNO',
 'IMMI': 'https://gedcom.io/terms/v7/IMMI',
 'INDI': 'https://gedcom.io/terms/v7/INDI',
 'INDI-CENS': 'https://gedcom.io/terms/v7/INDI-CENS',
 'INDI-EVEN': 'https://gedcom.io/terms/v7/INDI-EVEN',
 'INDI-FACT': 'https://gedcom.io/terms/v7/INDI-FACT',
 'INDI-FAMC': 'https://gedcom.io/terms/v7/INDI-FAMC',
 'INDI-NAME': 'https://gedcom.io/terms/v7/INDI-NAME',
 'INDI-NCHI': 'https://gedcom.io/terms/v7/INDI-NCHI',
 'INDI-RELI': 'https://gedcom.io/terms/v7/INDI-RELI',
 'INDI-RESI': 'https://gedcom.io/terms/v7/INDI-RESI',
 'INDI-TITL': 'https://gedcom.io/terms/v7/INDI-TITL',
 'INIL': 'https://gedcom.io/terms/v7/INIL',
 'LANG': 'https://gedcom.io/terms/v7/LANG',
 'LATI': 'https://gedcom.io/terms/v7/LATI',
 'LEFT': 'https://gedcom.io/terms/v7/LEFT',
 'LONG': 'https://gedcom.io/terms/v7/LONG',
 'MAP': 'https://gedcom.io/terms/v7/MAP',
 'MARB': 'https://gedcom.io/terms/v7/MARB',
 'MARC': 'https://gedcom.io/terms/v7/MARC',
 'MARL': 'https://gedcom.io/terms/v7/MARL',
 'MARR': 'https://gedcom.io/terms/v7/MARR',
 'MARS': 'https://gedcom.io/terms/v7/MARS',
 'MEDI': 'https://gedcom.io/terms/v7/MEDI',
 'MIME': 'https://gedcom.io/terms/v7/MIME',
 'NAME': 'https://gedcom.io/terms/v7/NAME',
 'NAME-TRAN': 'https://gedcom.io/terms/v7/NAME-TRAN',
 'NAME-TYPE': 'https://gedcom.io/terms/v7/NAME-TYPE',
 'NATI': 'https://gedcom.io/terms/v7/NATI',
 'NATU': 'https://gedcom.io/terms/v7/NATU',
 'NCHI': 'https://gedcom.io/terms/v7/NCHI',
 'NICK': 'https://gedcom.io/terms/v7/NICK',
 'NMR': 'https://gedcom.io/terms/v7/NMR',
 'NO': 'https://gedcom.io/terms/v7/NO',
 'NO-DATE': 'https://gedcom.io/terms/v7/NO-DATE',
 'NOTE': 'https://gedcom.io/terms/v7/NOTE',
 'NOTE-TRAN': 'https://gedcom.io/terms/v7/NOTE-TRAN',
 'NPFX': 'https://gedcom.io/terms/v7/NPFX',
 'NSFX': 'https://gedcom.io/terms/v7/NSFX',
 'OBJE': 'https://gedcom.io/terms/v7/OBJE',
 'OCCU': 'https://gedcom.io/terms/v7/OCCU',
 'ORDN': 'https://gedcom.io/terms/v7/ORDN',
 'PAGE': 'https://gedcom.io/terms/v7/PAGE',
 'PEDI': 'https://gedcom.io/terms/v7/PEDI',
 'PHON': 'https://gedcom.io/terms/v7/PHON',
 'PHRASE': 'https://gedcom.io/terms/v7/PHRASE',
 'PLAC': 'https://gedcom.io/terms/v7/PLAC',
 'PLAC-FORM': 'https://gedcom.io/terms/v7/PLAC-FORM',
 'PLAC-TRAN': 'https://gedcom.io/terms/v7/PLAC-TRAN',
 'POST': 'https://gedcom.io/terms/v7/POST',
 'PROB': 'https://gedcom.io/terms/v7/PROB',
 'PROP': 'https://gedcom.io/terms/v7/PROP',
 'PUBL': 'https://gedcom.io/terms/v7/PUBL',
 'QUAY': 'https://gedcom.io/terms/v7/QUAY',
 'REFN': 'https://gedcom.io/terms/v7/REFN',
 'RELI': 'https://gedcom.io/terms/v7/RELI',
 'REPO': 'https://gedcom.io/terms/v7/REPO',
 'RESI': 'https://gedcom.io/terms/v7/RESI',
 'RESN': 'https://gedcom.io/terms/v7/RESN',
 'RETI': 'https://gedcom.io/terms/v7/RETI',
 'ROLE': 'https://gedcom.io/terms/v7/ROLE',
 'SCHMA': 'https://gedcom.io/terms/v7/SCHMA',
 'SDATE': 'https://gedcom.io/terms/v7/SDATE',
 'SEX': 'https://gedcom.io/terms/v7/SEX',
 'SLGC': 'https://gedcom.io/terms/v7/SLGC',
 'SLGS': 'https://gedcom.io/terms/v7/SLGS',
 'SNOTE': 'https://gedcom.io/terms/v7/SNOTE',
 'SOUR': 'https://gedcom.io/terms/v7/SOUR',
 'SOUR-DATA': 'https://gedcom.io/terms/v7/SOUR-DATA',
 'SOUR-EVEN': 'https://gedcom.io/terms/v7/SOUR-EVEN',
 'SPFX': 'https://gedcom.io/terms/v7/SPFX',
 'SSN': 'https://gedcom.io/terms/v7/SSN',
 'STAE': 'https://gedcom.io/terms/v7/STAE',
 'STAT': 'https://gedcom.io/terms/v7/STAT',
 'SUBM': 'https://gedcom.io/terms/v7/SUBM',
 'SUBM-LANG': 'https://gedcom.io/terms/v7/SUBM-LANG',
 'SURN': 'https://gedcom.io/terms/v7/SURN',
 'TAG': 'https://gedcom.io/terms/v7/TAG',
 'TEMP': 'https://gedcom.io/terms/v7/TEMP',
 'TEXT': 'https://gedcom.io/terms/v7/TEXT',
 'TIME': 'https://gedcom.io/terms/v7/TIME',
 'TITL': 'https://gedcom.io/terms/v7/TITL',
 'TOP': 'https://gedcom.io/terms/v7/TOP',
 'TRAN': 'https://gedcom.io/terms/v7/TRAN',
 'TRLR': 'https://gedcom.io/terms/v7/TRLR',
 'TYPE': 'https://gedcom.io/terms/v7/TYPE',
 'UID': 'https://gedcom.io/terms/v7/UID',
 'VERS': 'https://gedcom.io/terms/v7/VERS',
 'WIDTH': 'https://gedcom.io/terms/v7/WIDTH',
 'WIFE': 'https://gedcom.io/terms/v7/WIFE',
 'WILL': 'https://gedcom.io/terms/v7/WILL',
 'WWW': 'https://gedcom.io/terms/v7/WWW',
 'enumset-ADOP': 'https://gedcom.io/terms/v7/enumset-ADOP',
 'enumset-EVEN': 'https://gedcom.io/terms/v7/enumset-EVEN',
 'enumset-EVENATTR': 'https://gedcom.io/terms/v7/enumset-EVENATTR',
 'enumset-FAMC-STAT': 'https://gedcom.io/terms/v7/enumset-FAMC-STAT',
 'enumset-MEDI': 'https://gedcom.io/terms/v7/enumset-MEDI',
 'enumset-NAME-TYPE': 'https://gedcom.io/terms/v7/enumset-NAME-TYPE',
 'enumset-PEDI': 'https://gedcom.io/terms/v7/enumset-PEDI',
 'enumset-QUAY': 'https://gedcom.io/terms/v7/enumset-QUAY',
 'enumset-RESN': 'https://gedcom.io/terms/v7/enumset-RESN',
 'enumset-ROLE': 'https://gedcom.io/terms/v7/enumset-ROLE',
 'enumset-SEX': 'https://gedcom.io/terms/v7/enumset-SEX',
 'ord-STAT': 'https://gedcom.io/terms/v7/ord-STAT',
 'record-FAM': 'https://gedcom.io/terms/v7/record-FAM',
 'record-INDI': 'https://gedcom.io/terms/v7/record-INDI',
 'record-OBJE': 'https://gedcom.io/terms/v7/record-OBJE',
 'record-REPO': 'https://gedcom.io/terms/v7/record-REPO',
 'record-SNOTE': 'https://gedcom.io/terms/v7/record-SNOTE',
 'record-SOUR': 'https://gedcom.io/terms/v7/record-SOUR',
 'record-SUBM': 'https://gedcom.io/terms/v7/record-SUBM'}

G7_URI_TO_TAG: Dict[str, str] = {}
for _tag, _uri in G7_TAG_TO_URI.items():
    G7_URI_TO_TAG.setdefault(_uri, _tag)


def normalize_tag(tag: str) -> str:
    """Normalize a GEDCOM tag.

    Args:
        tag: Raw GEDCOM tag value.

    Returns:
        Uppercase, stripped GEDCOM tag.

    Raises:
        TypeError: If ``tag`` is not a string.
    """
    if not isinstance(tag, str):
        raise TypeError(f"tag must be a string, got {type(tag)!r}")
    return tag.strip().upper()


def normalize_uri(uri: str) -> str:
    """Normalize a GEDCOM URI.

    Args:
        uri: Raw GEDCOM URI.

    Returns:
        Stripped GEDCOM URI.

    Raises:
        TypeError: If ``uri`` is not a string.
    """
    if not isinstance(uri, str):
        raise TypeError(f"uri must be a string, got {type(uri)!r}")
    return uri.strip()


def get_uri_for_tag(tag: str) -> Optional[str]:
    """Return the canonical GEDCOM 7 URI for a tag.

    Args:
        tag: GEDCOM tag.

    Returns:
        Matching URI or ``None`` if unknown.
    """
    return G7_TAG_TO_URI.get(normalize_tag(tag))


def get_tag_for_uri(uri: str) -> Optional[str]:
    """Return the canonical GEDCOM tag for a URI.

    Args:
        uri: GEDCOM URI.

    Returns:
        Matching tag or ``None`` if unknown.
    """
    return G7_URI_TO_TAG.get(normalize_uri(uri))


def is_known_tag(tag: str) -> bool:
    """Return whether a GEDCOM tag is known.

    Args:
        tag: GEDCOM tag.

    Returns:
        ``True`` if known, else ``False``.
    """
    return get_uri_for_tag(tag) is not None


def is_known_uri(uri: str) -> bool:
    """Return whether a GEDCOM URI is known.

    Args:
        uri: GEDCOM URI.

    Returns:
        ``True`` if known, else ``False``.
    """
    return get_tag_for_uri(uri) is not None


def register_tag_uri(tag: str, uri: str, *, overwrite: bool = False) -> None:
    """Register a GEDCOM tag/URI mapping.

    This is mainly used for extension tags declared in ``HEAD.SCHMA.TAG``.

    Args:
        tag: GEDCOM tag such as ``_FOO``.
        uri: GEDCOM URI for the extension tag.
        overwrite: Whether to overwrite an existing mapping.

    Raises:
        ValueError: If a conflicting mapping exists and ``overwrite`` is false.
    """
    normalized_tag = normalize_tag(tag)
    normalized_uri = normalize_uri(uri)

    existing_uri = G7_TAG_TO_URI.get(normalized_tag)
    if existing_uri is not None and existing_uri != normalized_uri and not overwrite:
        raise ValueError(
            f"Tag {normalized_tag!r} is already mapped to {existing_uri!r}."
        )

    existing_tag = G7_URI_TO_TAG.get(normalized_uri)
    if existing_tag is not None and existing_tag != normalized_tag:
        if not overwrite:
            raise ValueError(
                f"URI {normalized_uri!r} is already mapped to {existing_tag!r}."
            )
        # Warn only when two *standard* (non-extension) tags collide.
        # Extension tags (underscore-prefixed) routinely claim standard URIs
        # as declared in HEAD.SCHMA.TAG; that is intentional and expected.
        neither_is_extension = (
            not normalized_tag.startswith("_")
            and not existing_tag.startswith("_")
        )
        if neither_is_extension:
            warnings.warn(
                f"URI {normalized_uri!r} was mapped to standard tag "
                f"{existing_tag!r}; overwriting with {normalized_tag!r}. "
                "This may make get_tag_for_uri() inconsistent with "
                "get_uri_for_tag().",
                UserWarning,
                stacklevel=2,
            )

    G7_TAG_TO_URI[normalized_tag] = normalized_uri
    G7_URI_TO_TAG[normalized_uri] = normalized_tag


__all__ = [
    "G7_TAG_TO_URI",
    "G7_URI_TO_TAG",
    "normalize_tag",
    "normalize_uri",
    "get_uri_for_tag",
    "get_tag_for_uri",
    "is_known_tag",
    "is_known_uri",
    "register_tag_uri",
]
