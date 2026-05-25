"""
======================================================================
 Project: gedcomtools
 File:    gedcom7/gxtog7.py
 Purpose: GedcomX → GEDCOM 7 converter.

 Created: 2026-04-07
 Updated: 2026-04-12 — parent-pair FAM search: O(1) direct lookup for the
                        common two-parent case; O(n²) fallback only for >2 parents
           2026-04-12 — single-parent FAM fallback: score candidates by number of
                        matching parents; avoids assigning a child to a FAM from a
                        different partnership when a parent belongs to multiple families
           2026-04-15 — release refresh for v0.8.2b4 docs/build packaging
======================================================================

Converts a populated :class:`~gedcomtools.gedcomx.gedcomx.GedcomX`
object graph into a list of :class:`~gedcomtools.gedcom7.structure.GedcomStructure`
nodes that can be written to a GEDCOM 7 file via
:class:`~gedcomtools.gedcom7.writer.Gedcom7Writer`.

Usage::

    from gedcomtools.gedcomx.gedcomx import GedcomX
    from gedcomtools.gedcom7.gxtog7 import GedcomXConverter

    gx = GedcomX.from_dict(data)
    converter = GedcomXConverter()
    records = converter.convert(gx)

    from gedcomtools.gedcom7.writer import Gedcom7Writer
    Gedcom7Writer().write(records, "output.ged")

Alternatively use the convenience methods::

    # From a GedcomX object
    g7 = gx.to_gedcom7()
    g7.write("output.ged")

    # From a Gedcom7 object
    g7b = Gedcom7.from_gedcomx(gx)

Conversion phases
-----------------
1. Assign GEDCOM 7 xrefs to all GX objects (persons → @I1@, sources →
   @S1@, agents → @R1@/@SUBM1@, families → @F1@).
2. Analyse GX relationships to reconstruct GEDCOM FAM groupings; create
   implicit FAMs where no Couple relationship exists for a parent pair.
3. Build GEDCOM 7 records in canonical order:
   HEAD → REPO → SUBM → SOUR → INDI → FAM → TRLR.

Data loss
---------
GX constructs with no direct GEDCOM 7 equivalent are tracked in
:attr:`conversion_warnings` (tag → occurrence count), mirroring the
same pattern used by :class:`~gedcomtools.gedcom7.g7togx.Gedcom7Converter`.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from .structure import GedcomStructure
from ..glog import get_logger
from ..gedcomx.gedcomx import GedcomX

if TYPE_CHECKING:
    from ..gedcomx.fact import Fact
    from ..gedcomx.name import Name, NameForm
    from ..gedcomx.note import Note
    from ..gedcomx.source_reference import SourceReference
    from ..gedcomx.address import Address

log = get_logger("gxtog7")

# ---------------------------------------------------------------------------
# Reverse type-mapping tables  (inverted from gedcom7/g7togx.py)
# ---------------------------------------------------------------------------

# GedcomX FactType URI → GEDCOM 7 individual-event / attribute tag
_FACT_TO_INDI_TAG: Dict[str, str] = {
    "http://gedcomx.org/Birth":             "BIRT",
    "http://gedcomx.org/Christening":       "CHR",
    "http://gedcomx.org/Death":             "DEAT",
    "http://gedcomx.org/Burial":            "BURI",
    "http://gedcomx.org/Cremation":         "CREM",
    "http://gedcomx.org/Adoption":          "ADOP",
    "http://gedcomx.org/Baptism":           "BAPM",
    "http://gedcomx.org/BarMitzvah":        "BARM",
    "http://gedcomx.org/BatMitzvah":        "BASM",
    "http://gedcomx.org/Blessing":          "BLES",
    "http://gedcomx.org/Census":            "CENS",
    "http://gedcomx.org/Confirmation":      "CONF",
    "http://gedcomx.org/Emigration":        "EMIG",
    "http://gedcomx.org/Graduation":        "GRAD",
    "http://gedcomx.org/Immigration":       "IMMI",
    "http://gedcomx.org/Naturalization":    "NATU",
    "http://gedcomx.org/Ordination":        "ORDN",
    "http://gedcomx.org/Probate":           "PROB",
    "http://gedcomx.org/Retirement":        "RETI",
    "http://gedcomx.org/Will":              "WILL",
    "http://gedcomx.org/Residence":         "RESI",
    "http://gedcomx.org/Occupation":        "OCCU",
    "http://gedcomx.org/OfficialPosition":  "TITL",
    "http://gedcomx.org/Religion":          "RELI",
    "http://gedcomx.org/Nationality":       "NATI",
}

# GedcomX FactType URI → GEDCOM 7 family-event tag
_FACT_TO_FAM_TAG: Dict[str, str] = {
    "http://gedcomx.org/Marriage":          "MARR",
    "http://gedcomx.org/Divorce":           "DIV",
    "http://gedcomx.org/Engagement":        "ENGA",
    "http://gedcomx.org/MarriageBanns":     "MARB",
    "http://gedcomx.org/MarriageContract":  "MARC",
    "http://gedcomx.org/MarriageLicense":   "MARL",
    "http://gedcomx.org/Separation":        "MARS",
    "http://gedcomx.org/Annulment":         "ANUL",
    "http://gedcomx.org/DivorceFiling":     "DIVF",
}

# GedcomX NameType URI → GEDCOM 7 NAME TYPE code
_NAME_TYPE_TO_CODE: Dict[str, str] = {
    "http://gedcomx.org/BirthName":    "BIRTH",
    "http://gedcomx.org/MarriedName":  "MARRIED",
    "http://gedcomx.org/AlsoKnownAs":  "AKA",
    "http://gedcomx.org/Nickname":     "NICK",
    "http://gedcomx.org/AdoptiveName": "ADOPTED",
    "http://gedcomx.org/FormalName":   "FORMAL",
    "http://gedcomx.org/ReligiousName":"RELIGIOUS",
}

# GedcomX GenderType URI → GEDCOM 7 SEX code
_GENDER_TO_SEX: Dict[str, str] = {
    "http://gedcomx.org/Male":      "M",
    "http://gedcomx.org/Female":    "F",
    "http://gedcomx.org/Intersex":  "X",
    "http://gedcomx.org/Unknown":   "U",
}

# GedcomX ParentChild FactType URI → GEDCOM 7 PEDI value
_PEDI_FACT_TO_VALUE: Dict[str, str] = {
    "http://gedcomx.org/Adoption":              "ADOPTED",
    "http://gedcomx.org/FosterParent":          "FOSTER",
    "http://gedcomx.org/SealingChildToParents": "SEALING",
}

_COUPLE_URI    = "http://gedcomx.org/Couple"
_PC_URI        = "http://gedcomx.org/ParentChild"
_BIRTH_NAME_URI = "http://gedcomx.org/BirthName"

# Month index → GEDCOM month abbreviation
_MONTH_ABB = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"]


# ---------------------------------------------------------------------------
# Converter
# ---------------------------------------------------------------------------

class GedcomXConverter:
    """Convert a :class:`~gedcomtools.gedcomx.gedcomx.GedcomX` object to a
    list of GEDCOM 7 :class:`~gedcomtools.gedcom7.structure.GedcomStructure`
    records.

    Usage::

        converter = GedcomXConverter()
        records = converter.convert(gx)
        Gedcom7Writer().write(records, "output.ged")
    """

    def __init__(self) -> None:
        self._records: List[GedcomStructure] = []
        self._gx: GedcomX = GedcomX()

        # GX object id → assigned GEDCOM xref string
        self._person_xref: Dict[str, str] = {}
        self._source_xref: Dict[str, str] = {}
        self._agent_xref:  Dict[str, str] = {}

        # Agent ids that are repositories (referenced by SourceDescription.repository)
        self._repo_agents: set = set()

        # person_id → list of FAM xrefs the person appears in as a spouse
        self._person_fams: Dict[str, List[str]] = {}

        # child person_id → (fam_xref, pedi_value | None)
        self._person_famc: Dict[str, Tuple[str, Optional[str]]] = {}

        # fam_xref → family data dict
        # Keys: person1_id, person2_id, couple_rel, children [(child_id, pedi)]
        self._fam_data: Dict[str, dict] = {}

        self._unhandled: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def convert(self, source: "GedcomX") -> List[GedcomStructure]:
        """Convert *source* and return a list of GEDCOM 7 structure records.

        Args:
            source: A populated :class:`~gedcomtools.gedcomx.gedcomx.GedcomX`
                instance.

        Returns:
            A list of top-level :class:`~gedcomtools.gedcom7.structure.GedcomStructure`
            nodes (HEAD … TRLR) ready for :class:`~gedcomtools.gedcom7.writer.Gedcom7Writer`.
        """
        self._gx = source
        self._records = []
        self._person_xref = {}
        self._source_xref = {}
        self._agent_xref  = {}
        self._repo_agents = set()
        self._person_fams = {}
        self._person_famc = {}
        self._fam_data    = {}
        self._unhandled   = {}

        self._assign_xrefs()       # Phase 1
        self._analyze_families()   # Phase 2
        self._build_head()         # Phase 3 — records
        self._build_repo_records()
        self._build_subm_records()
        self._build_sour_records()
        self._build_indi_records()
        self._build_fam_records()
        self._records.append(GedcomStructure(level=0, tag="TRLR"))
        return list(self._records)

    @property
    def conversion_warnings(self) -> Dict[str, int]:
        """Return a dict of unconverted GX constructs and their occurrence counts."""
        return dict(self._unhandled)

    # ------------------------------------------------------------------
    # Phase 1 — Assign xrefs
    # ------------------------------------------------------------------

    def _assign_xrefs(self) -> None:
        gx = self._gx

        for i, person in enumerate(gx.persons, 1):
            self._person_xref[person.id] = f"@I{i}@"

        for i, sd in enumerate(gx.sourceDescriptions, 1):
            self._source_xref[sd.id] = f"@S{i}@"

        # Identify agents that are repositories (cited via SourceDescription.repository)
        for sd in gx.sourceDescriptions:
            if sd.repository:
                ref_id = self._ref_id(sd.repository)
                if ref_id:
                    self._repo_agents.add(ref_id)

        repo_n = subm_n = 0
        for agent in gx.agents:
            if agent.id in self._repo_agents:
                repo_n += 1
                self._agent_xref[agent.id] = f"@R{repo_n}@"
            else:
                subm_n += 1
                self._agent_xref[agent.id] = f"@SUBM{subm_n}@"

    # ------------------------------------------------------------------
    # Phase 2 — Reconstruct FAM groupings
    # ------------------------------------------------------------------

    def _analyze_families(self) -> None:
        """Build FAM records from Couple and ParentChild GX relationships."""
        gx = self._gx
        fam_counter = 0

        # couple frozenset{p1_id, p2_id} → fam_xref (for child lookup)
        couple_key_xref: Dict[frozenset, str] = {}

        # Pass 1: Couple relationships → FAMs
        for rel in gx.relationships:
            if self._type_uri(rel) != _COUPLE_URI:
                continue
            fam_counter += 1
            fam_xref = f"@F{fam_counter}@"
            p1_id = self._ref_id(rel.person1)
            p2_id = self._ref_id(rel.person2)

            key = frozenset(pid for pid in (p1_id, p2_id) if pid)
            if key:
                couple_key_xref[key] = fam_xref

            self._fam_data[fam_xref] = {
                "fam_xref":   fam_xref,
                "person1_id": p1_id,
                "person2_id": p2_id,
                "couple_rel": rel,
                "children":   [],
            }
            for pid in (p1_id, p2_id):
                if pid:
                    self._person_fams.setdefault(pid, []).append(fam_xref)

        # Pass 2: ParentChild relationships → assign children to FAMs
        # Group by child so we can consider both parents together
        child_rels: Dict[str, list] = {}
        for rel in gx.relationships:
            if self._type_uri(rel) != _PC_URI:
                continue
            child_id = self._ref_id(rel.person2)
            if child_id:
                child_rels.setdefault(child_id, []).append(rel)

        for child_id, rels in child_rels.items():
            parent_ids = [self._ref_id(r.person1) for r in rels
                          if self._ref_id(r.person1)]
            pedi_value = next(
                (pv for r in rels for pv in [self._extract_pedi(r)] if pv),
                None,
            )

            found_fam: Optional[str] = None

            # Try to find a FAM matching two parents.
            # Common case: exactly two parents — one O(1) dict lookup.
            # Rare case: >2 parents — fall back to scanning pairs.
            if len(parent_ids) >= 2:
                found_fam = couple_key_xref.get(frozenset(parent_ids[:2]))
                if not found_fam and len(parent_ids) > 2:
                    for i, pid_i in enumerate(parent_ids):
                        for j in range(i + 1, len(parent_ids)):
                            found_fam = couple_key_xref.get(frozenset([pid_i, parent_ids[j]]))
                            if found_fam:
                                break
                        if found_fam:
                            break

            # Fall back: find the FAM that matches the most of this child's
            # parents (avoids assigning a child to a FAM from a different
            # partnership when a parent belongs to more than one family).
            if not found_fam and parent_ids:
                parent_id_set = set(parent_ids)
                best_fam: Optional[str] = None
                best_score = 0
                for pid in parent_ids:
                    for fam_xref in self._person_fams.get(pid, []):
                        fdata = self._fam_data[fam_xref]
                        score = sum(
                            1 for p in (fdata["person1_id"], fdata["person2_id"])
                            if p in parent_id_set
                        )
                        if score > best_score:
                            best_score = score
                            best_fam = fam_xref
                found_fam = best_fam

            # Last resort: create an implicit FAM for the parent(s)
            if not found_fam and parent_ids:
                fam_counter += 1
                found_fam = f"@F{fam_counter}@"
                p1 = parent_ids[0]
                p2 = parent_ids[1] if len(parent_ids) > 1 else None
                self._fam_data[found_fam] = {
                    "fam_xref":   found_fam,
                    "person1_id": p1,
                    "person2_id": p2,
                    "couple_rel": None,
                    "children":   [],
                }
                for pid in (p1, p2):
                    if pid:
                        self._person_fams.setdefault(pid, []).append(found_fam)

            if found_fam:
                self._fam_data[found_fam]["children"].append((child_id, pedi_value))
                self._person_famc[child_id] = (found_fam, pedi_value)

    # ------------------------------------------------------------------
    # Phase 3 — Build records
    # ------------------------------------------------------------------

    def _build_head(self) -> None:
        head = GedcomStructure(level=0, tag="HEAD")
        self._records.append(head)

        gedc = GedcomStructure(level=1, tag="GEDC", parent=head)
        GedcomStructure(level=2, tag="VERS", payload="7.0", parent=gedc)

        # SUBM — first non-repository agent
        for agent in self._gx.agents:
            if agent.id not in self._repo_agents:
                subm_xref = self._agent_xref.get(agent.id)
                if subm_xref:
                    GedcomStructure(
                        level=1, tag="SUBM", payload=subm_xref,
                        payload_is_pointer=True, parent=head,
                    )
                break

        # Creation date from GX attribution
        if self._gx.attribution and self._gx.attribution.created:
            GedcomStructure(
                level=1, tag="DATE",
                payload=str(self._gx.attribution.created),
                parent=head,
            )

    def _build_repo_records(self) -> None:
        for agent in self._gx.agents:
            if agent.id not in self._repo_agents:
                continue
            xref = self._agent_xref.get(agent.id)
            if not xref:
                continue
            repo = GedcomStructure(level=0, tag="REPO", xref_id=xref)
            self._records.append(repo)

            if agent.names:
                name_val = self._text_value(agent.names[0])
                GedcomStructure(level=1, tag="NAME", payload=name_val, parent=repo)
            if agent.addresses:
                self._build_addr(repo, agent.addresses[0])
            for phone in agent.phones:
                val = self._uri_value(phone)
                GedcomStructure(level=1, tag="PHON",
                                payload=val[4:] if val.startswith("tel:") else val,
                                parent=repo)
            for email in agent.emails:
                val = self._uri_value(email)
                GedcomStructure(level=1, tag="EMAIL",
                                payload=val[7:] if val.startswith("mailto:") else val,
                                parent=repo)
            if agent.homepage:
                GedcomStructure(level=1, tag="WWW",
                                payload=self._uri_value(agent.homepage),
                                parent=repo)

    def _build_subm_records(self) -> None:
        for agent in self._gx.agents:
            if agent.id in self._repo_agents:
                continue
            xref = self._agent_xref.get(agent.id)
            if not xref:
                continue
            subm = GedcomStructure(level=0, tag="SUBM", xref_id=xref)
            self._records.append(subm)

            if agent.names:
                name_val = self._text_value(agent.names[0])
                GedcomStructure(level=1, tag="NAME", payload=name_val, parent=subm)
            if agent.addresses:
                self._build_addr(subm, agent.addresses[0])

    def _build_sour_records(self) -> None:
        for sd in self._gx.sourceDescriptions:
            xref = self._source_xref.get(sd.id)
            if not xref:
                continue
            sour = GedcomStructure(level=0, tag="SOUR", xref_id=xref)
            self._records.append(sour)

            if sd.titles:
                GedcomStructure(level=1, tag="TITL",
                                payload=self._text_value(sd.titles[0]),
                                parent=sour)

            # Author/publication/abbreviation were encoded as notes by g7togx
            for note in sd.notes:
                text = note.text or ""
                if text.startswith("Author: "):
                    GedcomStructure(level=1, tag="AUTH", payload=text[8:], parent=sour)
                elif text.startswith("Publication: "):
                    GedcomStructure(level=1, tag="PUBL", payload=text[13:], parent=sour)
                elif text.startswith("Abbreviation: "):
                    GedcomStructure(level=1, tag="ABBR", payload=text[14:], parent=sour)
                elif text:
                    GedcomStructure(level=1, tag="NOTE", payload=text, parent=sour)

            if sd.repository:
                repo_id   = self._ref_id(sd.repository)
                repo_xref = self._agent_xref.get(repo_id) if repo_id else None
                if repo_xref:
                    GedcomStructure(level=1, tag="REPO", payload=repo_xref,
                                    payload_is_pointer=True, parent=sour)

    def _build_indi_records(self) -> None:
        for person in self._gx.persons:
            xref = self._person_xref.get(person.id)
            if not xref:
                continue
            indi = GedcomStructure(level=0, tag="INDI", xref_id=xref)
            self._records.append(indi)

            # SEX
            if person.gender and person.gender.type:
                sex_code = _GENDER_TO_SEX.get(self._enum_uri(person.gender.type))
                if sex_code:
                    GedcomStructure(level=1, tag="SEX", payload=sex_code, parent=indi)

            # NAME(s)
            for name in person.names:
                self._build_name(indi, name)

            # Facts / events / attributes
            for fact in person.facts:
                self._build_indi_fact(indi, fact)

            # Notes
            for note in person.notes:
                self._build_note(indi, note)

            # Source citations
            for sr in person.sources:
                self._build_sour_ref(indi, sr)

            # FAMS links
            for fam_xref in self._person_fams.get(person.id, []):
                GedcomStructure(level=1, tag="FAMS", payload=fam_xref,
                                payload_is_pointer=True, parent=indi)

            # FAMC link
            famc_info = self._person_famc.get(person.id)
            if famc_info:
                famc_xref, pedi_value = famc_info
                famc_node = GedcomStructure(level=1, tag="FAMC", payload=famc_xref,
                                            payload_is_pointer=True, parent=indi)
                if pedi_value:
                    GedcomStructure(level=2, tag="PEDI", payload=pedi_value,
                                    parent=famc_node)

    def _build_fam_records(self) -> None:
        for fam_xref, fdata in self._fam_data.items():
            fam = GedcomStructure(level=0, tag="FAM", xref_id=fam_xref)
            self._records.append(fam)

            p1_id = fdata["person1_id"]
            p2_id = fdata["person2_id"]
            husb_id, wife_id = self._assign_husb_wife(p1_id, p2_id)

            if husb_id:
                husb_xref = self._person_xref.get(husb_id)
                if husb_xref:
                    GedcomStructure(level=1, tag="HUSB", payload=husb_xref,
                                    payload_is_pointer=True, parent=fam)
            if wife_id:
                wife_xref = self._person_xref.get(wife_id)
                if wife_xref:
                    GedcomStructure(level=1, tag="WIFE", payload=wife_xref,
                                    payload_is_pointer=True, parent=fam)

            for child_id, _pedi in fdata["children"]:
                child_xref = self._person_xref.get(child_id)
                if child_xref:
                    GedcomStructure(level=1, tag="CHIL", payload=child_xref,
                                    payload_is_pointer=True, parent=fam)

            couple_rel = fdata.get("couple_rel")
            if couple_rel:
                for fact in couple_rel.facts:
                    self._build_fam_fact(fam, fact)
                for note in couple_rel.notes:
                    self._build_note(fam, note)
                for sr in couple_rel.sources:
                    self._build_sour_ref(fam, sr)

    # ------------------------------------------------------------------
    # Structure builders
    # ------------------------------------------------------------------

    def _build_name(self, parent: GedcomStructure, name: "Name") -> None:
        """Build a NAME structure and its substructures."""
        if not name.nameForms:
            GedcomStructure(level=1, tag="NAME", payload="", parent=parent)
            return

        primary = name.nameForms[0]
        payload = self._name_form_payload(primary)
        name_node = GedcomStructure(level=1, tag="NAME", payload=payload, parent=parent)

        # TYPE — only emit when not the default BirthName
        if name.type:
            type_uri = self._enum_uri(name.type)
            if type_uri != _BIRTH_NAME_URI:
                code = _NAME_TYPE_TO_CODE.get(type_uri)
                if code:
                    GedcomStructure(level=2, tag="TYPE", payload=code, parent=name_node)

        # NPFX / GIVN / SURN / NSFX substructures from name parts
        if primary.parts:
            _PART_URI_TO_TAG = {
                "http://gedcomx.org/Prefix":  "NPFX",
                "http://gedcomx.org/Given":   "GIVN",
                "http://gedcomx.org/Surname": "SURN",
                "http://gedcomx.org/Suffix":  "NSFX",
            }
            for part in primary.parts:
                if not part.type or not part.value:
                    continue
                tag = _PART_URI_TO_TAG.get(self._enum_uri(part.type))
                if tag:
                    GedcomStructure(level=2, tag=tag, payload=part.value,
                                    parent=name_node)

        # Additional forms as TRAN sub-structures
        for form in name.nameForms[1:]:
            if not form.lang:
                continue
            tran = GedcomStructure(level=2, tag="TRAN",
                                   payload=self._name_form_payload(form),
                                   parent=name_node)
            GedcomStructure(level=3, tag="LANG", payload=form.lang, parent=tran)

    def _name_form_payload(self, form: "NameForm") -> str:
        """Build the slash-notation NAME payload from a NameForm."""
        if not form.parts:
            return form.fullText or ""

        prefix = given = surname = suffix = ""
        for part in form.parts:
            if not part.type or not part.value:
                continue
            uri = self._enum_uri(part.type)
            if uri == "http://gedcomx.org/Prefix":
                prefix = part.value
            elif uri == "http://gedcomx.org/Given":
                given = part.value
            elif uri == "http://gedcomx.org/Surname":
                surname = part.value
            elif uri == "http://gedcomx.org/Suffix":
                suffix = part.value

        tokens = []
        if prefix:
            tokens.append(prefix)
        if given:
            tokens.append(given)
        if surname:
            tokens.append(f"/{surname}/")
        if suffix:
            tokens.append(suffix)

        return " ".join(tokens) if tokens else (form.fullText or "")

    def _build_indi_fact(self, parent: GedcomStructure, fact: "Fact") -> None:
        """Build an individual fact / event / attribute structure."""
        if not fact.type:
            return

        type_uri = self._enum_uri(fact.type)
        tag = _FACT_TO_INDI_TAG.get(type_uri)

        if tag:
            # Attribute facts carry their value as the tag payload (OCCU, TITL…)
            # Event facts use an empty payload or "Y" if no detail is available.
            if fact.value and not fact.date and not fact.place and not fact.notes:
                payload = fact.value
            else:
                payload = fact.value or ""
            fact_node = GedcomStructure(level=1, tag=tag, payload=payload,
                                        parent=parent)
            self._add_event_detail(fact_node, fact)
        else:
            # Unknown/custom → EVEN with TYPE
            self._note_unhandled(f"FactType:{type_uri}")
            fact_node = GedcomStructure(level=1, tag="EVEN",
                                        payload=fact.value or "", parent=parent)
            label = type_uri.rsplit("/", 1)[-1] if "/" in type_uri else type_uri
            GedcomStructure(level=2, tag="TYPE", payload=label, parent=fact_node)
            self._add_event_detail(fact_node, fact)

        for note in fact.notes:
            self._build_note(fact_node, note)
        for sr in fact.sources:
            self._build_sour_ref(fact_node, sr)

    def _build_fam_fact(self, parent: GedcomStructure, fact: "Fact") -> None:
        """Build a family event structure."""
        if not fact.type:
            return

        type_uri = self._enum_uri(fact.type)
        tag = _FACT_TO_FAM_TAG.get(type_uri)

        if tag:
            fact_node = GedcomStructure(level=1, tag=tag,
                                        payload=fact.value or "", parent=parent)
            self._add_event_detail(fact_node, fact)
        else:
            self._note_unhandled(f"FamFactType:{type_uri}")
            fact_node = GedcomStructure(level=1, tag="EVEN",
                                        payload=fact.value or "", parent=parent)
            label = type_uri.rsplit("/", 1)[-1] if "/" in type_uri else type_uri
            GedcomStructure(level=2, tag="TYPE", payload=label, parent=fact_node)
            self._add_event_detail(fact_node, fact)

        for note in fact.notes:
            self._build_note(fact_node, note)
        for sr in fact.sources:
            self._build_sour_ref(fact_node, sr)

    def _add_event_detail(self, parent: GedcomStructure, fact: "Fact") -> None:
        """Append DATE and PLAC substructures to an event node."""
        lv = parent.level + 1
        if fact.date:
            date_str = self._gx_date_to_g7(fact.date)
            if date_str:
                GedcomStructure(level=lv, tag="DATE", payload=date_str, parent=parent)
        if fact.place and fact.place.original:
            GedcomStructure(level=lv, tag="PLAC", payload=fact.place.original,
                            parent=parent)

    def _build_note(self, parent: GedcomStructure, note: "Note") -> None:
        """Append an inline NOTE structure."""
        text = ""
        if note.subject and note.text:
            text = f"{note.subject}: {note.text}"
        elif note.subject:
            text = note.subject
        elif note.text:
            text = note.text
        if text:
            GedcomStructure(level=parent.level + 1, tag="NOTE",
                            payload=text, parent=parent)

    def _build_sour_ref(self, parent: GedcomStructure,
                        sr: "SourceReference") -> None:
        """Append a SOUR citation pointer."""
        desc_id = getattr(sr, "descriptionId", None)
        if not desc_id:
            desc_id = self._ref_id(getattr(sr, "description", None))

        sour_xref = self._source_xref.get(desc_id) if desc_id else None
        if not sour_xref:
            self._note_unhandled(f"SOUR:{desc_id}")
            return

        lv = parent.level + 1
        sour_node = GedcomStructure(level=lv, tag="SOUR", payload=sour_xref,
                                    payload_is_pointer=True, parent=parent)

        for qual in getattr(sr, "qualifiers", []):
            name_val = self._enum_uri(qual.name) if qual.name else ""
            if name_val.endswith("/Page"):
                GedcomStructure(level=lv + 1, tag="PAGE",
                                payload=qual.value or "", parent=sour_node)

    def _build_addr(self, parent: GedcomStructure, addr: "Address") -> None:
        """Append ADDR and its field substructures."""
        raw = getattr(addr, "_raw_value", None) or ""
        addr_node = GedcomStructure(level=parent.level + 1, tag="ADDR",
                                    payload=raw, parent=parent)
        lv = addr_node.level + 1
        fields = [
            ("street",          "ADR1"),
            ("street2",         "ADR2"),
            ("city",            "CITY"),
            ("stateOrProvince", "STAE"),
            ("postalCode",      "POST"),
            ("country",         "CTRY"),
        ]
        for attr, tag in fields:
            val = getattr(addr, attr, None)
            if val:
                GedcomStructure(level=lv, tag=tag, payload=val, parent=addr_node)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _assign_husb_wife(
        self,
        p1_id: Optional[str],
        p2_id: Optional[str],
    ) -> Tuple[Optional[str], Optional[str]]:
        """Return (husb_id, wife_id) based on person genders.

        Defaults to (person1, person2) order when genders are ambiguous.
        """
        if not p1_id:
            return None, p2_id
        if not p2_id:
            return p1_id, None

        def _sex(person_id: str) -> Optional[str]:
            p = self._gx.persons.by_id(person_id)
            if not p or not p.gender or not p.gender.type:
                return None
            return _GENDER_TO_SEX.get(self._enum_uri(p.gender.type))

        s1, s2 = _sex(p1_id), _sex(p2_id)
        if s1 == "F" and s2 != "F":
            return p2_id, p1_id   # swap: female goes to WIFE
        return p1_id, p2_id       # default order

    def _extract_pedi(self, rel) -> Optional[str]:
        """Return the GEDCOM PEDI value encoded in a ParentChild fact, or None."""
        for fact in rel.facts:
            if fact.type:
                pv = _PEDI_FACT_TO_VALUE.get(self._enum_uri(fact.type))
                if pv:
                    return pv
        return None

    def _type_uri(self, rel) -> str:
        """Return the relationship type URI, or ''."""
        if rel.type is None:
            return ""
        return self._enum_uri(rel.type)

    def _enum_uri(self, enum_val) -> str:
        """Extract the URI string from an enum value or plain string."""
        if enum_val is None:
            return ""
        if hasattr(enum_val, "value"):
            return str(enum_val.value)
        return str(enum_val)

    def _ref_id(self, ref) -> Optional[str]:
        """Extract the GX object id from a Resource reference or direct object."""
        if ref is None:
            return None
        # Direct GedcomXModel object with an id attribute (but not a Resource wrapper)
        if hasattr(ref, "id") and not hasattr(ref, "resource"):
            return ref.id
        # Resource wrapper: Resource(resource=URI(fragment="..."))
        if hasattr(ref, "resource"):
            uri = ref.resource
            if hasattr(uri, "fragment") and uri.fragment:
                return uri.fragment
            if hasattr(uri, "value") and uri.value:
                val = str(uri.value)
                return val.split("#", 1)[1] if "#" in val else val
        return None

    def _text_value(self, obj) -> str:
        """Return the text from a TextValue, URI, or str-like object."""
        if hasattr(obj, "value"):
            return str(obj.value) if obj.value is not None else ""
        return str(obj)

    def _uri_value(self, uri_obj) -> str:
        """Return the string value of a URI object."""
        if hasattr(uri_obj, "value"):
            return str(uri_obj.value) if uri_obj.value is not None else ""
        return str(uri_obj)

    def _gx_date_to_g7(self, date) -> str:
        """Convert a GX :class:`~gedcomtools.gedcomx.date.Date` to a G7 date string.

        Prefers ``original`` (the raw GEDCOM date as ingested) over ``formal``
        (the GedcomX formal ISO-style representation).
        """
        if date.original:
            return str(date.original)
        if date.formal:
            return self._formal_to_g7(str(date.formal))
        return ""

    def _formal_to_g7(self, formal: str) -> str:
        """Convert a GedcomX formal date string to a GEDCOM date grammar string."""

        def iso_to_ged(s: str) -> str:
            s = s.lstrip("+")
            parts = s.split("-")
            try:
                if len(parts) == 3:
                    y, m, d = parts
                    mon = _MONTH_ABB[int(m) - 1]
                    return f"{d.lstrip('0') or d} {mon} {y}"
                if len(parts) == 2:
                    y, m = parts
                    mon = _MONTH_ABB[int(m) - 1]
                    return f"{mon} {y}"
            except (ValueError, IndexError):
                pass
            return s

        # Approximate: A1900 or A1900-01-15
        if formal.startswith("A") and not formal.startswith("A/"):
            return f"ABT {iso_to_ged(formal[1:])}"
        # Before: A/1920 or /1920
        if formal.startswith(("A/", "/")):
            date_part = formal.lstrip("A").lstrip("/")
            return f"BEF {iso_to_ged(date_part)}"
        # After: 1915/
        if formal.endswith("/"):
            return f"AFT {iso_to_ged(formal.rstrip('/'))}"
        # Range: [1880/1900]
        if formal.startswith("[") and "/" in formal:
            inner = formal.strip("[]")
            halves = inner.split("/", 1)
            d1, d2 = halves[0], halves[1] if len(halves) > 1 else ""
            if d1 and d2:
                return f"BET {iso_to_ged(d1)} AND {iso_to_ged(d2)}"
            if d2:
                return f"BEF {iso_to_ged(d2)}"
            if d1:
                return f"AFT {iso_to_ged(d1)}"
        return iso_to_ged(formal)

    def _note_unhandled(self, key: str) -> None:
        self._unhandled[key] = self._unhandled.get(key, 0) + 1
