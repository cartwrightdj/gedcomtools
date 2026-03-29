# -*- coding: utf-8 -*-
# ======================================================================
#  Project: gedcomtools
#  File:    gedcom5/parser.py
#  Author:  David J. Cartwright
#  Purpose: GEDCOM 5.x file parser producing a tree of GedcomElement objects
#  Created: 2026-01-01
# ======================================================================
"""Parse GEDCOM 5.x files into the project’s element tree representation."""

# Python GEDCOM Parser
#
# Copyright (C) 2018 Damon Brodie (damon.brodie at gmail.com)
# Copyright (C) 2018-2019 Nicklas Reincke (contact at reynke.com)
# Copyright (C) 2016 Andreas Oberritter
# Copyright (C) 2012 Madeleine Price Ball
# Copyright (C) 2005 Daniel Zappala (zappala at cs.byu.edu)
# Copyright (C) 2005 Brigham Young University
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# GEDCOM 5.x file parser — builds a typed element tree from a .ged file.
#
# All high-level analysis lives in Gedcom5.
# This module is the raw parsing engine only.

import re as regex
from typing import List, Union

from .elements import (
    Element, FamilyRecord, FileElement, HeaderRecord,
    IndividualRecord, ObjectRecord, RepositoryRecord,
    RootElement, SourceRecord, SubmitterRecord,
)
from .tags import (
    GEDCOM_TAG_CONCATENATION,
    GEDCOM_TAG_FAMILY,
    GEDCOM_TAG_FILE,
    GEDCOM_TAG_HEADER,
    GEDCOM_TAG_INDIVIDUAL,
    GEDCOM_TAG_OBJECT,
    GEDCOM_TAG_REPOSITORY,
    GEDCOM_TAG_SOURCE,
    GEDCOM_TAG_SUBMITTER,
)


def _normalize_xref(xref: str) -> str:
    """Normalize an xref pointer for case-insensitive comparison.

    Strips surrounding whitespace and uppercases the value so that
    ``@i1@`` and ``@I1@`` compare equal.
    """
    return xref.strip().upper() if xref else ""


class GedcomFormatViolationError(Exception):
    """Raised when a line violates the GEDCOM 5.5 format."""


class Gedcom5x:
    """Low-level GEDCOM 5.x parser.

    Reads a ``.ged`` file and builds a typed element tree.  Typed
    record collections (``individuals``, ``families``, etc.) and a
    dictionary lookup (``get_element_dictionary()``) are the primary
    outputs consumed by :class:`~gedcomtools.gedcom5.gedcom5.Gedcom5`.
    """

    def __init__(self) -> None:
        self.__header: List[HeaderRecord] = []
        self.__submitters: List[SubmitterRecord] = []
        self.__individuals: List[IndividualRecord] = []
        self.__families: List[FamilyRecord] = []
        self.__sources: List[SourceRecord] = []
        self.__repositories: List[RepositoryRecord] = []
        self.__objects: List[ObjectRecord] = []
        self.__root_element: RootElement = RootElement()

    # ------------------------------------------------------------------
    # Typed record collections
    # ------------------------------------------------------------------

    @property
    def individuals(self) -> List[IndividualRecord]:
        """Return the individual records."""
        return self.__individuals

    @property
    def families(self) -> List[FamilyRecord]:
        """Return the family records."""
        return self.__families

    @property
    def sources(self) -> List[SourceRecord]:
        """Return the source records."""
        return self.__sources

    @property
    def repositories(self) -> List[RepositoryRecord]:
        """Return the repository records."""
        return self.__repositories

    @property
    def objects(self) -> List[ObjectRecord]:
        """Return the multimedia object records."""
        return self.__objects

    @property
    def header(self) -> List[HeaderRecord]:
        """Return the header record."""
        return self.__header

    @property
    def submitters(self) -> List[SubmitterRecord]:
        """Return the submitter records."""
        return self.__submitters

    # ------------------------------------------------------------------
    # Element lookup
    # ------------------------------------------------------------------

    def get_element_dictionary(self) -> dict:
        """Return all xref-identified records keyed by uppercased xref.

        :rtype: dict of Element
        """
        return {
            _normalize_xref(element.xref): element
            for element in self.get_root_child_elements()
            if element.xref
        }

    def get_root_child_elements(self) -> List[Element]:
        """Return top-level records in document order."""
        return self.__root_element.get_child_elements()

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def parse_file(self, file_path: str, strict: bool = True) -> None:
        """Open and parse a GEDCOM 5.x file.

        :type file_path: str
        :type strict: bool
        """
        with open(file_path, 'rb') as gedcom_stream:
            self.parse(gedcom_stream, strict)

    def parse(self, gedcom_stream, strict: bool = True) -> None:
        """Parse a byte stream as GEDCOM 5.x data.

        Resets all collections before parsing.

        :type gedcom_stream: binary file stream
        :type strict: bool
        """
        self.__header = []
        self.__submitters = []
        self.__individuals = []
        self.__families = []
        self.__sources = []
        self.__repositories = []
        self.__objects = []
        self.__root_element = RootElement()

        record_map: dict[int, Union[Element, None]] = {
            -1: self.__root_element,
            0: None, 1: None, 2: None, 3: None, 4: None, 5: None,
        }

        line_number = 1
        for line in gedcom_stream:
            element = self.__parse_line(line_number, line.decode('utf-8-sig'), strict)
            element._line_num = line_number

            if isinstance(element, HeaderRecord):
                self.__header.append(element)
            elif isinstance(element, IndividualRecord):
                self.__individuals.append(element)
            elif isinstance(element, FamilyRecord):
                self.__families.append(element)
            elif isinstance(element, SourceRecord):
                self.__sources.append(element)
            elif isinstance(element, RepositoryRecord):
                self.__repositories.append(element)
            elif isinstance(element, ObjectRecord):
                self.__objects.append(element)
            elif isinstance(element, SubmitterRecord):
                self.__submitters.append(element)

            element._set_parent(record_map[element.level - 1])
            record_map[element.level] = element
            record_map[element.level - 1].add_child_element(element)
            line_number += 1

    @staticmethod
    def __parse_line(line_number: int, line: str, strict: bool = True) -> Element:
        """Parse one GEDCOM line and return the appropriate Element subclass."""

        level_regex = '^(0|[1-9]+[0-9]*) '
        pointer_regex = r'(@[^@]+@\s|)'
        tag_regex = '([A-Za-z0-9_]+)'
        value_regex = '( [^\n\r]*|)'
        end_of_line_regex = '([\r\n]{1,2})'
        gedcom_line_regex = level_regex + pointer_regex + tag_regex + value_regex + end_of_line_regex

        regex_match = regex.match(gedcom_line_regex, line)

        if regex_match is None:
            if strict:
                raise GedcomFormatViolationError(
                    f"Line <{line_number}:{line}> violates GEDCOM format 5.5\n"
                    "See: https://chronoplexsoftware.com/gedcomvalidator/gedcom/gedcom-5.5.pdf"
                )
            # Quirk: last line may be missing CRLF
            last_line_regex = level_regex + pointer_regex + tag_regex + value_regex
            regex_match = regex.match(last_line_regex, line)
            if regex_match is not None:
                line_parts = regex_match.groups()
                level = int(line_parts[0])
                pointer = line_parts[1].rstrip(' ')
                tag = line_parts[2]
                value = line_parts[3][1:]
                crlf = '\n'
            else:
                # Quirk: embedded CR produces a fragment with no level/tag —
                # treat as CONC so text is not silently dropped.
                cont_line_regex = '([^\n\r]*|)' + end_of_line_regex
                regex_match = regex.match(cont_line_regex, line)
                line_parts = regex_match.groups()
                level = 1
                pointer = ""
                tag = GEDCOM_TAG_CONCATENATION
                value = line_parts[0]
                crlf = line_parts[1] if len(line_parts) > 1 else '\n'
        else:
            line_parts = regex_match.groups()
            level = int(line_parts[0])
            pointer = line_parts[1].rstrip(' ')
            tag = line_parts[2]
            value = line_parts[3][1:]
            crlf = line_parts[4]

        if tag == GEDCOM_TAG_HEADER:
            return HeaderRecord(level, pointer, tag, value, crlf, multi_line=False)
        if tag == GEDCOM_TAG_INDIVIDUAL:
            return IndividualRecord(level, pointer, tag, value, crlf, multi_line=False)
        if tag == GEDCOM_TAG_FAMILY:
            return FamilyRecord(level, pointer, tag, value, crlf, multi_line=False)
        if tag == GEDCOM_TAG_FILE:
            return FileElement(level, pointer, tag, value, crlf, multi_line=False)
        if tag == GEDCOM_TAG_OBJECT and level == 0:
            return ObjectRecord(level, pointer, tag, value, crlf, multi_line=False)
        if tag == GEDCOM_TAG_SOURCE and level == 0:
            return SourceRecord(level, pointer, tag, value, crlf, multi_line=False)
        if tag == GEDCOM_TAG_REPOSITORY and level == 0:
            return RepositoryRecord(level, pointer, tag, value, crlf, multi_line=False)
        if tag == GEDCOM_TAG_SUBMITTER and level == 0:
            return SubmitterRecord(level, pointer, tag, value, crlf, multi_line=False)
        return Element(level, pointer, tag, value, crlf, multi_line=False)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def save_gedcom(self, open_file) -> None:
        """Write the parsed GEDCOM tree to *open_file* in GEDCOM 5.x format."""
        open_file.write(self.__root_element.to_gedcom_string(True))

    def print_gedcom(self) -> None:
        """Write the parsed GEDCOM tree to stdout."""
        import sys
        self.save_gedcom(sys.stdout)
