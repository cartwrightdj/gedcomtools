# ======================================================================
#  Project: Gedcom-X
#  File:    converter.py
#  Author:  David J. Cartwright
#  Purpose: convert gedcom versions
#  Created: 2025-08-25
#  Updated: 2026-03-24 — accept Gedcom5 facade in Gedcom5x_GedcomX (unwrap ._parser)
# ======================================================================

# GEDCOM Module Types

import mimetypes
import re

# GEDCOM FORM values are often bare extensions in upper or lower case (JPEG,
# jpg, pdf, …).  mimetypes.guess_type is case-sensitive on some platforms and
# doesn't know all common genealogy extensions.  This map covers the gap.
_G5_FORM_MIME: dict[str, str] = {
    "jpeg": "image/jpeg",  "jpg":  "image/jpeg",
    "png":  "image/png",   "gif":  "image/gif",
    "tif":  "image/tiff",  "tiff": "image/tiff",
    "bmp":  "image/bmp",   "webp": "image/webp",
    "pdf":  "application/pdf",
    "mp3":  "audio/mpeg",  "m4a":  "audio/mp4",
    "ogg":  "audio/ogg",   "wav":  "audio/wav",
    "mp4":  "video/mp4",   "m4v":  "video/mp4",
    "avi":  "video/x-msvideo",
    "mov":  "video/quicktime",
    "txt":  "text/plain",  "htm":  "text/html",
    "html": "text/html",
}


def _form_to_mime(form_value: str) -> str | None:
    """Resolve a GEDCOM FORM value to a MIME type string, or return None."""
    if not form_value:
        return None
    key = form_value.strip().lower()
    if key in _G5_FORM_MIME:
        return _G5_FORM_MIME[key]
    mime, _ = mimetypes.guess_type(f"file.{key}")
    return mime
import math
import shutil
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, TypeVar
from collections.abc import Hashable

from gedcomtools.glog import get_logger
from ..gedcom5.elements import Element
from ..gedcom5.parser import Gedcom5x
from .address import Address
from .agent import Agent
from .attribution import Attribution
from .conclusion import Conclusion
from .date import Date
from .document import Document, DocumentParsingContainer
from .event import Event, EventType, EventRole, EventRoleType
from .exceptions import TagConversionError, ConversionErrorDump
from .fact import Fact, FactType
from .family import FamilyParser
from .gedcomx import GedcomX
from .gender import Gender, GenderType
from .identifier import Identifier, IdentifierType
from .name import Name, NameForm, NameType, NamePart, NamePartType, NamePartQualifier
from .note import Note
from .person import Person
from .place_description import PlaceDescription
from .place_reference import PlaceReference
from .qualifier import Qualifier
from .schemas import fact_from_even_tag
from .source_description import SourceDescription, ResourceType
from .source_reference import SourceReference, KnownSourceReference
from .textvalue import TextValue
from .uri import URI
log = get_logger(__name__)

T = TypeVar("T")
K = TypeVar("K", bound=Hashable)


class GxoObjectStack:
    """
    Level-indexed object stack (GEDCOM 'level' -> current GX object at that level)

    This replaces the old push/pop hybrid behavior with what your converter *actually*
    uses everywhere: `self.object_map[level] = obj` and `self.object_map[level-1]`.
    """

    def __init__(self) -> None:
        self._data: Dict[int, Any] = {}

    def __getitem__(self, level: int) -> Any:
        return self._data[level]

    def __setitem__(self, level: int, value: Any) -> None:
        self._data[level] = value

    def __delitem__(self, level: int) -> None:
        del self._data[level]

    def __contains__(self, level: int) -> bool:
        return level in self._data

    def get(self, level: int, default: Any = None) -> Any:
        """Return the object at the given level, or default if not present."""
        return self._data.get(level, default)

    def items(self):
        """Return (level, object) pairs for all entries in the stack."""
        return self._data.items()

    def clear(self) -> None:
        """Remove all entries from the stack."""
        self._data.clear()

    # ---- ergonomic helpers ----
    def parent(self, record: Element) -> Any:
        """Return the object at the level directly above the given record."""
        return self._data[record.level - 1]

    def ancestor(self, record: Element, up: int) -> Any:
        """Return the object ``up`` levels above the given record."""
        return self._data[record.level - up]

    def set_level(self, level: int, value: Any) -> Any:
        """Set the object at a given level and return it."""
        self._data[level] = value
        return value

    def items_desc(self) -> List[tuple[int, Any]]:
        """Return (level, object) pairs sorted from highest level to lowest."""
        return sorted(self._data.items(), key=lambda kv: kv[0], reverse=True)

    def __repr__(self) -> str:
        keys = ", ".join(str(k) for k in sorted(self._data.keys()))
        return f"GxoObjectStack(levels=[{keys}])"

class GedcomConverter:
    type_name_type = {"aka": NameType.AlsoKnownAs}

    personal_events = {
        "BARM", "BASM", "BLES", "CHRA", "CONF", "CENS", "CREM", "EMIG",
        "GRAD", "NATU", "ORDN", "RETI", "WILL",
    }

    def __init__(self) -> None:
        self.gedcomx: GedcomX = GedcomX()
        self.object_map = GxoObjectStack()
        self.object_map[-1] = self.gedcomx  # preserve your behavior

        self.missing_handler_count: Dict[str, int] = {}
        self._line_num: int = 0
        self._family_parser = FamilyParser(self.gedcomx)

        # Build dispatch table once.
        # Keys are GEDCOM tags (e.g., "NAME", "_APID") mapped to bound methods.
        self._dispatch: Dict[str, Callable[[Element], None]] = self._build_dispatch()

    # ------------------------------------------------------------------
    # Core utilities
    # ------------------------------------------------------------------

    @property
    def ignored_tags(self):
        """Return a dict of unhandled tag counts, or None if all tags were handled."""
        return self.missing_handler_count if self.missing_handler_count else None

    @staticmethod
    def clean_str(text: str | None) -> str:
        """Strip whitespace and remove HTML tags from a string; returns '' for None."""
        if text is None:
            return ""
        t = text.strip()
        if not t:
            return ""
        return re.sub(r"<[^>]+>", "", t)

    def _build_dispatch(self) -> Dict[str, Callable[[Element], None]]:
        """
        Maps GEDCOM tag -> handler.

        Your naming convention is handle_<lowercase tag>, so:
          handle_name -> tag NAME
          handle__apid -> tag _APID
          handle__wlnk -> tag _WLNK
        """
        dispatch: Dict[str, Callable[[Element], None]] = {}

        for attr_name in dir(self):
            if not attr_name.startswith("handle_"):
                continue
            fn = getattr(self, attr_name, None)
            if not callable(fn):
                continue

            suffix = attr_name[len("handle_"):]  # e.g. "name", "_apid"
            # Convert python-ish to GEDCOM tag:
            # name -> NAME
            # _apid -> _APID
            tag = suffix.upper()
            dispatch[tag] = fn  # type: ignore[assignment]

        return dispatch

    def _bump_missing(self, tag: str) -> None:
        self.missing_handler_count[tag] = self.missing_handler_count.get(tag, 0) + 1

    def _iter_subrecords(self, record: Element) -> Iterable[Element]:
        subs = record.sub_records()
        if not subs:
            return ()
        return subs

    # ------------------------------------------------------------------
    # Main parse loop
    # ------------------------------------------------------------------

    def parse_gedcom5x_record(self, record: Element) -> None:
        """Dispatch a single GEDCOM Element to its registered handler and recurse into subrecords.

        Args:
            record: The GEDCOM Element to process.

        Raises:
            AssertionError: If record is None.
            ConversionErrorDump: On unhandled exceptions during conversion.
        """
        if record is None:
            raise AssertionError("record is None")

        try:
            subs = record.sub_records() or []
            ln = record._line_num
            log.debug(
                "[{}]: Record tag={} level={} xref={!r} value={!r} subrecords={}",
                ln, record.tag, record.level, record.xref, record.value, len(subs),
            )

            # Special-case "personal event tags"
            if record.tag in self.personal_events:
                self.handle_pevent(record)
            else:
                handler = self._dispatch.get(record.tag)
                if handler is None:
                    self._bump_missing(record.tag)
                    log.error("[{}]: No handler for {}: {}", ln, record.tag, record.describe())
                    return

                log.info("[{}]: Using {} for: {}", ln, handler.__name__, record.describe())
                handler(record)

            # Recurse (your existing behavior)
            for sub in subs:
                log.debug("[{}]: Subrecord: {}", sub._line_num, sub.describe())
                self.parse_gedcom5x_record(sub)

        except ConversionErrorDump:
            raise
        except Exception as exc:
            # Force a consistent diagnostic dump, then re-raise as your dump exception
            self.convert_exception_dump(record, note=f"Unhandled exception: {exc!r}")

    # ------------------------------------------------------------------
    # Diagnostics / reporting
    # ------------------------------------------------------------------

    def convert_exception_dump(self, record: Element, note: Optional[str] = None) -> None:
        """
        Library-safe dump: logs full stack context, then raises ConversionErrorDump.
        No prints.
        """
        if note:
            log.error("Conversion dump note: {}", note)
        log.error("Failed at record: TAG={} line={} level={} | {}", record.tag, record._line_num, record.level, record.describe())

        for level, obj in self.object_map.items_desc():
            try:
                s = str(obj)
            except Exception:
                s = "<str() failed>"
            log.error("STACK level={} type={} repr={!r} str={}", level, type(obj).__name__, obj, s[:200])

        raise ConversionErrorDump()

    @staticmethod
    def format_counts_table(counts: Mapping[Any, int]) -> str:
        """Format a counts mapping as a multi-column text table sorted by count descending."""
        items = [(str(k), int(v)) for k, v in counts.items()]
        if not items:
            return "(empty)"

        items.sort(key=lambda kv: (-kv[1], kv[0]))

        key_w = max(len(k) for k, _ in items)
        num_w = max(len(str(v)) for _, v in items)
        cell_fmt = f"{{k:<{key_w}}}  {{v:>{num_w}}}"
        cell_width = key_w + 2 + num_w + 2

        term_cols = shutil.get_terminal_size(fallback=(100, 24)).columns
        fit_cols = max(1, term_cols // cell_width)
        sqrt_cols = max(1, int(math.sqrt(len(items))))
        cols = max(1, min(len(items), max(fit_cols, sqrt_cols)))
        rows = math.ceil(len(items) / cols)

        lines: List[str] = []
        for r in range(rows):
            line = []
            for c in range(cols):
                i = c * rows + r
                if i < len(items):
                    k, v = items[i]
                    cell = cell_fmt.format(k=k, v=v)
                    line.append(cell.ljust(cell_width))
            lines.append("".join(line).rstrip())
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Misc helpers you already use elsewhere
    # ------------------------------------------------------------------

    @staticmethod
    def has_duplicates(seq) -> bool:
        """Return True if the sequence contains any duplicate values."""
        return len(seq) != len(set(seq))

    @staticmethod
    def find_duplicates(seq):
        """Return a list of values that appear more than once in seq, preserving order."""
        seen, dups = set(), []
        for x in seq:
            if x in seen and x not in dups:
                dups.append(x)
            seen.add(x)
        return dups

    def unique(self, seq: Iterable[T], key: Optional[Callable[[T], K]] = None) -> List[T]:
        """Return a deduplicated list preserving first-occurrence order.

        Args:
            seq: Input iterable.
            key: Optional callable to extract a comparison key from each element.
        """
        seen: set[K] = set()
        out: List[T] = []
        for item in seq:
            k = item if key is None else key(item)  # type: ignore[assignment]
            if k not in seen:
                seen.add(k)  # type: ignore[arg-type]
                out.append(item)
        return out

    # ------------------------------------------------------------------
    # Conversion entrypoint
    # ------------------------------------------------------------------

    def Gedcom5x_GedcomX(self, gedcom5x: Gedcom5x) -> GedcomX:
        """Convert a parsed Gedcom5x object to a GedcomX genealogy.

        Primes id maps from GEDCOM cross-references, then walks every top-level
        record through the tag dispatch table to populate the GedcomX object.

        Args:
            gedcom5x: A fully parsed Gedcom5x instance.

        Returns:
            The populated GedcomX genealogy.

        Raises:
            ValueError: If gedcom5x is falsy.
        """
        if not gedcom5x:
            raise ValueError("gedcom5x is falsy")

        # Accept either a Gedcom5 facade or a raw Gedcom5x parser.
        if hasattr(gedcom5x, "_parser"):
            gedcom5x = gedcom5x._parser

        log.debug("Priming top-level IDs")
        for obj in gedcom5x.objects:
            gx_obj = SourceDescription(id=obj.xref, resourceType=ResourceType.DigitalArtifact)
            self.gedcomx.add_source_description(gx_obj)

        base_docs = len(self.gedcomx.documents)
        log.debug("Primed {} SourceDescriptions from GEDCOM5 Objects", base_docs)

        for source in gedcom5x.sources:
            gx_obj = SourceDescription(id=source.xref)
            self.gedcomx.add_source_description(gx_obj)

        log.debug(
            "Primed {} SourceDescriptions from GEDCOM5 Sources",
            len(self.gedcomx.sourceDescriptions) - base_docs,
        )

        for repo in gedcom5x.repositories:
            gx_obj = Agent(id=repo.xref)
            self.gedcomx.add_agent(gx_obj)

        for submitter in gedcom5x.submitters:
            gx_obj = Agent(id=submitter.xref)
            self.gedcomx.add_agent(gx_obj)

        for indi in gedcom5x.individuals:
            gx_obj = Person(id=indi.xref)
            self.gedcomx.add_person(gx_obj)

        # Parse all top-level records
        for header in gedcom5x.header:
            self.parse_gedcom5x_record(header)

        for source in gedcom5x.sources:
            self.parse_gedcom5x_record(source)
        for obj in gedcom5x.objects:
            self.parse_gedcom5x_record(obj)
        for indi in gedcom5x.individuals:
            self.parse_gedcom5x_record(indi)
        for repo in gedcom5x.repositories:
            self.parse_gedcom5x_record(repo)
        for fam in gedcom5x.families:
            self.parse_gedcom5x_record(fam)
        for sub in gedcom5x.submitters:
            self.parse_gedcom5x_record(sub)

        # Cleanup duplicates
        for sd in self.gedcomx.sourceDescriptions:
            sd.notes = self.unique(sd.notes, key=lambda n: n._key())
            sd.descriptions = self.unique(sd.descriptions, key=lambda n: n._key())

        # record unhandled tags for diagnostics
        self.gedcomx._import_unhandled_tags = dict(self.missing_handler_count)

        # Log missing counts (don’t print)
        if self.missing_handler_count:
            log.warning("Unhandled tags:\n{}", self.format_counts_table(self.missing_handler_count))

        return self.gedcomx


    def handle__apid(self, record: Element):
        if not record.value:
            return
        parent = self.object_map.get(record.level-1)
        if isinstance(parent, SourceReference):
            parent.description.add_identifier(Identifier(type=IdentifierType.Other, values=[URI.from_url('APID://' + record.value)])) # type: ignore
        elif isinstance(parent, SourceDescription):
            parent.add_identifier(Identifier(type=IdentifierType.Other, values=[URI.from_url('APID://' + record.value)])) # type: ignore
        else:
            log.debug(f"Skipping _APID — parent {type(parent).__name__} does not accept identifiers")

    def handle__meta(self, record: Element):
        if isinstance(self.object_map[record.level-1], SourceDescription):
            gxobject = Note(text=self.clean_str(record.value if record.value else 'Warning: This NOTE had not content.'))
            self.object_map[record.level-1].add_note(gxobject)

            self.object_map[record.level] = gxobject
        elif isinstance(self.object_map[record.level-1], DocumentParsingContainer):
            gxobject = Note(text=self.clean_str(record.value if record.value else 'Warning: This NOTE had not content.'))
            self.object_map[record.level-1].sourceDescription.add_note(gxobject)

            self.object_map[record.level] = gxobject
        else:
            self.convert_exception_dump(record=record)

    def handle__wlnk(self, record: Element):
        return self.handle_sour(record)

    def handle_adop(self, record: Element):
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Fact(type=FactType.Adoption)
            self.object_map[record.level-1].add_fact(gxobject)


            self.object_map[record.level] = gxobject
        else:
            self.convert_exception_dump(record=record)

    def handle_addr(self, record: Element):
        if isinstance(self.object_map[record.level-1], Agent):
            # TODO CHeck if URL?
            if record.value is not None and self.clean_str(record.value):
                gxobject = Address.model_validate({"value": self.clean_str(record.value)})
            else:
                gxobject = Address()
            self.object_map[record.level-1].add_address(gxobject)
            self.object_map[record.level] = gxobject
        else:
            raise ValueError(f"I do not know how to handle an 'ADDR' tag for a {type(self.object_map[record.level-1])}")

    def handle_adr1(self, record: Element):
        if isinstance(self.object_map[record.level-1], Address):
            if record.value is not None and self.clean_str(record.value):
                self.object_map[record.level-1].street = self.clean_str(record.value)
            else:
                self.convert_exception_dump(record=record)
        else:
            self.convert_exception_dump(record=record)

    def handle_adr2(self, record: Element):
        if isinstance(self.object_map[record.level-1], Address):
            if record.value is not None and self.clean_str(record.value):
                self.object_map[record.level-1].street2 = self.clean_str(record.value)
            else:
                self.convert_exception_dump(record=record)
        else:
            self.convert_exception_dump(record=record)

    def handle_adr3(self, record: Element):
        if isinstance(self.object_map[record.level-1], Address):
            if record.value is not None and self.clean_str(record.value):
                self.object_map[record.level-1].street3 = self.clean_str(record.value)
            else:
                self.convert_exception_dump(record=record)
        else:
            self.convert_exception_dump(record=record)

    def handle_adr4(self, record: Element):
        if isinstance(self.object_map[record.level-1], Address):
            if record.value is not None and self.clean_str(record.value):
                self.object_map[record.level-1].street4 = self.clean_str(record.value)
        else:
            self.convert_exception_dump(record=record)

    def handle_adr5(self, record: Element):
        if isinstance(self.object_map[record.level-1], Address):
            if record.value is not None and self.clean_str(record.value):
                self.object_map[record.level-1].street5 = self.clean_str(record.value)
        else:
            self.convert_exception_dump(record=record)

    def handle_adr6(self, record: Element):
        if isinstance(self.object_map[record.level-1], Address):
            if record.value is not None and self.clean_str(record.value):
                self.object_map[record.level-1].street6 = self.clean_str(record.value)
        else:
            self.convert_exception_dump(record=record)

    def handle_abbr(self, record: Element):
        if isinstance(self.object_map[record.level-1], SourceDescription) and record.value:
            from ..gedcomx.note import Note
            self.object_map[record.level-1].add_note(Note(text=f"Abbreviation: {self.clean_str(record.value)}"))
        else:
            self.convert_exception_dump(record=record)

    def handle_agnc(self, record: Element):
        parent = self.object_map[record.level-1]
        if record.value and isinstance(parent, (Fact, SourceDescription)):
            from ..gedcomx.note import Note
            parent.add_note(Note(text=f"Agency: {self.clean_str(record.value)}"))
        else:
            self.convert_exception_dump(record=record)

    def handle_auth(self, record: Element):
        if isinstance(self.object_map[record.level-1], SourceDescription):
            existing_agents = self.gedcomx.agents.by_name(record.value) if record.value else None
            if existing_agents:
                gxobject = existing_agents[0]
            else:
                gxobject = Agent(names=[TextValue(value=record.value)])
                self.gedcomx.add_agent(gxobject)

            self.object_map[record.level-1].author = gxobject

            self.object_map[record.level] = gxobject
        else:
            self.convert_exception_dump(record=record)

    def handle_phon(self, record: Element):
        if isinstance(self.object_map[record.level-1], Agent):
            if record.value is not None and self.clean_str(record.value):
                self.object_map[record.level-1].phones.append(self.clean_str(record.value))
        else:
            self.convert_exception_dump(record=record)

    def handle_email(self, record: Element):
        if isinstance(self.object_map[record.level-1], Agent):
            if record.value is not None and self.clean_str(record.value):
                self.object_map[record.level-1].emails.append(self.clean_str(record.value))
        else:
            self.convert_exception_dump(record=record)

    def handle_fax(self, record: Element):
        if isinstance(self.object_map[record.level-1], Agent):
            if record.value is not None and self.clean_str(record.value):
                self.object_map[record.level-1].emails.append('FAX:' + (self.clean_str(record.value) if record.value is not None else ''))
        else:
            self.convert_exception_dump(record=record)


    def handle_bapm(self, record: Element):
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Fact(type=FactType.Baptism)
            self.object_map[record.level-1].add_fact(gxobject)


            self.object_map[record.level] = gxobject
        else:
            self.convert_exception_dump(record=record)

    def handle_birt(self, record: Element):
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Fact(type=FactType.Birth)
            self.object_map[record.level-1].add_fact(gxobject)
            self.object_map[record.level] = gxobject
        else:
            self.convert_exception_dump(record=record)

    def handle_buri(self, record: Element):
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Fact(type=FactType.Burial)
            self.object_map[record.level-1].add_fact(gxobject)


            self.object_map[record.level] = gxobject
        else:
            self.convert_exception_dump(record=record)

    def handle_caln(self, record: Element):
        if isinstance(self.object_map[record.level-1], SourceReference):
            self.object_map[record.level-1].description.add_identifier(Identifier(type=IdentifierType.Other, values=[URI.from_url('Call Number:' + record.value if record.value else '')])) # type: ignore
        elif isinstance(self.object_map[record.level-1], SourceDescription):
            self.object_map[record.level-1].add_identifier(Identifier(type=IdentifierType.Other, values=[URI.from_url('Call Number:' + record.value if record.value else '')])) # type: ignore
        elif isinstance(self.object_map[record.level-1], Agent):
            pass
            # TODO Why is GEDCOM so shitty? A callnumber for a repository?
        else:
            self.convert_exception_dump(record=record)

    def handle_chan(self, record: Element):
        if isinstance(self.object_map[record.level-1], SourceDescription):
            date = record.sub_record('DATE')
            if date is not None:
                self.object_map[record.level-1].created = Date(original=date.value)
        elif isinstance(self.object_map[record.level-1], Agent):
            if self.object_map[record.level-1].attribution is None:
                gxobject = Attribution()
                self.object_map[record.level-1].attribution = gxobject
                self.object_map[record.level] = gxobject
            else:
                self.convert_exception_dump(record=record)
        elif isinstance(self.object_map[record.level-1], Person):
            if self.object_map[record.level-1].attribution is None:
                gxobject = Attribution()
                self.object_map[record.level-1].attribution = gxobject
                self.object_map[record.level] = gxobject
            else:
                self.convert_exception_dump(record=record)
        else:
            self.convert_exception_dump(record=record)

    def handle_chr(self, record: Element):
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Fact(type=FactType.Christening)
            self.object_map[record.level-1].add_fact(gxobject)


            self.object_map[record.level] = gxobject
        else:
            self.convert_exception_dump(record=record)

    def handle_city(self, record: Element):
        if isinstance(self.object_map[record.level-1], Address):
            if record.value is not None:
                self.object_map[record.level-1].city = self.clean_str(record.value)
            else: raise ValueError('Record had no value')
        else:
            raise ValueError(f"I do not know how to handle an 'CITY' tag for a {type(self.object_map[record.level-1])}")

    def handle_conc(self, record: Element):
        obj_map = sorted(self.object_map.items(), reverse=True)
        obj_map = dict(obj_map)
        if isinstance(self.object_map[record.level-1], Note):
            gxobject = self.clean_str(str(record.value))
            self.object_map[record.level-1].append(gxobject)
        elif isinstance(self.object_map[record.level-1], Agent):
            gxobject = str(record.value)
            self.object_map[record.level-1]._append_to_name(gxobject)
        elif isinstance(self.object_map[record.level-1], Qualifier):
            gxobject = str(record.value)
            self.object_map[record.level-1]._append(gxobject)
        elif isinstance(self.object_map[record.level-1], TextValue):
            #gxobject = TextValue(value=self.clean_str(record.value))
            self.object_map[record.level-1]._append_to_value(record.value)
        elif isinstance(self.object_map[record.level-1], SourceReference):
            self.object_map[record.level-1].append(record.value)
        elif isinstance(self.object_map[record.level-1], Fact):
            self.object_map[record.level-1].notes[0].text += record.value
        elif isinstance(self.object_map[record.level-1], str):
            self.object_map[record.level-1] = self.object_map[record.level-1] = record.value

        else:
            self.convert_exception_dump(record=record)

    def handle_cont(self, record: Element):
        if isinstance(self.object_map[record.level-1], Note):
            gxobject = str(" " + record.value if record.value else '')
            if gxobject:
                self.object_map[record.level-1].append(gxobject)
        elif isinstance(self.object_map[record.level-1], Agent):
            gxobject = str(" " + record.value if record.value else '')
        elif isinstance(self.object_map[record.level-1], Qualifier):
            gxobject = str(" " + record.value if record.value else '')
            self.object_map[record.level-1]._append(gxobject)
        elif isinstance(self.object_map[record.level-1], TextValue):
            #gxobject = TextValue(value="\n" + record.value)
            self.object_map[record.level-1]._append_to_value(record.value if record.value else '\n')
        elif isinstance(self.object_map[record.level-1], SourceReference):
            if record.value:
                self.object_map[record.level-1].append(record.value)
        elif isinstance(self.object_map[record.level-1], Address):
            if record.value:
                self.object_map[record.level-1]._append(record.value)
        elif isinstance(self.object_map[record.level-1], str):
            self.object_map[record.level-1] = self.object_map[record.level-1] = record.value
        else:
            self.convert_exception_dump(record=record)

    def handle_crea(self, record: Element):
        if isinstance(self.object_map[record.level-1], SourceDescription):
            date = record.sub_record('DATE')
            if  date is not None:
                self.object_map[record.level-1].created = Date(original=date[0].value)
            else: raise ValueError('DATE had not value')

        elif isinstance(self.object_map[record.level-1], Agent):
            if self.object_map[record.level-1].attribution is None:
                gxobject = Attribution()
                self.object_map[record.level-1].attribution = gxobject

                self.object_map[record.level] = gxobject
            else:
                log.info(f"[{record.tag}] Attribution already exists for SourceDescription with id: {self.object_map[record.level-1].id}")
        else:
            raise ValueError(f"Could not handle '{record.tag}' tag in record {record.describe()}, last stack object {self.object_map[record.level-1]}")

    def handle__crea(self, record: Element):
        if isinstance(self.object_map[record.level-1], SourceDescription):
            if  record.value is not None:
                self.object_map[record.level-1].created = Date(original=record.value)
            else: raise ValueError('DATE had not value')

    def handle_ctry(self, record: Element):
        if isinstance(self.object_map[record.level-1], Address):
            if record.value is not None:
                self.object_map[record.level-1].country = self.clean_str(record.value)
            else:
                raise ValueError('Recrod had no value')
        else:
            raise ValueError(f"I do not know how to handle an '{record.tag}' tag for a {type(self.object_map[record.level-1])}")

    def handle_data(self, record: Element) -> None:
        self.object_map[record.level] = self.object_map[record.level-1]

    def handle_date(self, record: Element):
        if record.parent is not None and record.parent.tag == 'PUBL':
            #gxobject = Date(original=record.value) #TODO Make a parser for solid timestamps
            #self.object_map[0].published = gxobject
            #self.object_map[0].published = date_to_timestamp(record.value) if record.value else None
            self.object_map[0].published = record.value
            #
            #self.object_map[record.level] = gxobject
        elif isinstance(self.object_map[record.level-1], FamilyParser):
            self.object_map[record.level-1].set_marr_date(record)
        elif isinstance(self.object_map[record.level-1], Event):
            self.object_map[record.level-1].date = Date(original=record.value)
        elif isinstance(self.object_map[record.level-1], Fact):
            self.object_map[record.level-1].date = Date(original=record.value)
        elif record.parent is not None and record.parent.tag == 'DATA' and isinstance(self.object_map[record.level-2], SourceReference):
            gxobject = Note(text='Date: ' + record.value if record.value else '')
            self.object_map[record.level-2].description.add_note(gxobject)

            self.object_map[record.level] = gxobject
        elif isinstance(self.object_map[record.level-1], SourceDescription):
            self.object_map[record.level-1].created = record.value
        elif isinstance(self.object_map[record.level-1], DocumentParsingContainer):
            self.object_map[record.level-1].sourceDescription.created = record.value
        elif isinstance(self.object_map[record.level-1], Attribution):
            if record.parent is not None and record.parent.tag == 'CREA':
                self.object_map[record.level-1].created = record.value
            elif record.parent is not None and record.parent.tag == "CHAN":
                self.object_map[record.level-1].modified = record.value
            elif (_created := self.object_map[record.level-1].created) is None:
                self.object_map[record.level-1].created = record.value


        elif record.parent is not None and record.parent.tag in ['CREA','CHAN']:
            pass

        elif isinstance(self.object_map[record.level-1], Agent):
            # e.g. HEAD/SOUR/DATA/DATE — source publication date; no GedcomX slot, skip
            log.debug("Skipping DATE under Agent context ({}): {}", record.parent.tag if record.parent else "?", record.value)

        else:
            self.convert_exception_dump(record=record)

    def handle_deat(self, record: Element):
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Fact(type=FactType.Death)
            self.object_map[record.level-1].add_fact(gxobject)


            self.object_map[record.level] = gxobject
        else:
            self.convert_exception_dump(record=record)

    def handle_pevent(self, record: Element):
        # EVEN (Fact) specific to INDI (Person)
        if (fact_type := fact_from_even_tag(record.tag)) is not None:
            if isinstance(self.object_map[record.level-1], Person):
                gxobject = Fact(type=fact_type)
                self.object_map[record.level-1].add_fact(gxobject)
                self.object_map[record.level] = gxobject

    def handle_even(self, record: Element):
        # TODO If events in a @S, check if only 1 person matches?
        # TODO, how to deal with and diferentiate Events
        if record.value and (not record.value.strip() == ''):
            values = [value.strip() for value in record.value.split(",")]
            for value in values:
                if (fact_type := fact_from_even_tag(value)) is not None:
                    if isinstance(self.object_map[record.level-1], Person):
                        gxobject = Fact(type=fact_type)
                        self.object_map[record.level-1].add_fact(gxobject)
                        self.object_map[record.level] = gxobject

                    elif isinstance(self.object_map[record.level-1], SourceDescription):
                        sd = self.object_map[record.level-1]
                        source_ref = SourceReference(description=sd)
                        try:
                            event_type = EventType(fact_type.value)
                        except ValueError:
                            event_type = None
                        gxobject = Event(type=event_type, sources=[source_ref])
                        self.gedcomx.add_event(gxobject)
                        self.object_map[record.level] = gxobject
                    else:
                        self.convert_exception_dump(record=record)
                else:
                    log.warning(f"EVEN type is not known {record.describe()}")
                    gxobject = Event(roles=[EventRole(person=self.object_map[record.level],type=EventRoleType.Principal)])
                    self.gedcomx.add_event(gxobject)
                    self.object_map[record.level] = gxobject

        else:
            if (even_type := record.sub_record('TYPE')) is not None:

                if possible_fact := FactType.guess(even_type.value):
                    gxobject = Fact(type=possible_fact)
                    self.object_map[record.level-1].add_fact(gxobject)
                    self.object_map[record.level] = gxobject
                    return
                if EventType.guess(even_type.value):
                    if isinstance(self.object_map[record.level-1], Person):
                        gxobject = Event(type=EventType.guess(even_type.value), roles=[EventRole(person=self.object_map[record.level-1], type=EventRoleType.Principal)])
                        self.gedcomx.add_event(gxobject)

                        self.object_map[record.level] = gxobject
                    return
                if isinstance(self.object_map[record.level-1], Person):
                    gxobject = Event(type=None, roles=[EventRole(person=self.object_map[record.level-1], type=EventRoleType.Principal)])
                    gxobject.add_note(Note(subject='Event', text=record.value))
                    self.gedcomx.add_event(gxobject)

                    self.object_map[record.level] = gxobject
                    return

                self.convert_exception_dump(record=record)

    def handle_exid(self,record: Element):
        if record.value:
            gxobject = Identifier(type=IdentifierType.External, values=[URI.from_url(record.value)]) # type: ignore
            self.object_map[record.level-1].add_identifier(gxobject)
            self.object_map[record.level] = gxobject
        else: raise ValueError('Record had no value')

    def handle_fam(self, record: Element) -> None:
        self._family_parser.reset()
        self.object_map[record.level] = self._family_parser

    def handle_husb(self, record: Element):
        if record is not None:
            obj_id = record.value
            if obj_id:
                husband = self.gedcomx.get_person_by_id(obj_id)
                self._family_parser.set_husband(husband)
                log.debug(f"found husband: {husband}")
                self.object_map[record.level] = husband

    def handle_wife(self, record: Element):
        if record is not None:
            obj_id = record.value
            if obj_id:
                wife = self.gedcomx.get_person_by_id(obj_id)
                self._family_parser.set_wife(wife)
                log.debug(f"found husband: {wife}")
                self.object_map[record.level] = wife

    def handle_chil(self, record: Element):
        if record is not None:
            obj_id = record.value
            if obj_id:
                child = self.gedcomx.get_person_by_id(obj_id)
                self._family_parser.add_child(child)
                _child_name = child.names[0].nameForms[0].fullText if child and child.names and child.names[0].nameForms else None
                log.debug("found child: id={} name={}", getattr(child, "id", None), _child_name)
                self.object_map[record.level] = child

    def handle_famc(self, _record: Element) -> None:
        #TODO
        return

    def handle_fams(self, _record: Element) -> None:
        #TODO
        return

    def handle_file(self, record: Element):
        if isinstance(self.object_map[record.level-1], SourceDescription):
            sd = self.object_map[record.level-1]
            sd.resourceType = ResourceType.DigitalArtifact
            if record.value:
                if sd.about is None:
                    sd.about = record.value
                else:
                    # Multiple FILE entries: store extras as notes (about is singular)
                    sd.add_note(Note(text=f"Additional file: {record.value}"))

        elif isinstance(self.object_map[record.level-1], DocumentParsingContainer):
            container = self.object_map[record.level-1]
            container.sourceDescription.resourceType = ResourceType.DigitalArtifact
            if record.value:
                if container.sourceDescription.about is None:
                    container.sourceDescription.about = record.value
                else:
                    container.sourceDescription.add_note(
                        Note(text=f"Additional file: {record.value}")
                    )
            self.object_map[record.level] = container



        elif isinstance(self.object_map[record.level-1], Attribution):
            log.warning("Encountered a 'FILE' tag under an 'Attribution', assuming this is in the 'HEAD' block and skipping")
        else:
            self.convert_exception_dump(record=record)

    def handle_form(self, record: Element):
        parent_obj = self.object_map.get(record.level-2)
        if record.parent is not None and record.parent.tag == 'FILE' and isinstance(parent_obj, SourceDescription):
            if record.value and record.value.strip():
                mime_type = _form_to_mime(record.value)
                if mime_type:
                    parent_obj.mediaType = mime_type
                else:
                    log.error("Could not determine mime type from {}", record.value)
        elif record.parent is not None and record.parent.tag == 'FILE' and isinstance(parent_obj, DocumentParsingContainer):
            if record.value and record.value.strip():
                mime_type = _form_to_mime(record.value)
                if mime_type:
                    parent_obj.sourceDescription.mediaType = mime_type
                else:
                    log.error("Could not determine mime type from {}", record.value)
        elif isinstance(self.object_map[record.level-1], PlaceDescription):
            self.object_map[record.level-1].names.append(TextValue(value=record.value))
        elif isinstance(self.object_map[record.level-1], DocumentParsingContainer):
            container = self.object_map[record.level-1]
            if record.value and record.value.strip():
                mime_type = _form_to_mime(record.value)
                if mime_type:
                    container.sourceDescription.mediaType = mime_type
                else:
                    log.error("Could not determine mime type from {}", record.value)
            self.object_map[record.level] = container

        elif record.parent is not None and record.parent.tag == 'TRAN':
            # FORM under TRAN specifies the script/encoding of the transliteration
            # (e.g. "gedcom/standard", "gedcom/zh-Hant"). No GedcomX equivalent;
            # store as a note on the NameForm or TextValue if present.
            parent = self.object_map.get(record.level - 1)
            if isinstance(parent, NameForm) and record.value:
                parent.fullText = (parent.fullText or "") + f" [{record.value}]"
            else:
                log.debug("handle_form[TRAN]: ignoring FORM={!r} under TRAN for {}", record.value, type(parent).__name__ if parent else "None")
        else:
            self.convert_exception_dump(record=record)

    def handle_medi(self, record: Element) -> None:
        """Handle GEDCOM 5 FILE.MEDI (media qualifier: photo, video, audio, …).

        No direct GedcomX equivalent; the value is stored as a note on the
        parent SourceDescription so the information is not lost.  MEDI under
        REPO.CALN has no GX mapping and is silently ignored.
        """
        parent = self.object_map.get(record.level - 1)
        sd = None
        if isinstance(parent, SourceDescription):
            sd = parent
        elif isinstance(parent, DocumentParsingContainer):
            sd = parent.sourceDescription
        if sd is not None and record.value:
            sd.add_note(Note(text=f"Media type: {record.value}"))
        # else: MEDI under REPO.CALN or other contexts — no mapping, skip silently

    def handle_fsid(self,record: Element):
        if record.value:
            gxobject = Identifier(type=IdentifierType.FamilySearchId, values=[URI.from_url(record.value)]) # type: ignore
            self.object_map[record.level-1].add_identifier(gxobject)
            self.object_map[record.level] = gxobject
        else:
            self.convert_exception_dump(record=record)

    def handle_givn(self, record: Element):
        if isinstance(self.object_map[record.level-1], Name):
            given_name = NamePart(value=record.value, type=NamePartType.Given)
            self.object_map[record.level-1]._add_name_part(given_name)
        else:
            self.convert_exception_dump(record=record)

    def handle_head(self,record: Element):
        attribution = Attribution()
        self.gedcomx.attribution = attribution
        self.object_map[record.level] = attribution

    def handle_indi(self, record: Element):
        person = self.gedcomx.persons.by_id(record.xref)
        if person is None:
            log.warning('Had to create person with id {recrod.xref}')
            if isinstance(record.xref,str):
                person = Person(id=record.xref)
                self.gedcomx.add_person(person)
            else:
                self.convert_exception_dump(record=record)
        self.object_map[record.level] = person

    def handle_immi(self, record: Element):
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Fact(type=FactType.Immigration)
            self.object_map[record.level-1].add_fact(gxobject)


            self.object_map[record.level] = gxobject
        else:
            self.convert_exception_dump(record=record)

    def handle_map(self, record: Element):
        if isinstance(self.object_map[record.level-1],PlaceReference):
            self.object_map[record.level] = self.object_map[record.level-1].description
        else:
            self.convert_exception_dump(record=record)

    def handle_marr(self, record: Element):
        """
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Fact(type=FactType.Marriage)
            self.object_map[record.level-1].add_fact(gxobject)


            self.object_map[record.level] = gxobject
        """
        if record.parent is not None and record.parent.tag == 'FAM':
            self._family_parser.reset()
            self.object_map[record.level] = self._family_parser
            return


        if (add_fact := getattr(self.object_map[record.level-1],'add_fact',None)) is not None:
            gxobject = Fact(type=FactType.Marriage)
            add_fact(gxobject)
            self.object_map[record.level] = gxobject
        else:
            self.convert_exception_dump(record=record)

    def handle_lati(self, record: Element):
        if isinstance(self.object_map[record.level-1], PlaceDescription):
            self.object_map[record.level-1].latitude = record.value
        else:
            self.convert_exception_dump(record=record)

    def handle_long(self, record: Element):
        if isinstance(self.object_map[record.level-1], PlaceDescription):
            self.object_map[record.level-1].longitude = record.value
        else:
            self.convert_exception_dump(record=record)

    def handle__link(self,record: Element):
        if isinstance(self.object_map[record.level-1], SourceReference):
            gxobject = Identifier(values=[URI.from_url(record.value)], type=IdentifierType.External) # type: ignore
            self.object_map[record.level-1].description.add_identifier(gxobject)
            self.object_map[record.level] = gxobject
        else:
            self.convert_exception_dump(record=record)

    def handle__milt(self, record: Element):
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Fact(type=FactType.MilitaryService)
            self.object_map[record.level-1].add_fact(gxobject)
            self.object_map[record.level] = gxobject
        else:
            self.convert_exception_dump(record=record)

    def handle_name(self, record: Element):
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Name.simple(record.value if record.value else 'WARNING: NAME had no value')
            #gxobject = Name(nameForms=[NameForm(fullText=record.value)], type=NameType.BirthName)
            self.object_map[record.level-1].add_name(gxobject)
            self.object_map[record.level] = gxobject
        elif isinstance(self.object_map[record.level-1], Agent):
            gxobject = TextValue(value=record.value)
            self.object_map[record.level-1].add_name(gxobject)
        else:
            self.convert_exception_dump(record=record)

    def handle_note(self, record: Element):
        if isinstance(self.object_map[record.level-1], SourceDescription):
            gxobject = Note(text=self.clean_str(record.value))
            self.object_map[record.level-1].add_note(gxobject)


            self.object_map[record.level] = gxobject
        elif isinstance(self.object_map[record.level-1], SourceReference):
            if self.object_map[record.level-1].description is not None:
                gxobject = Note(text=self.clean_str(record.value))
                self.object_map[record.level-1].description.add_note(gxobject)
                self.object_map[record.level] = gxobject
            else:
                log.error('SourceReference does not have description')



        elif isinstance(self.object_map[record.level-1], Conclusion):
            gxobject = Note(text=record.value)
            self.object_map[record.level-1].add_note(gxobject)


            self.object_map[record.level] = gxobject
        elif isinstance(self.object_map[record.level-1], Agent):
            gxobject = Note(text=record.value)
            self.object_map[record.level-1].add_note(gxobject)
            self.object_map[record.level] = gxobject
        elif isinstance(self.object_map[record.level-1], Attribution):
            if self.object_map[record.level-1].changeMessage is None:
                gxobject = record.value
                self.object_map[record.level-1].changeMessage = gxobject
            else:
                gxobject = self.object_map[record.level-1].changeMessage + '' + record.value
                self.object_map[record.level-1].changeMessage = gxobject

            self.object_map[record.level] = gxobject
        elif isinstance(self.object_map[record.level-1], Note):
            gxobject = Note(text=self.clean_str(record.value))
            self.object_map[record.level-2].add_note(gxobject)
            self.object_map[record.level] = gxobject
        elif isinstance(self.object_map[record.level-1], FamilyParser):
            gxobject = Note(text=self.clean_str(record.value))
            self.object_map[record.level-1].add_note(gxobject)
            self.object_map[record.level] = gxobject
        elif isinstance(self.object_map[record.level-1], DocumentParsingContainer):
            gxobject = Note(text=self.clean_str(record.value if record.value else ''))
            self.object_map[record.level-1].sourceDescription.add_note(gxobject)
            self.object_map[record.level] = gxobject
        else:
            self.convert_exception_dump(record=record)

    def handle_nsfx(self, record: Element):
        if isinstance(self.object_map[record.level-1], Name):
            surname = NamePart(value=record.value, type=NamePartType.Suffix)
            self.object_map[record.level-1]._add_name_part(surname)
        else:
            self.convert_exception_dump(record=record)

    def handle_occu(self, record: Element):
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Fact(type=FactType.Occupation)
            self.object_map[record.level-1].add_fact(gxobject)


            self.object_map[record.level] = gxobject
        else:
            self.convert_exception_dump(record=record)

    def handle_obje(self, record: Element):
        if record.level == 0:
            # Use DocumentParser to Create Documnet and Update Underlying SourceDescription Made from OBJE tags
            if (gxobject := self.gedcomx.sourceDescriptions.by_id(record.xref)) is None:
                log.debug(f"SourceDescription with id: {record.xref} was not found. Creating a new SourceDescription")
                log.debug(f"Creating SourceDescription from Object {record.tag} {record.describe()}")
                gxobject = SourceDescription(id=record.xref if record.xref else None)
                self.object_map[record.level-1].add_source_description(gxobject)
                gxobject = DocumentParsingContainer(source=gxobject)
            else:
                log.debug(f"Found SourceDescription with id:{record.xref}")
                gxobject = DocumentParsingContainer(source=gxobject)
            self.object_map[record.level] = gxobject

        if isinstance(self.object_map[record.level-1],SourceReference) and record.level > 0:
            gxobject = DocumentParsingContainer(source=self.object_map[record.level-1].description)
            self.object_map[record.level] = gxobject

    def handle_page(self, record: Element):
        if isinstance(self.object_map[record.level-1], SourceReference):
            #self.object_map[record.level-1].descriptionId = record.value
            gx_object = Qualifier(name=KnownSourceReference.Page,value=record.value)
            self.object_map[record.level-1].add_qualifier(gx_object)
            self.object_map[record.level] = gx_object
        else:
            pass

    def handle_plac(self, record: Element):
        if isinstance(self.object_map[record.level-1], Agent):
            gxobject = Address.model_validate({"value": record.value})
            self.object_map[record.level-1].add_address(gxobject)
            self.object_map[record.level] = gxobject
        elif isinstance(self.object_map[record.level-1], FamilyParser):
            self.object_map[record.level-1].set_marr_date(record)

        elif isinstance(self.object_map[record.level-1], Event):
            existing_place = self.gedcomx.places.by_name(record.value)
            if existing_place:
                self.object_map[record.level-1].place = PlaceReference(original=record.value, description=existing_place[0])
            else:
                place_des = PlaceDescription(names=[TextValue(value=record.value)])
                self.gedcomx.add_place_description(place_des)
                self.object_map[record.level-1].place = PlaceReference(original=record.value, description=place_des)
                if (record.sub_records() is not None) and len(record.sub_records()) > 0: # type: ignore
                    self.object_map[record.level]= place_des

        elif isinstance(self.object_map[record.level-1], Fact):
            existing_place = self.gedcomx.places.by_name(record.value)
            if existing_place:
                self.object_map[record.level-1].place = PlaceReference(original=record.value, description=existing_place[0])
            else:
                place_des = PlaceDescription(names=[TextValue(value=record.value)])
                self.gedcomx.add_place_description(place_des)
                self.object_map[record.level-1].place = PlaceReference(original=record.value, description=place_des)
            self.object_map[record.level] = self.object_map[record.level-1].place
        elif isinstance(self.object_map[record.level-1], SourceDescription):
            if (place := self.gedcomx.places.by_name(record.value)) is not None:
                self.object_map[record.level-1].place = place
            else:
                place = PlaceDescription(names=[TextValue(value=record.value)])
                self.gedcomx.add_place_description(place)
                self.object_map[record.level-1].place = PlaceReference(original=record.value, description=place)
            gxobject = Note(text='Place: ' + record.value if record.value else 'WARNING: NOTE had no value')
            self.object_map[record.level-1].add_note(gxobject)

            self.object_map[record.level] = place
        elif isinstance(self.object_map[record.level-1], DocumentParsingContainer):
            existing = self.gedcomx.places.by_name(record.value)
            if existing:
                place = existing[0] if isinstance(existing, list) else existing
                self.object_map[record.level-1].sourceDescription.place = PlaceReference(original=record.value, description=place)
            else:
                place = PlaceDescription(names=[TextValue(value=record.value)])
                self.gedcomx.add_place_description(place)
                self.object_map[record.level-1].sourceDescription.place = PlaceReference(original=record.value, description=place)
            gxobject = Note(text='Place: ' + record.value if record.value else 'WARNING: NOTE had no value')
            self.object_map[record.level-1].sourceDescription.add_note(gxobject)
            self.object_map[record.level] = place
        else:
            self.convert_exception_dump(record=record)

    def handle_post(self, record: Element):
        if isinstance(self.object_map[record.level-1], Address):
            self.object_map[record.level-1].postalCode = self.clean_str(record.value)
        else:
            self.convert_exception_dump(record=record)

    def handle_publ(self, record: Element):
        if isinstance(self.object_map[record.level-1], SourceDescription):
            if record.value is None or record.value.strip() == '':
                #check for date
                if (date := record['DATE']) is not None:
                    self.object_map[record.level-1].published = date
            else:
                existing_agents = self.gedcomx.agents.by_name(record.value) if record.value else None
                if existing_agents:
                    gxobject = existing_agents[0]
                else:
                    gxobject = Agent(names=[TextValue(value=record.value)])
                    self.gedcomx.add_agent(gxobject)
                self.object_map[record.level-1].publisher = gxobject
                self.object_map[record.level] = gxobject
        else:
            self.convert_exception_dump(record=record)

    def handle_prob(self, record: Element):
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Fact(type=FactType.Probate)
            self.object_map[record.level-1].add_fact(gxobject)


            self.object_map[record.level] = gxobject
        else:
            self.convert_exception_dump(record=record)

    def handle_uid(self, record: Element):
        parent_obj = self.object_map.get(record.level-1)
        if record.value and hasattr(parent_obj, 'add_identifier'):
            gxobject = Identifier(values=[URI.from_url('UID:' + record.value)], type=IdentifierType.Primary) # type: ignore
            parent_obj.add_identifier(gxobject)
            self.object_map[record.level] = gxobject
        else:
            self.convert_exception_dump(record=record)

    def handle_refn(self, record: Element):
        if isinstance(self.object_map[record.level-1], (Person, SourceDescription)):
            gxobject = Identifier(values=[URI.from_url('Reference Number:' + record.value)] if record.value else [], type=IdentifierType.External) # type: ignore
            self.object_map[record.level-1].add_identifier(gxobject)
            self.object_map[record.level] = gxobject
        elif isinstance(self.object_map[record.level-1], Agent):
            gxobject = Identifier(values=[URI.from_url('Reference Number:' + record.value)] if record.value else [], type=IdentifierType.External) # type: ignore
            self.object_map[record.level-1].add_identifier(gxobject) #NOTE GC7

            self.object_map[record.level] = gxobject
        else:
            self.convert_exception_dump(record=record)

    def handle_repo(self, record: Element):
        if record.level == 0:
            if record.value is not None and self.gedcomx.agents.by_name(record.value):
                gxobject = self.gedcomx.agents.by_id(record.xref)

            else:
                gxobject = Agent(id=record.xref, names=[TextValue(value=record.value)] if record.value else [])
                self.gedcomx.add_agent(gxobject)
            self.object_map[record.level] = gxobject
        elif isinstance(self.object_map[record.level-1], SourceDescription):
            if self.gedcomx.agents.by_id(record.value) is not None:
                gxobject = self.gedcomx.agents.by_id(record.value)
                self.object_map[record.level-1].repository = gxobject
                self.object_map[record.level] = gxobject
            else:
                self.convert_exception_dump(record=record)
        else:
            self.convert_exception_dump(record=record)

    def handle_resi(self, record: Element):
        if isinstance(self.object_map[record.level-1], Person):
            gxobject = Fact(type=FactType.Residence)
            if record.value and record.value.strip() != '':
                gxobject.add_note(Note(text=record.value))
            self.object_map[record.level-1].add_fact(gxobject)


            self.object_map[record.level] = gxobject
        else:
            self.convert_exception_dump(record=record)

    def handle_rin(self, record: Element):
        if isinstance(self.object_map[record.level-1], SourceDescription):
            self.object_map[record.level-1].add_identifier(Identifier(type=IdentifierType.External, values=[URI.from_url(record.value)] if record.value else [])) # type: ignore
            self.object_map[record.level-1].add_note(Note(text=f"Source had RIN: of {record.value}"))
        elif isinstance(self.object_map[record.level-1], DocumentParsingContainer):
            self.object_map[record.level-1].sourceDescription.add_identifier(Identifier(type=IdentifierType.External, values=[URI.from_url(record.value)] if record.value else [])) # type: ignore
            self.object_map[record.level-1].sourceDescription.add_note(Note(text=f"Source had RIN: of {record.value}"))

        else:
            self.convert_exception_dump(record=record)

    def handle_sex(self, record: Element):
        if isinstance(self.object_map[record.level-1], Person):
            if record.value == 'M':
                gxobject = Gender(type=GenderType.Male)
            elif record.value == 'F':
                gxobject = Gender(type=GenderType.Female)
            else:
                gxobject = Gender(type=GenderType.Unknown)
            self.object_map[record.level-1].gender = gxobject
            self.object_map[record.level] = gxobject
        else:
            self.convert_exception_dump(record=record)

    def handle_sour(self, record: Element):

        if record.level == 0 and (record.tag in ['SOUR','OBJE','_WLNK']):
            if (gxobject := self.gedcomx.sourceDescriptions.by_id(record.xref)) is None:
                log.debug(f"SourceDescription with id: {record.xref} was not found. Creating a new SourceDescription")
                log.debug(f"Creating SourceDescription from {record.tag} {record.describe()}")
                gxobject = SourceDescription(id=record.xref if record.xref else None)
                self.object_map[record.level-1].add_source_description(gxobject)

            else:
                log.debug(f"Found SourceDescription with id:{record.xref}")
            self.object_map[record.level] = gxobject

        elif (add_method := getattr(self.object_map[record.level-1],"add_source_reference",None)) is not None:
            if (source_description := self.gedcomx.sourceDescriptions.by_id(record.value)) is not None:
                gxobject = SourceReference(descriptionId=record.value, description=source_description)
                add_method(gxobject)
                self.object_map[record.level] = gxobject
            else:
                if not record.value:
                    log.warning(f"Skipping SOUR/OBJE/_WLNK reference with empty value at level {record.level}")
                    return
                log.error(f"Could not find source with id: {record.value}, Creating Place Holder Description")
                gxobject = SourceDescription(id=record.value)
                gxobject._place_holder = True
                gxobject = SourceReference(descriptionId=record.value, description=gxobject)
                self.object_map[record.level] = gxobject

        elif record.tag == 'OBJE' and isinstance(self.object_map[record.level-1],SourceReference):
            if (source_description := self.gedcomx.sourceDescriptions.by_id(record.value)) is not None:
                gxobject = SourceReference(descriptionId=record.value, description=source_description)
                self.object_map[record.level-1].description.add_source_reference(gxobject)
                self.object_map[record.level] = gxobject
            else:
                self.convert_exception_dump(record=record)
        elif isinstance(self.object_map[record.level-1],Attribution):
            gxobject = Agent(names=[TextValue(value=record.value)])

            self.gedcomx.add_agent(gxobject)
            self.object_map[record.level-1].creator = gxobject
            self.object_map[record.level] = gxobject


        else:
            self.convert_exception_dump(record=record)

    def handle_stae(self, record: Element):
        if isinstance(self.object_map[record.level-1], Address):
            self.object_map[record.level-1].stateOrProvince = self.clean_str(record.value)
        else:
            raise ValueError(f"I do not know how to handle an 'STAE' tag for a {type(self.object_map[record.level-1])}")

    def handle_subm(self, record: Element):
        if record.level == 0:
            existing = self.gedcomx.agents.by_id(record.xref)
            if existing is not None:
                gxobject = existing
            else:
                gxobject = Agent(id=record.xref)
                self.gedcomx.add_agent(gxobject)

            if isinstance(self.object_map[record.level-1], Attribution):
                self.object_map[record.level-1].contributor = gxobject
            elif isinstance(self.object_map[record.level-1], (Gedcom5x, GedcomX)):
                pass  # agent already added to self.gedcomx above
            else:
                self.convert_exception_dump(record=record)
            self.object_map[record.level] = gxobject
        else:
            if (gxobject := self.gedcomx.agents.by_id(record.value)) is None:
                gxobject = Agent(id=record.value)
            self.gedcomx.add_agent(gxobject)
            self.object_map[record.level] = gxobject

    def handle_surn(self, record: Element):
        if isinstance(self.object_map[record.level-1], Name):
            surname = NamePart(value=record.value, type=NamePartType.Surname)
            self.object_map[record.level-1]._add_name_part(surname)
        else:
            self.convert_exception_dump(record=record)

    def handle_text(self, record: Element):
        if record.parent is not None and record.parent.tag == 'DATA':
            if isinstance(self.object_map[record.level-2], SourceReference):
                gxobject = TextValue(value=record.value)
                self.object_map[record.level-2].description.add_description(gxobject)

                self.object_map[record.level] = gxobject
        elif isinstance(self.object_map[record.level-1], SourceDescription):
            gxobject = Document(text=record.value)
            self.object_map[record.level-1].analysis = gxobject
        else:
            raise TagConversionError(record, self.object_map)

    def handle_titl(self, record: Element):
        if isinstance(self.object_map[record.level-1], SourceDescription):

            gxobject = TextValue(value=self.clean_str(record.value))
            self.object_map[record.level-1].add_title(gxobject)
            self.object_map[record.level] = gxobject

        elif (record.parent is not None) and (record.parent.tag == 'FILE') and isinstance(self.object_map[record.level-2], SourceDescription):
            gxobject = TextValue(value=record.value)
            self.object_map[record.level-2].add_title(gxobject)
            self.object_map[record.level] = gxobject
        elif self.object_map[record.level] and isinstance(self.object_map[record.level], Name):
            gxobject = NamePart(value=record.value, qualifiers=[NamePartQualifier.Title])

            self.object_map[record.level]._add_name_part(gxobject)
        else:
            log.warning("Could not parse TITLE")
           #log.debug(self.convert_exception_dump(record=record))

    def handle_tran(self, record: Element):
        """Handle TRAN (Translation/Transliteration) tags.

        GEDCOM 5.5.1 uses TRAN to provide alternate language/script forms of
        text-bearing records.  GedcomX represents these as additional NameForms
        (for Name records) or additional Notes/TextValues (for text records).
        The LANG child tag is processed by handle_lang, which sets the lang
        attribute on whatever this method stores in the object_map.
        """
        parent = self.object_map.get(record.level - 1)
        if isinstance(parent, Name):
            # Additional transliteration/translation of a name
            name_form = NameForm(fullText=record.value or "")
            parent.nameForms.append(name_form)
            self.object_map[record.level] = name_form
        elif isinstance(parent, Note):
            # Translation of a note — store as a sibling Note with lang set by LANG child
            gxobject = Note(text=self.clean_str(record.value or ""))
            # Add to the same container as the original note (go up one more level)
            grandparent = self.object_map.get(record.level - 2)
            if grandparent is not None and hasattr(grandparent, "add_note"):
                grandparent.add_note(gxobject)
            self.object_map[record.level] = gxobject
        elif isinstance(parent, TextValue):
            # Translation of a title or description
            gxobject = TextValue(value=self.clean_str(record.value or ""))
            self.object_map[record.level] = gxobject
        else:
            log.debug("handle_tran: unhandled parent type {} for {}", type(parent).__name__ if parent else "None", record.describe())

    def handle_lang(self, record: Element):
        """Set the lang attribute on the current object (child of TRAN/FONE)."""
        parent = self.object_map.get(record.level - 1)
        if parent is None:
            return
        if hasattr(parent, "lang"):
            parent.lang = record.value
        else:
            log.debug("handle_lang: parent {} has no lang attribute", type(parent).__name__)

    def handle_type(self, record: Element):
        # peek to see if event or fact
        parent_obj = self.object_map.get(record.level-1)
        if record.parent is not None and record.parent.tag == 'FORM':
            level0 = self.object_map.get(0)
            if isinstance(level0, DocumentParsingContainer):
                if not level0.sourceDescription.mediaType:
                    level0.sourceDescription.mediaType = record.value
            elif isinstance(level0, SourceDescription):
                if not level0.mediaType:
                    level0.mediaType = record.value
            return
        if isinstance(parent_obj, Event):
            if EventType.guess(record.value):
                parent_obj.type = EventType.guess(record.value)
            else:
                log.warning(f"Could not determine type of event with value '{record.value}'")
            parent_obj.add_note(Note(text=self.clean_str(record.value)))
        elif isinstance(parent_obj, Fact):
            if not parent_obj.type:
                parent_obj.type = FactType.guess(record.value)
        elif isinstance(parent_obj, Identifier):
            parent_obj.values.append(self.clean_str(record.value))
            parent_obj.type = IdentifierType.Other  # type: ignore
        elif isinstance(parent_obj, Document):
            parent_obj.values.append(self.clean_str(record.value))
            parent_obj.type = IdentifierType.Other  # type: ignore
        elif isinstance(parent_obj, DocumentParsingContainer):
            container = parent_obj
            _rt_map = {
                'image': ResourceType.DigitalArtifact,
                'photo': ResourceType.DigitalArtifact,
                'video': ResourceType.DigitalArtifact,
                'audio': ResourceType.DigitalArtifact,
                'document': ResourceType.PhysicalArtifact,
                'book': ResourceType.PhysicalArtifact,
                'record': ResourceType.Record,
                'collection': ResourceType.Collection,
            }
            if record.value:
                container.sourceDescription.resourceType = _rt_map.get(record.value.lower(), ResourceType.DigitalArtifact)
            self.object_map[record.level] = container

        elif isinstance(parent_obj, Name):
            parent_obj.type = GedcomConverter.type_name_type.get(record.value, NameType.Other)
        elif parent_obj is None:
            log.warning("TYPE at level {} has no parent object in stack; ignoring", record.level)
        else:
            raise TagConversionError(record, self.object_map)

    def handle__url(self, record: Element):
        if isinstance(self.object_map[record.level-2], SourceDescription):
            self.object_map[record.level-2].about = URI.from_url(record.value) if record.value else None
        else:
            raise ValueError(f"Could not handle '_URL' tag in record {record.describe()}, last stack object {self.object_map[record.level-1]}")

    def handle_www(self, record: Element):
        if isinstance(self.object_map[record.level-1], Agent):
            self.object_map[record.level-1].homepage = self.clean_str(record.value)
        elif isinstance(self.object_map[record.level-2], SourceReference):
            self.object_map[record.level-2].description.add_identifier(Identifier(values=[URI.from_url(record.value)] if record.value else []))
        else:
            raise ValueError(f"Could not handle 'WWW' tag in record {record.describe()}, last stack object {self.object_map[record.level-1]}")
