"""
======================================================================
 Project: gedcomtools
 File:    gedcom7/writer.py
 Author:  David J. Cartwright
 Purpose: GEDCOM 7 serializer — converts GedcomStructure trees to
          valid GEDCOM 7 text files.

 Created: 2026-03-15
 Updated:
   - 2026-03-15: initial implementation; CONT re-splitting; line-length warning
   - 2026-03-16: CONT lines now also checked for line-length; write() wraps
                 FileNotFoundError with a clear message
   - 2026-03-16: import updated GedcomStructure.py → structure.py
======================================================================

Serializes in-memory GedcomStructure trees back to valid GEDCOM 7 text.

Design notes
------------
- The parser merges CONT lines into the parent payload using ``\\n`` as a
  separator.  The writer splits those embedded newlines back into CONT
  substructures at ``level + 1``.
- CONC is not emitted; it was removed in GEDCOM 7.0.  Very long single-line
  payloads are written as-is with a warning returned to the caller.
- The class is intentionally stateless between calls so that a single writer
  instance can be re-used for many files or round-trip conversions.
- Future converters (GEDCOM 5 → 7, GEDCOMx → 7) build a
  ``List[GedcomStructure]`` and pass it straight to this writer.

The docstrings are written in Google style so they render well with
Sphinx Napoleon.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Iterator, List, Union

from .structure import GedcomStructure


class Gedcom7Writer:
    """Serialize :class:`GedcomStructure` trees to GEDCOM 7 text.

    Args:
        line_ending: Line terminator written after every GEDCOM line.
            GEDCOM 7 specifies U+000A (LF, ``"\\n"``).  Use ``"\\r\\n"``
            only when the target system requires CRLF.
        bom: Whether to prepend a UTF-8 BOM (U+FEFF).  The GEDCOM 7
            specification discourages the BOM; the default is ``False``.

    Example::

        from gedcomtools.gedcom7 import Gedcom7
        from gedcomtools.gedcom7.writer import Gedcom7Writer

        g = Gedcom7("family.ged")
        writer = Gedcom7Writer()
        writer.write(g.records, "output.ged")
        text = writer.serialize(g.records)
    """

    def __init__(
        self,
        *,
        line_ending: str = "\n",
        bom: bool = False,
    ) -> None:
        self.line_ending = line_ending
        self.bom = bom
        self._warnings: List[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_warnings(self) -> List[str]:
        """Return line-length warnings from the last serialize() or write() call.

        Returns:
            List of human-readable warning strings.
        """
        return list(self._warnings)

    def write(
        self,
        records: List[GedcomStructure],
        filepath: Union[str, Path],
        *,
        encoding: str = "utf-8",
    ) -> List[str]:
        """Write *records* to a file atomically.

        Serializes to a ``.tmp`` sibling first, then renames it into place so
        that a failed write never leaves the destination file truncated or
        corrupted.

        Args:
            records: Top-level GEDCOM structures (typically HEAD … TRLR).
            filepath: Destination file path.  Any intermediate directories
                must already exist.
            encoding: File encoding.  GEDCOM 7 mandates UTF-8; only change
                this for special debugging purposes.

        Returns:
            Line-length warnings collected during serialization (same as
            ``get_warnings()``).  An empty list means no warnings.

        Raises:
            FileNotFoundError: If the destination directory does not exist.
        """
        dest = Path(filepath)
        content = self.serialize(records)
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        try:
            tmp.write_text(content, encoding=encoding)
            tmp.replace(dest)
        except FileNotFoundError as exc:
            tmp.unlink(missing_ok=True)
            raise FileNotFoundError(
                f"Cannot write to {dest}: parent directory does not exist."
            ) from exc
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
        return list(self._warnings)

    def serialize(self, records: List[GedcomStructure]) -> str:
        """Serialize *records* to a GEDCOM 7 string.

        Args:
            records: Top-level GEDCOM structures.

        Returns:
            The complete GEDCOM 7 file content as a :class:`str`, including
            the final line terminator on the TRLR line.
        """
        self._warnings = []
        buf = io.StringIO()
        if self.bom:
            buf.write("\ufeff")
        for line in self._render_records(records):
            buf.write(line)
            buf.write(self.line_ending)
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Internal rendering helpers
    # ------------------------------------------------------------------

    def _render_records(self, records: List[GedcomStructure]) -> Iterator[str]:
        """Yield rendered GEDCOM lines for all *records*.

        Args:
            records: Top-level structures.

        Yields:
            GEDCOM line strings without line endings.
        """
        for record in records:
            yield from self._render_node(record)

    _MAX_DEPTH = 100  # GEDCOM 7 structures are rarely deeper than ~10 levels

    def _render_node(self, node: GedcomStructure, _depth: int = 0) -> Iterator[str]:
        """Yield rendered GEDCOM lines for *node* and all descendants.

        Args:
            node: Root node to render.
            _depth: Current recursion depth (used for cycle detection).

        Yields:
            GEDCOM line strings without line endings.

        Raises:
            RecursionError: If nesting exceeds ``_MAX_DEPTH`` (indicates a
                cycle in the child list).
        """
        if _depth > self._MAX_DEPTH:
            raise RecursionError(
                f"GEDCOM tree depth limit ({self._MAX_DEPTH}) exceeded at "
                f"tag {node.tag!r} — possible circular child reference."
            )
        yield from self._format_lines(node)
        for child in node.children:
            yield from self._render_node(child, _depth + 1)

    def _format_lines(self, node: GedcomStructure) -> Iterator[str]:
        """Format one node as one or more GEDCOM line strings.

        If the node's payload contains embedded ``\\n`` characters (created
        during parsing when CONT lines were merged), they are re-emitted as
        ``CONT`` substructures at ``level + 1``.

        Args:
            node: Node to format.

        Yields:
            GEDCOM line strings without line endings.
        """
        # Build "level [xref_id] tag"
        parts: list[str] = [str(node.level)]
        if node.xref_id:
            parts.append(node.xref_id)
        parts.append(node.tag)
        prefix = " ".join(parts)

        payload = node.payload

        if not payload:
            yield prefix
            return

        # Re-split on embedded newlines that the parser merged from CONT lines.
        segments = payload.split("\n")

        first = segments[0]
        first_emitted = f"{prefix} {first}" if first else prefix
        yield first_emitted

        # Warn if any emitted line exceeds 255 chars (GEDCOM 7 SHOULD limit).
        _MAX_LINE = 255
        if len(first_emitted) > _MAX_LINE:
            self._warnings.append(
                f"Line for {node.tag} at source line {node.line_num} is "
                f"{len(first_emitted)} chars (>{_MAX_LINE}); "
                f"GEDCOM 7 recommends \u2264{_MAX_LINE}."
            )

        if len(segments) > 1:
            cont_level = node.level + 1
            cont_prefix = f"{cont_level} CONT"
            for seg in segments[1:]:
                cont_line = f"{cont_prefix} {seg}" if seg else cont_prefix
                yield cont_line
                if len(cont_line) > _MAX_LINE:
                    self._warnings.append(
                        f"CONT line for {node.tag} at source line {node.line_num} is "
                        f"{len(cont_line)} chars (>{_MAX_LINE}); "
                        f"GEDCOM 7 recommends \u2264{_MAX_LINE}."
                    )
