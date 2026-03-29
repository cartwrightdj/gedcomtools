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
- CONC is not emitted; it was removed in GEDCOM 7.0.
- Long single-line values that exceed 255 chars are emitted as-is with a
  warning.  GEDCOM 7 removed CONC, so there is no standard way to split a
  non-multiline value without changing its semantics: every CONT continuation
  merges back as ``\\n`` on re-parse, which would corrupt URLs, PAGE refs,
  and even free-text NOTE values (a paragraph break != a line-wrap).
  The 255-char limit is a SHOULD, not a MUST.
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

        Returns the line-length warnings collected during serialization.
        Raises :class:`FileNotFoundError` if the destination directory does
        not exist.
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

    _MAX_LINE = 255  # GEDCOM 7 recommended line-length limit

    def _emit_segment(self, text: str, line_prefix: str, warn_tag: str) -> Iterator[str]:
        """Yield one line for *text*, warning if it exceeds the line-length limit.

        A CONT newline is a semantic paragraph-break, not a mere line-wrap.
        Inserting CONT mid-segment would change the payload value on re-parse
        (every CONT merges back as ``\\n``).  Therefore this method always emits
        exactly one line; long values generate a warning.

        Args:
            text:        Payload text for this logical segment (no embedded newlines).
            line_prefix: ``"level [xref] tag"`` string for the first line.
            warn_tag:    Tag name used in the warning message.

        Yields:
            A single GEDCOM line string without a line ending.
        """
        if not text:
            yield line_prefix
            return

        line = f"{line_prefix} {text}"
        if len(line) > self._MAX_LINE:
            self._warnings.append(
                f"Line exceeds {self._MAX_LINE} chars (tag={warn_tag!r}, "
                f"len={len(line)}): {line[:80]!r}…"
            )
        yield line

    def _format_lines(self, node: GedcomStructure) -> Iterator[str]:
        """Format one node as one or more GEDCOM line strings.

        Embedded ``\\n`` characters (merged from CONT lines during parsing)
        are re-split into CONT substructures.  Any segment that would exceed
        ``_MAX_LINE`` characters is additionally wrapped into further CONT
        lines so the output always stays within the recommended limit.

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
        line_prefix = " ".join(parts)
        cont_prefix = f"{node.level + 1} CONT"

        payload = node.payload

        if not payload:
            yield line_prefix
            return

        # Re-split on embedded newlines from CONT merging, then emit each
        # segment as a single line.  CONT is a semantic paragraph separator —
        # inserting it mid-segment would add a spurious \n on re-parse.
        segments = payload.split("\n")
        first_prefix = line_prefix
        for seg in segments:
            yield from self._emit_segment(seg, first_prefix, node.tag)
            # All segments after the first are continuations.
            first_prefix = cont_prefix
