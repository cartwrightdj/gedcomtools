"""
======================================================================
 Project: gedcomtools
 File:    gedcom7/g7togx.py
 Author:  David J. Cartwright
 Purpose: GEDCOM 7 → GedcomX converter.

          Consumes the pre-assembled Detail objects produced by
          gedcom7/models.py and populates a GedcomX object graph.
          No level-tracking stack is needed because the Detail objects
          already aggregate all sub-structures into typed Python fields.

 Created: 2026-03-24
======================================================================
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional

from ..glog import get_logger

if TYPE_CHECKING:
    from ..gedcom7.gedcom7 import Gedcom7
    from ..gedcomx.agent import Agent
    from ..gedcomx.fact import Fact
    from ..gedcomx.gedcomx import GedcomX
    from ..gedcomx.name import Name
    from ..gedcomx.person import Person
    from ..gedcomx.place_description import PlaceDescription
    from ..gedcomx.place_reference import PlaceReference
    from ..gedcomx.source_description import SourceDescription

log = get_logger("g7togx")


# ---------------------------------------------------------------------------
# GEDCOM 7 tag → FactType URI  (individual events)
# ---------------------------------------------------------------------------

_INDI_FACT_MAP: Dict[str, str] = {
    "BIRT": "http://gedcomx.org/Birth",
    "CHR":  "http://gedcomx.org/Christening",
    "DEAT": "http://gedcomx.org/Death",
    "BURI": "http://gedcomx.org/Burial",
    "CREM": "http://gedcomx.org/Cremation",
    "ADOP": "http://gedcomx.org/Adoption",
    "BAPM": "http://gedcomx.org/Baptism",
    "BARM": "http://gedcomx.org/BarMitzvah",
    "BASM": "http://gedcomx.org/BatMitzvah",
    "BLES": "http://gedcomx.org/Blessing",
    "CENS": "http://gedcomx.org/Census",
    "CONF": "http://gedcomx.org/Confirmation",
    "EMIG": "http://gedcomx.org/Emigration",
    "GRAD": "http://gedcomx.org/Graduation",
    "IMMI": "http://gedcomx.org/Immigration",
    "NATU": "http://gedcomx.org/Naturalization",
    "ORDN": "http://gedcomx.org/Ordination",
    "PROB": "http://gedcomx.org/Probate",
    "RETI": "http://gedcomx.org/Retirement",
    "WILL": "http://gedcomx.org/Will",
    "RESI": "http://gedcomx.org/Residence",
    "OCCU": "http://gedcomx.org/Occupation",
    "TITL": "http://gedcomx.org/OfficialPosition",
    "RELI": "http://gedcomx.org/Religion",
    "NATI": "http://gedcomx.org/Nationality",
}

_FAM_FACT_MAP: Dict[str, str] = {
    "MARR": "http://gedcomx.org/Marriage",
    "DIV":  "http://gedcomx.org/Divorce",
    "ENGA": "http://gedcomx.org/Engagement",
    "MARB": "http://gedcomx.org/MarriageBanns",
    "MARC": "http://gedcomx.org/MarriageContract",
    "MARL": "http://gedcomx.org/MarriageLicense",
    "MARS": "http://gedcomx.org/Separation",
    "ANUL": "http://gedcomx.org/Annulment",
    "DIVF": "http://gedcomx.org/DivorceFiling",
}

_NAME_TYPE_MAP: Dict[str, str] = {
    "BIRTH":     "http://gedcomx.org/BirthName",
    "MARRIED":   "http://gedcomx.org/MarriedName",
    "AKA":       "http://gedcomx.org/AlsoKnownAs",
    "NICK":      "http://gedcomx.org/Nickname",
    "ADOPTED":   "http://gedcomx.org/AdoptiveName",
    "FORMAL":    "http://gedcomx.org/FormalName",
    "RELIGIOUS": "http://gedcomx.org/ReligiousName",
}

_SEX_MAP: Dict[str, str] = {
    "M": "http://gedcomx.org/Male",
    "F": "http://gedcomx.org/Female",
    "X": "http://gedcomx.org/Intersex",
    "U": "http://gedcomx.org/Unknown",
}

# GEDCOM PEDI value → GedcomX fact type URI for parent-child relationships.
# BIRTH is the default and needs no annotation.
_PEDI_FACT_MAP: Dict[str, str] = {
    "ADOPTED": "http://gedcomx.org/Adoption",
    "FOSTER":  "http://gedcomx.org/FosterParent",
    "SEALING": "http://gedcomx.org/SealingChildToParents",
}


# ---------------------------------------------------------------------------
# Converter
# ---------------------------------------------------------------------------

class Gedcom7Converter:
    """Convert a :class:`~gedcomtools.gedcom7.gedcom7.Gedcom7` object to GedcomX.

    Usage::

        from gedcomtools.gedcom7.gedcom7 import Gedcom7
        from gedcomtools.gedcom7.g7togx import Gedcom7Converter

        g7 = Gedcom7("family.ged")
        gx = Gedcom7Converter().convert(g7)
        with open("family.json", "wb") as f:
            f.write(gx.json)
    """

    def __init__(self) -> None:
        # These are populated during Phase 1 (priming)
        self._person_map: Dict[str, Person] = {}
        self._source_map: Dict[str, SourceDescription] = {}
        self._agent_map:  Dict[str, Agent] = {}
        self._place_cache: Dict[str, PlaceDescription] = {}
        self._unhandled: Dict[str, int] = {}
        self._gx: Optional[GedcomX] = None
        # (fam_xref, child_xref) -> PEDI value; populated in _convert_indi
        self._pedigree: Dict[tuple, str] = {}

    @property
    def _root(self) -> GedcomX:
        """Return the GedcomX root; always non-None after convert() is called."""
        assert self._gx is not None, "convert() must be called before accessing _root"
        return self._gx

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def convert(self, gedcom7: "Gedcom7") -> "GedcomX":
        """Convert *gedcom7* and return a populated :class:`GedcomX`.

        Args:
            gedcom7: A loaded :class:`~gedcomtools.gedcom7.gedcom7.Gedcom7` instance.

        Returns:
            A :class:`~gedcomtools.gedcomx.gedcomx.GedcomX` object.
        """
        from ..gedcomx.gedcomx import GedcomX
        gx = GedcomX()
        self._gx = gx

        # Phase 1 — prime empty shells so forward-references resolve
        self._prime_sources(gedcom7)
        self._prime_agents(gedcom7)
        self._prime_persons(gedcom7)

        # Phase 2 — populate each record type
        self._convert_head(gedcom7)
        for d in gedcom7.source_details():
            self._convert_source(d)
        for d in gedcom7.repository_details():
            self._convert_repo(d)
        for d in gedcom7.submitter_details():
            self._convert_subm(d)
        for d in gedcom7.shared_note_details():
            self._convert_snote(d)
        for d in gedcom7.media_details():
            self._convert_media(d)
        for d in gedcom7.individual_details():
            self._convert_indi(d)
        for d in gedcom7.family_details():
            self._convert_fam(d)

        # Phase 3 — attach diagnostics
        gx._import_unhandled_tags = dict(self._unhandled)
        return gx

    # ------------------------------------------------------------------
    # Phase 1 helpers — prime empty shells
    # ------------------------------------------------------------------

    def _prime_sources(self, gedcom7: "Gedcom7") -> None:
        from ..gedcomx.source_description import SourceDescription
        gx = self._root
        for node in gedcom7.sources():
            xref = node.xref_id
            if not xref:
                continue
            sd = SourceDescription(id=xref)
            self._source_map[xref] = sd
            gx.add_source_description(sd)
        for node in gedcom7.media_objects():
            xref = node.xref_id
            if not xref:
                continue
            from ..gedcomx.source_description import ResourceType
            sd = SourceDescription(id=xref, resourceType=ResourceType.DigitalArtifact)
            self._source_map[xref] = sd
            gx.add_source_description(sd)

    def _prime_agents(self, gedcom7: "Gedcom7") -> None:
        from ..gedcomx.agent import Agent
        gx = self._root
        for node in gedcom7.repositories():
            xref = node.xref_id
            if not xref:
                continue
            agent = Agent(id=xref)
            self._agent_map[xref] = agent
            gx.add_agent(agent)
        for node in gedcom7.submitters():
            xref = node.xref_id
            if not xref:
                continue
            agent = Agent(id=xref)
            self._agent_map[xref] = agent
            gx.add_agent(agent)

    def _prime_persons(self, gedcom7: "Gedcom7") -> None:
        from ..gedcomx.person import Person
        gx = self._root
        for node in gedcom7.individuals():
            xref = node.xref_id
            if not xref:
                continue
            person = Person(id=xref)
            self._person_map[xref] = person
            gx.add_person(person)

    # ------------------------------------------------------------------
    # Phase 2 — record-type converters
    # ------------------------------------------------------------------

    def _convert_head(self, gedcom7: "Gedcom7") -> None:
        from ..gedcomx.attribution import Attribution
        head_list = gedcom7["HEAD"]
        if not head_list:
            return
        head = head_list[0]
        attribution = Attribution()
        date_node = head.first_child("DATE")
        if date_node and date_node.payload:
            attribution.created = date_node.payload
        subm_node = head.first_child("SUBM")
        if subm_node and subm_node.payload_is_pointer and subm_node.payload:
            agent = self._agent_map.get(subm_node.payload)
            if agent:
                from ..gedcomx.resource import Resource
                from ..gedcomx.uri import URI
                attribution.contributor = Resource(resource=URI(fragment=agent.id))
        self._root.attribution = attribution

    def _convert_source(self, d) -> None:
        from ..gedcomx.note import Note
        sd = self._source_map.get(d.xref)
        if sd is None:
            return
        if d.title:
            sd.add_title(d.title)
        if d.author:
            sd.add_note(Note(text=f"Author: {d.author}"))
        if d.publication:
            sd.add_note(Note(text=f"Publication: {d.publication}"))
        if d.abbreviation:
            sd.add_note(Note(text=f"Abbreviation: {d.abbreviation}"))
        for repo_xref in d.repository_refs:
            agent = self._agent_map.get(repo_xref)
            if agent:
                from ..gedcomx.resource import Resource
                from ..gedcomx.uri import URI
                sd.repository = Resource(resource=URI(fragment=agent.id))
                break  # GedcomX SourceDescription.repository is singular
        for text in d.note_texts:
            sd.add_note(Note(text=text))

    def _convert_repo(self, d) -> None:
        from ..gedcomx.address import Address
        from ..gedcomx.uri import URI
        agent = self._agent_map.get(d.xref)
        if agent is None:
            return
        if d.name:
            agent.add_name(d.name)
        if d.address:
            agent.add_address(Address.model_validate({"value": d.address}))
        if d.phone:
            agent.phones.append(URI.model_validate({"value": f"tel:{d.phone}"}))
        if d.email:
            agent.emails.append(URI.model_validate({"value": f"mailto:{d.email}"}))
        if d.website:
            agent.homepage = URI.model_validate({"value": d.website})

    def _convert_subm(self, d) -> None:
        from ..gedcomx.address import Address
        from ..gedcomx.uri import URI
        agent = self._agent_map.get(d.xref)
        if agent is None:
            return
        if d.name:
            agent.add_name(d.name)
        if d.address:
            agent.add_address(Address.model_validate({"value": d.address}))
        if d.phone:
            agent.phones.append(URI.model_validate({"value": f"tel:{d.phone}"}))
        if d.email:
            agent.emails.append(URI.model_validate({"value": f"mailto:{d.email}"}))
        if d.website:
            agent.homepage = URI.model_validate({"value": d.website})

    def _convert_media(self, d) -> None:
        from ..gedcomx.note import Note
        from ..gedcomx.uri import URI

        sd = self._source_map.get(d.xref)
        if sd is None:
            return

        if d.title:
            sd.add_title(d.title)

        # FILE entries — first becomes about/mediaType; extras stored as notes
        # since SourceDescription.about is singular in GedcomX.
        for filepath, form in d.files:
            if sd.about is None:
                sd.about = URI.model_validate({"value": filepath})
                if form:
                    sd.mediaType = form
            else:
                extra = f"Additional file: {filepath}"
                if form:
                    extra += f" ({form})"
                sd.add_note(Note(text=extra))

        # Inline notes
        for text in d.note_texts:
            sd.add_note(Note(text=text))

        # Shared-note references — copy note text (SNOTE already converted above)
        for snote_xref in d.shared_note_refs:
            snote_sd = self._source_map.get(snote_xref)
            if snote_sd is not None:
                for snote_note in snote_sd.notes:
                    sd.add_note(Note(text=snote_note.text))

        # UID → Persistent identifier
        if d.uid:
            from ..gedcomx.identifier import Identifier, IdentifierType
            uid_val = d.uid if d.uid.startswith("urn:") else f"urn:uuid:{d.uid}"
            sd.add_identifier(Identifier(
                type=IdentifierType.Persistent,  # type: ignore[attr-defined]
                values=[URI(value=uid_val)],
            ))

    def _convert_snote(self, d) -> None:
        sd = self._source_map.get(d.xref)
        if sd is not None:
            # Shared notes already primed as SourceDescription shells
            # Patch the resource type and store the text
            from ..gedcomx.source_description import ResourceType
            from ..gedcomx.note import Note
            sd.resourceType = ResourceType.Record
            if d.text:
                sd.add_note(Note(text=d.text))
            return
        # Not primed — create fresh and register
        from ..gedcomx.source_description import SourceDescription, ResourceType
        from ..gedcomx.note import Note
        sd = SourceDescription(id=d.xref, resourceType=ResourceType.Record)
        if d.text:
            sd.add_note(Note(text=d.text))
        self._source_map[d.xref] = sd
        self._root.add_source_description(sd)

    def _convert_indi(self, d) -> None:
        person = self._person_map.get(d.xref)
        if person is None:
            return
        person.living = d.is_living

        # Names
        for name_detail in d.names:
            gx_name = self._build_name(name_detail)
            person.add_name(gx_name)

        # Gender
        if d.sex and d.sex.upper() in _SEX_MAP:
            from ..gedcomx.gender import Gender, GenderType
            gender_uri = _SEX_MAP[d.sex.upper()]
            gender_type = next(
                (gt for gt in GenderType if gt.value == gender_uri), GenderType.Unknown
            )
            person.gender = Gender(type=gender_type)

        # Standard events
        event_pairs = [
            (d.birth,       "BIRT"),
            (d.christening, "CHR"),
            (d.death,       "DEAT"),
            (d.burial,      "BURI"),
            (d.cremation,   "CREM"),
        ]
        for event, tag in event_pairs:
            if event:
                fact = self._build_fact(tag, event)
                if fact:
                    person.add_fact(fact)

        # Residence events (list)
        for event in d.residences:
            fact = self._build_fact("RESI", event)
            if fact:
                person.add_fact(fact)

        # Generic EVEN events
        for event in d.events:
            fact = self._build_fact("EVEN", event)
            if fact:
                person.add_fact(fact)

        # Attribute facts (value-only, no event substructures)
        attr_pairs = [
            (d.occupation,   "OCCU"),
            (d.title,        "TITL"),
            (d.religion,     "RELI"),
            (d.nationality,  "NATI"),
        ]
        for value, tag in attr_pairs:
            if value:
                from ..gedcomx.fact import Fact, FactType
                ft = FactType.from_value(_INDI_FACT_MAP[tag])
                person.add_fact(Fact(type=ft, value=value))

        # Record-level source citations and media links
        self._attach_source_refs(person, d.source_citations)
        self._attach_media_refs(person, d.media_refs)

        # Record PEDI values so _convert_fam can attach them to relationships
        for link in d.families_as_child:
            if link.pedigree and link.pedigree != "BIRTH":
                self._pedigree[(link.xref, d.xref)] = link.pedigree

    def _convert_fam(self, d) -> None:
        from ..gedcomx.relationship import Relationship, RelationshipType
        from ..gedcomx.resource import Resource
        from ..gedcomx.uri import URI

        husb = self._person_map.get(d.husband_xref) if d.husband_xref else None
        wife = self._person_map.get(d.wife_xref)    if d.wife_xref  else None

        # Couple relationship
        if husb or wife:
            couple_rel = Relationship(
                id=f"couple-{d.xref}",
                type=RelationshipType.Couple,
                person1=Resource(resource=URI(fragment=husb.id)) if husb else None,
                person2=Resource(resource=URI(fragment=wife.id)) if wife else None,
            )
            if d.marriage:
                fact = self._build_fact("MARR", d.marriage)
                if fact:
                    couple_rel.add_fact(fact)
            if d.divorce:
                fact = self._build_fact("DIV", d.divorce)
                if fact:
                    couple_rel.add_fact(fact)
            for event in d.events:
                tag = event.event_type or "EVEN"
                fact = self._build_fact(tag, event)
                if fact:
                    couple_rel.add_fact(fact)
            self._attach_source_refs(couple_rel, d.source_citations)
            self._attach_media_refs(couple_rel, d.media_refs)
            self._root.add_relationship(couple_rel)

        # Parent-child relationships
        parents = [p for p in (husb, wife) if p is not None]
        for child_xref in d.children_xrefs:
            child = self._person_map.get(child_xref)
            if child is None:
                continue
            for parent in parents:
                pc_rel = Relationship(
                    id=f"pc-{d.xref}-{parent.id}-{child.id}",
                    type=RelationshipType.ParentChild,
                    person1=Resource(resource=URI(fragment=parent.id)),
                    person2=Resource(resource=URI(fragment=child.id)),
                )
                pedi = self._pedigree.get((d.xref, child_xref))
                if pedi:
                    pedi_fact = self._build_pedigree_fact(pedi)
                    if pedi_fact:
                        pc_rel.add_fact(pedi_fact)
                self._root.add_relationship(pc_rel)

    # ------------------------------------------------------------------
    # Building helpers
    # ------------------------------------------------------------------

    def _build_name(self, nd) -> Name:
        """Build a GedcomX :class:`Name` from a :class:`NameDetail`."""
        from ..gedcomx.name import Name, NameForm, NamePart, NameType, NamePartType

        # Determine name type
        name_type = NameType.BirthName
        if nd.name_type:
            uri = _NAME_TYPE_MAP.get(nd.name_type.upper())
            if uri:
                name_type = next((nt for nt in NameType if nt.value == uri), NameType.BirthName)

        # If we have no sub-parts at all, use the smart Name.simple() parser
        if not any([nd.given, nd.surname, nd.prefix, nd.suffix, nd.surname_prefix]):
            name = Name.simple(nd.full)
            name.type = name_type
            return name

        # Build parts explicitly
        parts: List[NamePart] = []
        if nd.prefix:
            parts.append(NamePart(type=NamePartType.Prefix, value=nd.prefix))
        if nd.given:
            parts.append(NamePart(type=NamePartType.Given, value=nd.given))
        if nd.surname:
            surn = f"{nd.surname_prefix} {nd.surname}".strip() if nd.surname_prefix else nd.surname
            parts.append(NamePart(type=NamePartType.Surname, value=surn))
        if nd.suffix:
            parts.append(NamePart(type=NamePartType.Suffix, value=nd.suffix))

        primary_form = NameForm(fullText=nd.display, parts=parts)
        name_forms: List[NameForm] = [primary_form]

        # Add language translations as extra NameForms
        for tran in nd.translations:
            tran_parts: List[NamePart] = []
            if tran.given:
                tran_parts.append(NamePart(type=NamePartType.Given, value=tran.given))
            if tran.surname:
                surn = f"{tran.surname_prefix} {tran.surname}".strip() if tran.surname_prefix else tran.surname
                tran_parts.append(NamePart(type=NamePartType.Surname, value=surn))
            name_forms.append(NameForm(lang=tran.lang, fullText=tran.display, parts=tran_parts))

        return Name(type=name_type, nameForms=name_forms)

    def _build_pedigree_fact(self, pedi: str) -> "Optional[Fact]":
        """Return a :class:`Fact` encoding a non-birth PEDI value, or ``None``."""
        from ..gedcomx.fact import Fact, FactType
        uri = _PEDI_FACT_MAP.get(pedi)
        if uri is None:
            self._note_unhandled(f"PEDI:{pedi}")
            return None
        return Fact(type=FactType.from_value(uri))

    def _build_fact(self, tag: str, event) -> Optional[Fact]:
        """Build a GedcomX :class:`Fact` from an :class:`EventDetail`.

        Args:
            tag:   GEDCOM tag (used to look up FactType).
            event: :class:`~gedcomtools.gedcom7.models.EventDetail`.

        Returns:
            A :class:`~gedcomtools.gedcomx.fact.Fact` or ``None``.
        """
        from ..gedcomx.fact import Fact, FactType, FactQualifier
        from ..gedcomx.date import Date

        # Determine FactType
        fact_uri = _INDI_FACT_MAP.get(tag) or _FAM_FACT_MAP.get(tag)
        if fact_uri:
            fact_type = FactType.from_value(fact_uri)
        elif tag == "EVEN" and event.event_type:
            fact_type = FactType.guess(event.event_type) or FactType.Unknown
        else:
            self._note_unhandled(tag)
            fact_type = FactType.Unknown

        fact = Fact(type=fact_type)

        if event.date:
            fact.date = Date(original=event.date)

        if event.place:
            fact.place = self._make_place_reference(event.place)

        qualifiers = []
        if event.age:
            qualifiers.append(FactQualifier.Age)
        if event.cause:
            qualifiers.append(FactQualifier.Cause)
        if qualifiers:
            fact.qualifiers = qualifiers

        if event.note:
            from ..gedcomx.note import Note
            fact.add_note(Note(text=event.note))

        if event.agency:
            from ..gedcomx.note import Note
            fact.add_note(Note(text=f"Agency: {event.agency}"))

        self._attach_source_refs(fact, event.sources)
        return fact

    def _make_place_reference(self, place_name: str) -> PlaceReference:
        """Return a :class:`PlaceReference` for *place_name*, deduplicating the description."""
        from ..gedcomx.place_description import PlaceDescription
        from ..gedcomx.place_reference import PlaceReference
        from ..gedcomx.textvalue import TextValue

        pd = self._place_cache.get(place_name)
        if pd is None:
            existing = self._root.places.by_name(place_name)
            if existing:
                pd = existing[0]
            else:
                pd = PlaceDescription(names=[TextValue(value=place_name)])
                self._root.add_place_description(pd)
            self._place_cache[place_name] = pd

        from ..gedcomx.resource import Resource
        from ..gedcomx.uri import URI
        return PlaceReference(
            original=place_name,
            description=Resource(resource=URI(fragment=pd.id)),
        )

    def _attach_source_refs(self, target, citations: List) -> None:
        """Attach :class:`SourceReference` objects from *citations* to *target*."""
        from ..gedcomx.source_reference import SourceReference, KnownSourceReference
        from ..gedcomx.qualifier import Qualifier
        from ..gedcomx.resource import Resource
        from ..gedcomx.uri import URI

        for cit in citations:
            sd = self._source_map.get(cit.xref)
            if sd is None:
                self._note_unhandled(f"SOUR:{cit.xref}")
                continue
            sr = SourceReference(
                descriptionId=cit.xref,
                description=Resource(resource=URI(fragment=sd.id)),
            )
            if cit.page:
                sr.add_qualifier(
                    Qualifier(name=KnownSourceReference.Page, value=cit.page)
                )
            if hasattr(target, "add_source_reference"):
                target.add_source_reference(sr)

    def _attach_media_refs(self, target, media_refs: List[str]) -> None:
        """Attach media-object SourceReferences from *media_refs* to *target*."""
        from ..gedcomx.source_reference import SourceReference
        from ..gedcomx.resource import Resource
        from ..gedcomx.uri import URI

        for xref in media_refs:
            sd = self._source_map.get(xref)
            if sd is None:
                self._note_unhandled(f"OBJE:{xref}")
                continue
            sr = SourceReference(
                descriptionId=xref,
                description=Resource(resource=URI(fragment=sd.id)),
            )
            if hasattr(target, "add_source_reference"):
                target.add_source_reference(sr)

    def _note_unhandled(self, tag: str) -> None:
        self._unhandled[tag] = self._unhandled.get(tag, 0) + 1
