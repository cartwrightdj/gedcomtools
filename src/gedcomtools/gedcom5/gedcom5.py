# -*- coding: utf-8 -*-
"""
======================================================================
 Project: gedcomtools
 File:    gedcom/gedcom5.py
 Author:  David J. Cartwright
 Purpose: High-level GEDCOM 5.x facade that mirrors the Gedcom7 API.

          Wraps Gedcom5x internally.  All plain accessors return the
          raw Element / typed record objects so callers can read and
          edit them directly.  The ``*_detail`` / ``*_details``
          variants return the high-level Detail dataclasses only when
          explicitly requested.

          Plain (raw record) access:
              g = Gedcom5("file.ged")
              rec = g.get_individual("@I1@")   # IndividualRecord
              rec.value = "Doe, John"           # edit in place

          Detail (model snapshot) access:
              d = g.get_individual_detail("@I1@")  # IndividualDetail
              print(d.full_name, d.birth_year)

 Created: 2026-03-16
 Updated: 2026-03-24 — added to_gedcom7() and to_gedcomx() conversion helpers
 Updated: 2026-03-31 — added _rel_cache; get_parents/get_children_of/get_spouses
                        now cache results and invalidate on loadfile()
 Updated: 2026-03-31 — URL support in __init__ and load_url(); .ged extension check
 Updated: 2026-04-01 — use RelationshipCacheMixin; replace _rel_cache
                        direct access with _cache_get/_cache_set/_cache_clear
======================================================================
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union
import io
import urllib.error
import urllib.parse
import urllib.request


def _is_url(s: str) -> bool:
    """Return True if *s* looks like an HTTP/HTTPS URL."""
    return s.startswith(("http://", "https://"))


def _check_ged_url(url: str) -> None:
    """Raise :class:`ValueError` if the URL path does not end in ``.ged``."""
    path = urllib.parse.urlparse(url).path
    if Path(path).suffix.lower() != ".ged":
        raise ValueError(
            f"URL does not point to a .ged file: {url!r}"
        )

from .elements import (
    FamilyRecord,
    IndividualRecord,
    ObjectRecord,
    RepositoryRecord,
    SourceRecord,
    SubmitterRecord,
)
from .parser import Gedcom5x, _normalize_xref
from .models5 import (
    family_detail_from_g5,
    individual_detail_from_g5,
    media_detail_from_g5,
    repository_detail_from_g5,
    source_detail_from_g5,
    submitter_detail_from_g5,
)
from ..gedcom7.models import (
    FamilyDetail,
    IndividualDetail,
    MediaDetail,
    RepositoryDetail,
    SharedNoteDetail,
    SourceDetail,
    SubmitterDetail,
)
from ..rel_cache import RelationshipCacheMixin


class Gedcom5(RelationshipCacheMixin):
    """Parse GEDCOM 5.x files and expose a :class:`Gedcom7`-compatible API.

    **Two access tiers:**

    * Plain accessors (``individuals()``, ``get_individual(xref)``, etc.)
      return the raw :class:`~gedcomtools.gedcom.elements.Element`-based
      record objects.  These are mutable — changes made to them are
      reflected in the in-memory tree.

    * Detail accessors (``individual_details()``,
      ``get_individual_detail(xref)``, etc.) return a read-only snapshot
      as one of the shared model dataclasses (e.g.
      :class:`~gedcomtools.gedcom7.models.IndividualDetail`).  Use these
      when you only need clean, named-field access and do not intend to
      write back.
    """

    def __init__(self, filepath: Optional[Union[str, Path]] = None) -> None:
        """Initialise the parser.

        Args:
            filepath: Optional path to a GEDCOM 5.x file **or** HTTP/HTTPS
                URL to load immediately.  URLs must end in ``.ged``.
        """
        self._parser = Gedcom5x()
        self._rel_cache: dict[str, list] = {}

        if filepath is not None:
            s = str(filepath)
            if _is_url(s):
                self.filepath: Optional[Path] = None
                self.load_url(s)
            else:
                self.filepath = Path(s)
                self.loadfile(self.filepath)
        else:
            self.filepath = None

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def loadfile(self, path: Union[str, Path], strict: bool = False) -> None:
        """Load a GEDCOM 5.x file.

        Args:
            path: Path to the GEDCOM file.
            strict: When ``True``, raises on the first parse error rather
                than tolerating minor deviations.
        """
        self.filepath = Path(path)
        self._cache_clear()
        self._parser.parse_file(str(self.filepath), strict=strict)

    def load_url(self, url: str) -> None:
        """Download and parse a GEDCOM 5.x file from an HTTP/HTTPS URL.

        The response body is decoded as UTF-8.  Use :meth:`loadfile` for
        local files.

        Args:
            url: HTTP or HTTPS URL pointing to a ``.ged`` file.

        Raises:
            ValueError:             If the URL does not end in ``.ged``.
            urllib.error.URLError:  If the URL cannot be reached.
            urllib.error.HTTPError: If the server returns an error status.
        """
        _check_ged_url(url)
        try:
            with urllib.request.urlopen(url) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            raise urllib.error.HTTPError(
                exc.url, exc.code,
                f"HTTP {exc.code} fetching GEDCOM from {url}: {exc.reason}",
                exc.headers, exc.fp,
            ) from exc
        except urllib.error.URLError as exc:
            raise urllib.error.URLError(
                f"Cannot fetch GEDCOM from {url}: {exc.reason}"
            ) from exc
        self._cache_clear()
        self._parser.parse(io.BytesIO(raw))

    # ------------------------------------------------------------------
    # Version detection
    # ------------------------------------------------------------------

    def detect_gedcom_version(self) -> Optional[str]:
        """Return the GEDCOM version declared in the file header.

        Reads ``HEAD > GEDC > VERS`` when present; falls back to
        ``HEAD > VERS``; returns ``"5.5"`` as a safe default.

        Returns:
            Version string such as ``"5.5.1"`` or ``"5.5"``.
        """
        for el in self._parser.get_root_child_elements():
            if el.tag != "HEAD":
                continue
            gedc = el.sub_record("GEDC")
            if gedc:
                vers = gedc.sub_record("VERS")
                if vers and vers.value:
                    return vers.value.strip() or None
            vers = el.sub_record("VERS")
            if vers and vers.value:
                return vers.value.strip() or None
        return "5.5"

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self):
        """Validate the loaded file against the GEDCOM 5.5.1 specification.

        Returns:
            A list of :class:`~gedcomtools.gedcom7.validator.ValidationIssue`
            instances, each with ``severity`` (``"error"`` or ``"warning"``),
            ``code``, ``message``, ``tag``, and ``line_num`` fields.
        """
        from .validator5 import Gedcom5Validator
        return Gedcom5Validator(self._parser).validate()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _lookup(self, xref: str):
        """Return the raw Element for *xref*, or ``None``."""
        return self._parser.get_element_dictionary().get(_normalize_xref(xref))

    # ------------------------------------------------------------------
    # Raw record accessors
    # ------------------------------------------------------------------

    def individuals(self) -> List[IndividualRecord]:
        """Return every INDI record as a raw :class:`IndividualRecord`."""
        return list(self._parser.individuals)

    def get_individual(self, xref: str) -> Optional[IndividualRecord]:
        """Return the raw :class:`IndividualRecord` for *xref*, or ``None``."""
        el = self._lookup(xref)
        return el if el is not None and el.tag == "INDI" else None

    def families(self) -> List[FamilyRecord]:
        """Return every FAM record as a raw :class:`FamilyRecord`."""
        return list(self._parser.families)

    def get_family(self, xref: str) -> Optional[FamilyRecord]:
        """Return the raw :class:`FamilyRecord` for *xref*, or ``None``."""
        el = self._lookup(xref)
        return el if el is not None and el.tag == "FAM" else None

    def sources(self) -> List[SourceRecord]:
        """Return every SOUR record as a raw :class:`SourceRecord`."""
        return list(self._parser.sources)

    def get_source(self, xref: str) -> Optional[SourceRecord]:
        """Return the raw :class:`SourceRecord` for *xref*, or ``None``."""
        el = self._lookup(xref)
        return el if el is not None and el.tag == "SOUR" else None

    def repositories(self) -> List[RepositoryRecord]:
        """Return every REPO record as a raw :class:`RepositoryRecord`."""
        return list(self._parser.repositories)

    def get_repository(self, xref: str) -> Optional[RepositoryRecord]:
        """Return the raw :class:`RepositoryRecord` for *xref*, or ``None``."""
        el = self._lookup(xref)
        return el if el is not None and el.tag == "REPO" else None

    def media_objects(self) -> List[ObjectRecord]:
        """Return every OBJE record as a raw :class:`ObjectRecord`."""
        return list(self._parser.objects)

    def get_media(self, xref: str) -> Optional[ObjectRecord]:
        """Return the raw :class:`ObjectRecord` for *xref*, or ``None``."""
        el = self._lookup(xref)
        return el if el is not None and el.tag == "OBJE" else None

    def submitters(self) -> List[SubmitterRecord]:
        """Return every SUBM record as a raw :class:`SubmitterRecord`."""
        return list(self._parser.submitters)

    def get_submitter(self, xref: str) -> Optional[SubmitterRecord]:
        """Return the raw :class:`SubmitterRecord` for *xref*, or ``None``."""
        el = self._lookup(xref)
        return el if el is not None and el.tag == "SUBM" else None

    # ------------------------------------------------------------------
    # Detail model accessors  (explicit snapshot; not editable)
    # ------------------------------------------------------------------

    def individual_details(self) -> List[IndividualDetail]:
        """Return :class:`IndividualDetail` for every INDI record."""
        return [individual_detail_from_g5(r) for r in self._parser.individuals]

    def get_individual_detail(self, xref: str) -> Optional[IndividualDetail]:
        """Return :class:`IndividualDetail` for a single INDI by xref."""
        el = self._lookup(xref)
        return individual_detail_from_g5(el) if el is not None and el.tag == "INDI" else None

    def family_details(self) -> List[FamilyDetail]:
        """Return :class:`FamilyDetail` for every FAM record."""
        return [family_detail_from_g5(r) for r in self._parser.families]

    def get_family_detail(self, xref: str) -> Optional[FamilyDetail]:
        """Return :class:`FamilyDetail` for a single FAM by xref."""
        el = self._lookup(xref)
        return family_detail_from_g5(el) if el is not None and el.tag == "FAM" else None

    def source_details(self) -> List[SourceDetail]:
        """Return :class:`SourceDetail` for every SOUR record."""
        return [source_detail_from_g5(r) for r in self._parser.sources]

    def get_source_detail(self, xref: str) -> Optional[SourceDetail]:
        """Return :class:`SourceDetail` for a single SOUR by xref."""
        el = self._lookup(xref)
        return source_detail_from_g5(el) if el is not None and el.tag == "SOUR" else None

    def repository_details(self) -> List[RepositoryDetail]:
        """Return :class:`RepositoryDetail` for every REPO record."""
        return [repository_detail_from_g5(r) for r in self._parser.repositories]

    def get_repository_detail(self, xref: str) -> Optional[RepositoryDetail]:
        """Return :class:`RepositoryDetail` for a single REPO by xref."""
        el = self._lookup(xref)
        return repository_detail_from_g5(el) if el is not None and el.tag == "REPO" else None

    def media_details(self) -> List[MediaDetail]:
        """Return :class:`MediaDetail` for every OBJE record."""
        return [media_detail_from_g5(r) for r in self._parser.objects]

    def get_media_detail(self, xref: str) -> Optional[MediaDetail]:
        """Return :class:`MediaDetail` for a single OBJE by xref."""
        el = self._lookup(xref)
        return media_detail_from_g5(el) if el is not None and el.tag == "OBJE" else None

    def shared_notes(self) -> list:
        """Always returns ``[]`` — GEDCOM 5.x has no SNOTE records."""
        return []

    def get_shared_note(self, _xref: str) -> Optional[SharedNoteDetail]:  # noqa: ARG002
        """Always returns ``None`` — GEDCOM 5.x has no SNOTE records."""
        return None

    def submitter_details(self) -> List[SubmitterDetail]:
        """Return :class:`SubmitterDetail` for every SUBM record."""
        return [submitter_detail_from_g5(r) for r in self._parser.submitters]

    def get_submitter_detail(self, xref: str) -> Optional[SubmitterDetail]:
        """Return :class:`SubmitterDetail` for a single SUBM by xref."""
        el = self._lookup(xref)
        return submitter_detail_from_g5(el) if el is not None and el.tag == "SUBM" else None

    def resolve_subm(self, xref: str) -> str:
        """Resolve a SUBM xref pointer to a human-readable name.

        Returns the submitter's NAME value, or the raw *xref* string if the
        record cannot be found or has no name.

        Args:
            xref: Xref id, e.g. ``"@S1@"`` or ``"S1"``.
        """
        xref = xref.strip()
        if not xref.startswith("@"):
            xref = f"@{xref}@"
        detail = self.get_submitter_detail(xref)
        if detail and detail.name:
            return detail.name
        return xref

    # ------------------------------------------------------------------
    # Relationship traversal — raw records
    # ------------------------------------------------------------------

    def get_parents(self, indi_xref: str) -> List[IndividualRecord]:
        """Return the parents of an individual as raw records.

        Walks FAMC → FAM → HUSB/WIFE.

        Args:
            indi_xref: Xref id of the individual (e.g. ``"@I1@"``).

        Returns:
            Raw :class:`IndividualRecord` for each parent found.
        """
        cached = self._cache_get("p", indi_xref)
        if cached is not None:
            return cached  # type: ignore[return-value]
        el = self._lookup(indi_xref)
        if el is None or el.tag != "INDI":
            return []
        result: List[IndividualRecord] = []
        for famc in el.get_child_elements():
            if famc.tag != "FAMC" or not famc.value:
                continue
            fam_el = self._lookup(famc.value)
            if fam_el is None or fam_el.tag != "FAM":
                continue
            for tag in ("HUSB", "WIFE"):
                ptr = fam_el.sub_record(tag)
                if ptr and ptr.value:
                    parent_el = self._lookup(ptr.value)
                    if parent_el and parent_el.tag == "INDI":
                        result.append(parent_el)
        self._cache_set("p", indi_xref, result)
        return result

    def get_children_of(self, indi_xref: str) -> List[IndividualRecord]:
        """Return the children of an individual as raw records.

        Walks FAMS → FAM → CHIL.

        Args:
            indi_xref: Xref id of the individual.

        Returns:
            Raw :class:`IndividualRecord` for each child found.
        """
        cached = self._cache_get("c", indi_xref)
        if cached is not None:
            return cached  # type: ignore[return-value]
        el = self._lookup(indi_xref)
        if el is None or el.tag != "INDI":
            return []
        result: List[IndividualRecord] = []
        for fams in el.get_child_elements():
            if fams.tag != "FAMS" or not fams.value:
                continue
            fam_el = self._lookup(fams.value)
            if fam_el is None or fam_el.tag != "FAM":
                continue
            for chil in fam_el.get_child_elements():
                if chil.tag == "CHIL" and chil.value:
                    child_el = self._lookup(chil.value)
                    if child_el and child_el.tag == "INDI":
                        result.append(child_el)
        self._cache_set("c", indi_xref, result)
        return result

    def get_spouses(self, indi_xref: str) -> List[IndividualRecord]:
        """Return the spouses of an individual as raw records.

        For each FAMS family, returns the other HUSB or WIFE record.

        Args:
            indi_xref: Xref id of the individual.

        Returns:
            Raw :class:`IndividualRecord` for each spouse found.
        """
        norm = _normalize_xref(indi_xref)
        cached = self._cache_get("s", indi_xref)
        if cached is not None:
            return cached  # type: ignore[return-value]
        el = self._lookup(indi_xref)
        if el is None or el.tag != "INDI":
            return []
        result: List[IndividualRecord] = []
        for fams in el.get_child_elements():
            if fams.tag != "FAMS" or not fams.value:
                continue
            fam_el = self._lookup(fams.value)
            if fam_el is None or fam_el.tag != "FAM":
                continue
            for tag in ("HUSB", "WIFE"):
                ptr = fam_el.sub_record(tag)
                if ptr and ptr.value and _normalize_xref(ptr.value) != norm:
                    spouse_el = self._lookup(ptr.value)
                    if spouse_el and spouse_el.tag == "INDI":
                        result.append(spouse_el)
        self._cache_set("s", indi_xref, result)
        return result

    # ------------------------------------------------------------------
    # Relationship traversal — Detail models (explicit)
    # ------------------------------------------------------------------

    def get_parents_detail(self, indi_xref: str) -> List[IndividualDetail]:
        """Return parents as :class:`IndividualDetail` snapshots."""
        return [individual_detail_from_g5(r) for r in self.get_parents(indi_xref)]

    def get_children_detail(self, indi_xref: str) -> List[IndividualDetail]:
        """Return children as :class:`IndividualDetail` snapshots."""
        return [individual_detail_from_g5(r) for r in self.get_children_of(indi_xref)]

    def get_spouses_detail(self, indi_xref: str) -> List[IndividualDetail]:
        """Return spouses as :class:`IndividualDetail` snapshots."""
        return [individual_detail_from_g5(r) for r in self.get_spouses(indi_xref)]

    # ------------------------------------------------------------------
    # Format conversion
    # ------------------------------------------------------------------

    def to_gedcomx(self):
        """Convert this GEDCOM 5 file to a :class:`~gedcomtools.gedcomx.gedcomx.GedcomX` object.

        Returns:
            A :class:`~gedcomtools.gedcomx.gedcomx.GedcomX` instance populated
            from this file's records.

        Example::

            g5 = Gedcom5("family.ged")
            gx = g5.to_gedcomx()
            with open("family.json", "wb") as f:
                f.write(gx.json)
        """
        from ..gedcomx.conversion import GedcomConverter
        return GedcomConverter().Gedcom5x_GedcomX(self)  # type: ignore[arg-type]  # unwrapped inside

    def to_gedcom7(self, *, unknown_tags: str = "drop"):
        """Convert this GEDCOM 5 file to a :class:`~gedcomtools.gedcom7.gedcom7.Gedcom7` object.

        Args:
            unknown_tags: How to handle vendor/non-standard tags.
                ``"drop"`` (default) discards them; ``"convert"`` renames
                them to ``_TAG`` extension tags declared in ``HEAD.SCHMA``.

        Returns:
            A :class:`~gedcomtools.gedcom7.gedcom7.Gedcom7` instance populated
            from the converted records.

        Example::

            g5 = Gedcom5("family.ged")
            g7 = g5.to_gedcom7(unknown_tags="convert")
            g7.write("family7.ged")
        """
        from .g5tog7 import Gedcom5to7
        from ..gedcom7.gedcom7 import Gedcom7
        conv = Gedcom5to7(unknown_tags=unknown_tags)
        records = conv.convert(self)
        g7 = Gedcom7()
        for record in records:
            g7._append_record(record)
        return g7

    def gml(self) -> str:
        """Return the family graph as a GML string.

        Converts this GEDCOM 5 file to GedcomX and serializes it to GML
        (Graph Modelling Language) suitable for Gephi, yEd, and NetworkX.

        Strings are encoded per the Himsolt 1997 GML spec: ``&quot;`` for
        embedded double-quotes, ``&amp;`` for ampersands, ``&#NNN;`` for
        non-ASCII and control characters.  Backslash has no special meaning
        in GML and is passed through unchanged.

        Returns:
            GML content as a :class:`str`.

        Example::

            g5 = Gedcom5("family.ged")
            print(g5.gml())
        """
        return self.to_gedcomx().gml()

    def write_gml(
        self,
        path: Union[str, Path],
        *,
        encoding: str = "utf-8",
    ) -> None:
        """Write the family graph to a GML file.

        Converts this GEDCOM 5 file to GedcomX and writes it as GML
        (Graph Modelling Language) using an atomic write via a temporary
        file so a failed write never corrupts the destination.

        Args:
            path: Destination path.  Parent directory must exist.
            encoding: File encoding (default UTF-8).

        Raises:
            FileNotFoundError: If the parent directory does not exist.

        Example::

            g5 = Gedcom5("family.ged")
            g5.write_gml("family.gml")
        """
        from ..gedcomx.gml import GedcomXGmlExporter
        GedcomXGmlExporter().write(self.to_gedcomx(), path, encoding=encoding)
