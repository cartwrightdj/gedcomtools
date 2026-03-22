"""
======================================================================
 Project: gedcomtools
 File:    graph.py
 Author:  David J. Cartwright
 Purpose: Directed multigraph builder and exporter for GEDCOM 7 and
          GEDCOMx genealogical data, backed by NetworkX MultiDiGraph.

 Created: 2026-03-16
 Updated:
   - 2026-03-16: added from_gedcom5() builder
======================================================================

Build directed multigraphs from GEDCOM 7 or GEDCOMx data using
`NetworkX <https://networkx.org/>`_ as the underlying graph engine.

Quick start::

    from gedcomtools.gedcom7 import Gedcom7
    from gedcomtools.graph import GedcomGraph

    g = Gedcom7("family.ged")
    gr = GedcomGraph.from_gedcom7(g)
    print(gr)                              # GedcomGraph(250 nodes, 430 edges)
    print(gr.summary())

    # Ancestor subgraph (4 generations)
    sub = gr.ancestors_subgraph("@I1@", depth=4)

    # Export
    gr.to_graphml("family.graphml")        # Gephi / yEd
    gr.to_gexf("family.gexf")             # Gephi with attributes
    gr.to_json("family_graph.json")        # D3.js / Cytoscape.js / vis.js
    gr.to_jsonl("nodes.jsonl", "edges.jsonl")  # one JSON object per line

Node types (``node_type`` attribute):

    ============  =============================================
    person        Individual / Person
    family        FAM record (GEDCOM 7 only)
    source        Bibliographic source / SourceDescription
    repository    Archive or library (GEDCOM 7 REPO)
    place         Geographical location
    media         Media file / OBJE record
    ============  =============================================

Edge types (``rel`` attribute):

    ============  ================================================
    CHILD_IN      person → family  (individual is child in FAM)
    SPOUSE_IN     person → family  (individual is spouse in FAM)
    HAS_CHILD     family → person
    HAS_HUSBAND   family → person
    HAS_WIFE      family → person
    PARENT_OF     person → person  (derived shortcut)
    CHILD_OF      person → person  (reverse of PARENT_OF)
    SPOUSE_OF     person → person  (derived shortcut; both directions)
    CITES         person/family → source
    HELD_BY       source → repository
    BORN_IN       person → place
    DIED_IN       person → place
    LIVED_IN      person → place
    HAS_MEDIA     person/family → media
    ============  ================================================
"""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any, Dict, List, Optional

try:
    import networkx as nx
except ImportError as _nx_err:
    raise ImportError(
        "networkx is required for GedcomGraph.  "
        "Install it with:  pip install networkx"
    ) from _nx_err


class GedcomGraph:
    """Directed multigraph over GEDCOM 7 or GEDCOMx genealogical data.

    Build with the class-method factories:

    - :meth:`from_gedcom7` — accepts a ``Gedcom7`` instance.
    - :meth:`from_gedcomx` — accepts a ``GedcomX`` document instance.

    After construction the underlying ``networkx.MultiDiGraph`` is
    available as :attr:`G` for any NetworkX operations not directly
    exposed here.
    """

    def __init__(self) -> None:
        self.G: nx.MultiDiGraph = nx.MultiDiGraph()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _add_node(self, node_id: str, **attrs: Any) -> None:
        """Add or update a node, silently dropping ``None`` values."""
        clean = {k: v for k, v in attrs.items() if v is not None}
        if self.G.has_node(node_id):
            self.G.nodes[node_id].update(clean)
        else:
            self.G.add_node(node_id, **clean)

    def _add_edge(self, src: str, dst: str, rel: str, **attrs: Any) -> None:
        """Add a directed edge only when both endpoint nodes exist."""
        if self.G.has_node(src) and self.G.has_node(dst):
            clean = {k: v for k, v in attrs.items() if v is not None}
            self.G.add_edge(src, dst, rel=rel, **clean)

    def _intern_place(self, name: Optional[str]) -> Optional[str]:
        """Return a stable ``place:<name>`` node id, creating the node if needed."""
        if not name:
            return None
        pid = f"place:{name}"
        if not self.G.has_node(pid):
            self.G.add_node(pid, node_type="place", name=name)
        return pid

    # ------------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------------

    @classmethod
    def from_gedcom7(cls, g: Any) -> "GedcomGraph":
        """Build a :class:`GedcomGraph` from a :class:`~gedcomtools.gedcom7.Gedcom7` instance.

        Nodes are created for INDI, FAM, SOUR, REPO, OBJE records and for
        any place names found on birth, death, and residence events.

        Structural edges (CHILD_IN, SPOUSE_IN, HAS_CHILD, …) are added
        alongside derived shortcut edges (PARENT_OF, CHILD_OF, SPOUSE_OF)
        so that ancestor / descendant traversal works without routing
        through family nodes.

        Args:
            g: A parsed ``Gedcom7`` instance.

        Returns:
            Populated :class:`GedcomGraph`.
        """
        gr = cls()

        # ---- nodes -------------------------------------------------------

        for p in g.individual_details():
            gr._add_node(
                p.xref,
                node_type="person",
                name=p.full_name,
                sex=p.sex,
                birth_year=p.birth_year,
                death_year=p.death_year,
                is_living=p.is_living,
            )

        for f in g.family_details():
            gr._add_node(
                f.xref,
                node_type="family",
                marriage_year=f.marriage_year,
                divorce_year=f.divorce_year,
            )

        for s in g.source_details():
            gr._add_node(s.xref, node_type="source", title=s.title, author=s.author)

        for r in g.repository_details():
            gr._add_node(r.xref, node_type="repository", name=r.name)

        for m in g.media_details():
            gr._add_node(m.xref, node_type="media", title=m.title)

        # ---- family structural + derived edges ---------------------------

        for f in g.family_details():
            parents: List[str] = []

            if f.husband_xref and gr.G.has_node(f.husband_xref):
                gr._add_edge(f.husband_xref, f.xref, "SPOUSE_IN")
                gr._add_edge(f.xref, f.husband_xref, "HAS_HUSBAND")
                parents.append(f.husband_xref)

            if f.wife_xref and gr.G.has_node(f.wife_xref):
                gr._add_edge(f.wife_xref, f.xref, "SPOUSE_IN")
                gr._add_edge(f.xref, f.wife_xref, "HAS_WIFE")
                parents.append(f.wife_xref)

            if len(parents) == 2:
                gr._add_edge(parents[0], parents[1], "SPOUSE_OF")
                gr._add_edge(parents[1], parents[0], "SPOUSE_OF")

            for child_xref in f.children_xrefs:
                if not gr.G.has_node(child_xref):
                    continue
                gr._add_edge(child_xref, f.xref, "CHILD_IN")
                gr._add_edge(f.xref, child_xref, "HAS_CHILD")
                for parent_xref in parents:
                    gr._add_edge(parent_xref, child_xref, "PARENT_OF")
                    gr._add_edge(child_xref, parent_xref, "CHILD_OF")

        # ---- source citation edges ---------------------------------------

        for p in g.individual_details():
            for cit in p.source_citations:
                gr._add_edge(p.xref, cit.xref, "CITES")

        for f in g.family_details():
            for cit in f.source_citations:
                gr._add_edge(f.xref, cit.xref, "CITES")

        for s in g.source_details():
            for repo_ref in s.repository_refs:
                gr._add_edge(s.xref, repo_ref, "HELD_BY")

        # ---- place edges -------------------------------------------------

        for p in g.individual_details():
            if p.birth and p.birth.place:
                place_id = gr._intern_place(p.birth.place)
                gr._add_edge(p.xref, place_id, "BORN_IN")
            if p.death and p.death.place:
                place_id = gr._intern_place(p.death.place)
                gr._add_edge(p.xref, place_id, "DIED_IN")
            for resi in p.residences:
                if resi.place:
                    place_id = gr._intern_place(resi.place)
                    gr._add_edge(p.xref, place_id, "LIVED_IN")

        # ---- media edges -------------------------------------------------

        for p in g.individual_details():
            for mref in p.media_refs:
                gr._add_edge(p.xref, mref, "HAS_MEDIA")

        for f in g.family_details():
            for mref in f.media_refs:
                gr._add_edge(f.xref, mref, "HAS_MEDIA")

        return gr

    @classmethod
    def from_gedcom5(cls, g: Any) -> "GedcomGraph":
        """Build a :class:`GedcomGraph` from a :class:`~gedcomtools.gedcom5.Gedcom5` instance.

        Handles GEDCOM 5.5 ``IndividualRecord``, ``FamilyRecord``,
        ``SourceRecord``, ``RepositoryRecord``, and ``ObjectRecord`` elements.
        Structural edges (CHILD_IN, SPOUSE_IN, HAS_CHILD, …) and derived
        shortcut edges (PARENT_OF, CHILD_OF, SPOUSE_OF) are both added so
        ancestor/descendant traversal works identically to the GEDCOM 7 builder.

        Args:
            g: A parsed ``Gedcom5`` instance.

        Returns:
            Populated :class:`GedcomGraph`.
        """
        gr = cls()

        # ---- person nodes ------------------------------------------------

        for p in g.individual_details():
            gr._add_node(
                p.xref,
                node_type="person",
                name=p.full_name,
                sex=p.sex,
                birth_year=p.birth_year,
                death_year=p.death_year,
                is_living=p.is_living,
            )

        # ---- family nodes ------------------------------------------------

        for f in g.family_details():
            gr._add_node(
                f.xref,
                node_type="family",
                marriage_year=f.marriage_year,
                divorce_year=f.divorce_year,
            )

        # ---- source nodes ------------------------------------------------

        for s in g.source_details():
            gr._add_node(s.xref, node_type="source", title=s.title, author=s.author)

        # ---- repository nodes --------------------------------------------

        for r in g.repository_details():
            gr._add_node(r.xref, node_type="repository", name=r.name)

        # ---- media nodes -------------------------------------------------

        for m in g.media_details():
            gr._add_node(m.xref, node_type="media", title=m.title)

        # ---- family structural + derived edges ---------------------------

        for f in g.family_details():
            parents: List[str] = []

            if f.husband_xref and gr.G.has_node(f.husband_xref):
                gr._add_edge(f.husband_xref, f.xref, "SPOUSE_IN")
                gr._add_edge(f.xref, f.husband_xref, "HAS_HUSBAND")
                parents.append(f.husband_xref)

            if f.wife_xref and gr.G.has_node(f.wife_xref):
                gr._add_edge(f.wife_xref, f.xref, "SPOUSE_IN")
                gr._add_edge(f.xref, f.wife_xref, "HAS_WIFE")
                parents.append(f.wife_xref)

            if len(parents) == 2:
                gr._add_edge(parents[0], parents[1], "SPOUSE_OF")
                gr._add_edge(parents[1], parents[0], "SPOUSE_OF")

            for child_xref in f.children_xrefs:
                if not gr.G.has_node(child_xref):
                    continue
                gr._add_edge(child_xref, f.xref, "CHILD_IN")
                gr._add_edge(f.xref, child_xref, "HAS_CHILD")
                for parent_xref in parents:
                    gr._add_edge(parent_xref, child_xref, "PARENT_OF")
                    gr._add_edge(child_xref, parent_xref, "CHILD_OF")

        # ---- source citation edges ---------------------------------------

        for p in g.individual_details():
            for cit in p.source_citations:
                gr._add_edge(p.xref, cit.xref, "CITES")

        for f in g.family_details():
            for cit in f.source_citations:
                gr._add_edge(f.xref, cit.xref, "CITES")

        for s in g.source_details():
            for repo_ref in s.repository_refs:
                gr._add_edge(s.xref, repo_ref, "HELD_BY")

        # ---- place edges -------------------------------------------------

        for p in g.individual_details():
            if p.birth and p.birth.place:
                place_id = gr._intern_place(p.birth.place)
                gr._add_edge(p.xref, place_id, "BORN_IN")
            if p.death and p.death.place:
                place_id = gr._intern_place(p.death.place)
                gr._add_edge(p.xref, place_id, "DIED_IN")
            for resi in p.residences:
                if resi.place:
                    place_id = gr._intern_place(resi.place)
                    gr._add_edge(p.xref, place_id, "LIVED_IN")

        # ---- media edges -------------------------------------------------

        for p in g.individual_details():
            for mref in p.media_refs:
                gr._add_edge(p.xref, mref, "HAS_MEDIA")

        for f in g.family_details():
            for mref in f.media_refs:
                gr._add_edge(f.xref, mref, "HAS_MEDIA")

        return gr

    @classmethod
    def from_gedcomx(cls, gx: Any) -> "GedcomGraph":
        """Build a :class:`GedcomGraph` from a GEDCOMx document.

        Supports ``GedcomX`` instances whose ``.persons``,
        ``.relationships``, ``.sourceDescriptions``, and ``.places``
        collections follow the standard GEDCOMx Python model.

        ``RelationshipType.Couple`` → bidirectional SPOUSE_OF edges.
        ``RelationshipType.ParentChild`` → PARENT_OF (p1→p2) and
        CHILD_OF (p2→p1) edges.

        Args:
            gx: A ``GedcomX`` document instance.

        Returns:
            Populated :class:`GedcomGraph`.
        """
        gr = cls()

        from .gedcomx.fact import FactType
        from .gedcomx.relationship import RelationshipType

        # ---- helpers -----------------------------------------------------

        def _resolve_id(ref: Any) -> Optional[str]:
            """Extract person id from a Person object or a Resource ref."""
            if ref is None:
                return None
            if hasattr(ref, "names"):           # actual Person object
                return getattr(ref, "id", None)
            # Resource: URI fragment or path component holds the id
            res = getattr(ref, "resource", None)
            if res is not None:
                frag = getattr(res, "fragment", None)
                if frag:
                    return frag.lstrip("#")
                val = (
                    getattr(res, "value", None)
                    or getattr(res, "path", None)
                    or str(res)
                )
                if val:
                    return str(val).lstrip("#").rsplit("/", maxsplit=1)[-1] or None
            return getattr(ref, "id", None)

        def _year(date_obj: Any) -> Optional[int]:
            orig = str(getattr(date_obj, "original", "") or "")
            m = re.search(r"\b(\d{3,4})\b", orig)
            return int(m.group(1)) if m else None

        def _display_name(person: Any) -> str:
            try:
                return person.names[0].nameForms[0].fullText or ""
            except (IndexError, AttributeError):
                return ""

        def _first_fact(person: Any, *types: FactType) -> Any:
            for f in getattr(person, "facts", None) or []:
                if getattr(f, "type", None) in types:
                    return f
            return None

        def _place_name(fact: Any) -> Optional[str]:
            pr = getattr(fact, "place", None)
            return getattr(pr, "original", None) if pr else None

        def _text_value(tv: Any) -> Optional[str]:
            return getattr(tv, "value", None) or str(tv) or None

        # ---- person nodes ------------------------------------------------

        for person in gx.persons:
            pid = person.id
            if not pid:
                continue

            birth_f = _first_fact(person, FactType.Birth, FactType.Christening)
            death_f = _first_fact(person, FactType.Death, FactType.Burial, FactType.Cremation)

            gender_type = getattr(getattr(person, "gender", None), "type", None)
            sex = getattr(gender_type, "name", None)  # e.g. "Male", "Female"

            gr._add_node(
                pid,
                node_type="person",
                name=_display_name(person),
                sex=sex,
                birth_year=_year(getattr(birth_f, "date", None)) if birth_f else None,
                death_year=_year(getattr(death_f, "date", None)) if death_f else None,
                is_living=getattr(person, "living", None),
            )

            if birth_f:
                pname = _place_name(birth_f)
                if pname:
                    gr._add_edge(pid, gr._intern_place(pname), "BORN_IN")
            if death_f:
                pname = _place_name(death_f)
                if pname:
                    gr._add_edge(pid, gr._intern_place(pname), "DIED_IN")

        # ---- source nodes ------------------------------------------------

        for src in gx.sourceDescriptions:
            sid = src.id
            if not sid:
                continue
            titles = getattr(src, "titles", None) or []
            title = _text_value(titles[0]) if titles else None
            gr._add_node(sid, node_type="source", title=title)

        # ---- place nodes (explicit PlaceDescription records) -------------

        for place in gx.places:
            pid_ = place.id
            if not pid_:
                continue
            names = getattr(place, "names", None) or []
            pname = _text_value(names[0]) if names else None
            gr._add_node(pid_, node_type="place", name=pname)

        # ---- relationship edges ------------------------------------------

        for rel in gx.relationships:
            p1_id = _resolve_id(rel.person1)
            p2_id = _resolve_id(rel.person2)
            if not p1_id or not p2_id:
                continue

            if rel.type == RelationshipType.Couple:
                gr._add_edge(p1_id, p2_id, "SPOUSE_OF")
                gr._add_edge(p2_id, p1_id, "SPOUSE_OF")
            elif rel.type == RelationshipType.ParentChild:
                # GEDCOM-X convention: person1 = parent, person2 = child
                gr._add_edge(p1_id, p2_id, "PARENT_OF")
                gr._add_edge(p2_id, p1_id, "CHILD_OF")

        return gr

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def ancestors_subgraph(self, node_id: str, depth: int = 0) -> nx.MultiDiGraph:
        """Return a subgraph containing genealogical ancestors.

        Traverses ``CHILD_OF`` edges (person → parent). Works for both
        GEDCOM 7 (where these shortcuts are derived from FAM) and GEDCOMx.

        Args:
            node_id: Starting person node ID.
            depth:   Maximum generations to climb; ``0`` = unlimited.

        Returns:
            :class:`networkx.MultiDiGraph` subgraph copy.
        """
        return self._bfs_subgraph(node_id, {"CHILD_OF"}, depth)

    def descendants_subgraph(self, node_id: str, depth: int = 0) -> nx.MultiDiGraph:
        """Return a subgraph containing genealogical descendants.

        Traverses ``PARENT_OF`` edges. Works for both GEDCOM 7 and GEDCOMx.

        Args:
            node_id: Starting person node ID.
            depth:   Maximum generations to descend; ``0`` = unlimited.

        Returns:
            :class:`networkx.MultiDiGraph` subgraph copy.
        """
        return self._bfs_subgraph(node_id, {"PARENT_OF"}, depth)

    def _bfs_subgraph(
        self, start: str, follow_rels: set, depth: int
    ) -> nx.MultiDiGraph:
        """BFS over *follow_rels* edges from *start*, limited to *depth* hops."""
        visited = {start}
        frontier = {start}
        gen = 0
        while frontier and (depth == 0 or gen < depth):
            next_f: set = set()
            for n in frontier:
                for succ in self.G.successors(n):
                    if succ in visited:
                        continue
                    edges = self.G.get_edge_data(n, succ) or {}
                    if any(d.get("rel") in follow_rels for d in edges.values()):
                        next_f.add(succ)
            visited |= next_f
            frontier = next_f
            gen += 1
        return self.G.subgraph(visited).copy()

    def shortest_path(self, a: str, b: str) -> List[str]:
        """Undirected shortest path between two nodes (ignores edge direction).

        Useful for "how are these two people related?" queries.

        Args:
            a: Source node ID.
            b: Target node ID.

        Returns:
            Ordered list of node IDs on the path, or ``[]`` if unreachable.
        """
        try:
            return nx.shortest_path(self.G.to_undirected(), a, b)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def connected_components(self) -> List[List[str]]:
        """Return weakly connected components as lists of node IDs, largest first.

        Returns:
            List of node-ID lists, sorted by descending size.
        """
        comps = list(nx.weakly_connected_components(self.G))
        return [list(c) for c in sorted(comps, key=len, reverse=True)]

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def nodes_by_type(self, node_type: str) -> List[str]:
        """Return all node IDs with the given ``node_type``.

        Args:
            node_type: ``"person"``, ``"family"``, ``"source"``,
                       ``"repository"``, ``"place"``, or ``"media"``.

        Returns:
            List of matching node IDs.
        """
        return [n for n, d in self.G.nodes(data=True) if d.get("node_type") == node_type]

    def person_nodes(self) -> List[str]:
        """Return all person node IDs."""
        return self.nodes_by_type("person")

    def family_nodes(self) -> List[str]:
        """Return all family node IDs."""
        return self.nodes_by_type("family")

    def edges_of_type(self, rel: str) -> List[tuple]:
        """Return all ``(src, dst)`` pairs for a given edge type.

        Args:
            rel: Edge type, e.g. ``"PARENT_OF"``, ``"SPOUSE_OF"``, ``"CITES"``.

        Returns:
            List of ``(src, dst)`` tuples.
        """
        return [(u, v) for u, v, d in self.G.edges(data=True) if d.get("rel") == rel]

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def to_graphml(self, path: str) -> None:
        """Write to GraphML format (Gephi / yEd compatible).

        Args:
            path: Output file path.
        """
        nx.write_graphml(self.G, path)

    def to_gexf(self, path: str) -> None:
        """Write to GEXF format (Gephi with node/edge attributes).

        Args:
            path: Output file path.
        """
        nx.write_gexf(self.G, path)

    def to_json(self, path: str) -> None:
        """Write to node-link JSON (D3.js / Cytoscape.js / vis.js compatible).

        Args:
            path: Output file path.
        """
        from networkx.readwrite import json_graph
        data = json_graph.node_link_data(self.G)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def to_jsonl(self, nodes_path: str, edges_path: str) -> None:
        """Write nodes and edges as JSONL.

        Follows the existing ``graph/persons.jsonl`` /
        ``graph/person_to_person.jsonl`` convention: one JSON object
        per line, ``None`` values omitted.

        Args:
            nodes_path: Output path for node records.
            edges_path: Output path for edge records.
        """
        with open(nodes_path, "w", encoding="utf-8") as f:
            for nid, attrs in self.G.nodes(data=True):
                row: dict = {"id": nid}
                row.update({k: v for k, v in attrs.items() if v is not None})
                f.write(json.dumps(row, default=str) + "\n")

        with open(edges_path, "w", encoding="utf-8") as f:
            for src, dst, attrs in self.G.edges(data=True):
                row = {"src": src, "dst": dst}
                row.update({k: v for k, v in attrs.items() if v is not None})
                f.write(json.dumps(row, default=str) + "\n")

    def to_adjacency_dict(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return a plain adjacency dict keyed by source node ID.

        Each value is a list of ``{"dst": ..., "rel": ..., ...}`` dicts.

        Returns:
            Adjacency dict.
        """
        result: Dict[str, List[Dict[str, Any]]] = {}
        for src, dst, attrs in self.G.edges(data=True):
            entry: Dict[str, Any] = {"dst": dst}
            entry.update({k: v for k, v in attrs.items() if v is not None})
            result.setdefault(src, []).append(entry)
        return result

    # ------------------------------------------------------------------
    # Summary / dunder
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """Return a breakdown of node and edge type counts.

        Returns:
            Dict with ``"nodes"``, ``"edges"``, ``"total_nodes"``,
            ``"total_edges"`` keys.
        """
        node_counts = Counter(
            d.get("node_type", "unknown")
            for _, d in self.G.nodes(data=True)
        )
        edge_counts = Counter(
            d.get("rel", "unknown")
            for _, _, d in self.G.edges(data=True)
        )
        return {
            "nodes": dict(node_counts),
            "edges": dict(edge_counts),
            "total_nodes": self.G.number_of_nodes(),
            "total_edges": self.G.number_of_edges(),
        }

    def __repr__(self) -> str:
        return (
            f"GedcomGraph("
            f"{self.G.number_of_nodes()} nodes, "
            f"{self.G.number_of_edges()} edges)"
        )
