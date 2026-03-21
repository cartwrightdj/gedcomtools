# -*- coding: utf-8 -*-
from __future__ import annotations
"""
======================================================================
 Project: gedcomtools
 File:    gedcom5/elements.py
 Author:  David J. Cartwright
 Purpose: GEDCOM 5.x element classes representing parsed GEDCOM records

 Created: 2026-01-01
 Updated:

======================================================================
"""
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
#
# Further information about the license: http://www.gnu.org/licenses/gpl-2.0.html

import re as regex
"""
Base GEDCOM element
"""

from sys import version_info
from gedcomtools.gedcom5.helpers import deprecated

from .tags import (
    GEDCOM_TAG_BIRTH,
    GEDCOM_TAG_BURIAL,
    GEDCOM_TAG_CENSUS,
    GEDCOM_TAG_CHANGE,
    GEDCOM_TAG_CONCATENATION,
    GEDCOM_TAG_CONTINUED,
    GEDCOM_TAG_DATE,
    GEDCOM_TAG_DEATH,
    GEDCOM_TAG_FAMILY,
    GEDCOM_TAG_FAMILY_CHILD,
    GEDCOM_TAG_FILE,
    GEDCOM_TAG_GIVEN_NAME,
    GEDCOM_TAG_INDIVIDUAL,
    GEDCOM_TAG_NAME,
    GEDCOM_TAG_OBJECT,
    GEDCOM_TAG_OCCUPATION,
    GEDCOM_TAG_PLACE,
    GEDCOM_TAG_PRIVATE,
    GEDCOM_TAG_SEX,
    GEDCOM_TAG_SOURCE,
    GEDCOM_TAG_SURNAME,
)

class Element(object):
    """GEDCOM element

    Each line in a GEDCOM file is an element with the format

    `level [pointer] tag [value]`

    where `level` and `tag` are required, and `pointer` and `value` are
    optional.  Elements are arranged hierarchically according to their
    level, and elements with a level of zero are at the top level.
    Elements with a level greater than zero are children of their
    parent.

    A pointer has the format `@pname@`, where `pname` is any sequence of
    characters and numbers. The pointer identifies the object being
    pointed to, so that any pointer included as the value of any
    element points back to the original object.  For example, an
    element may have a `FAMS` tag whose value is `@F1@`, meaning that this
    element points to the family record in which the associated person
    is a spouse. Likewise, an element with a tag of `FAMC` has a value
    that points to a family record in which the associated person is a
    child.

    See a GEDCOM file for examples of tags and their values.

    Tags available to an element are seen here: `gedcom.tags`
    """

    def __init__(self, level, xref, tag, value, crlf="\n", multi_line=True):
        # basic element info
        self.__level = level
        self.__xref = xref
        self.__tag = tag
        self.__value = value
        self.__crlf = crlf
        self._line_num: int = 0

        # structuring
        self.__parent = None
        self.__children = []

        if multi_line:
            self.set_multi_line_value(value)

    def _set_parent(self,parent: 'Element'):
        self.__parent = parent

    @property
    def parent(self):
        return self.__parent
    
    @property
    def level(self) -> int:
        """Returns the level of this element from within the GEDCOM file
        :rtype: int
        """
        return self.__level
    
    @level.setter
    def level(self, level):
        self.__level = level

    @property
    def xref(self):
        """Returns the pointer of this element from within the GEDCOM file
        :rtype: str
        """
        return self.__xref

    @property
    def tag(self):
        """Returns the tag of this element from within the GEDCOM file
        :rtype: str
        """
        return self.__tag
    @tag.setter
    def tag(self, tag):
        self.__tag = tag

    @property
    def value(self):
        return self.__value

    def describe(self) ->str:
        s = f"{self._line_num} [{type(self).__name__}] {self.xref} {self.level} {self.tag} {self.get_value()}"
        return s

    def get_value(self):
        """Return the value of this element from within the GEDCOM file
        :rtype: str
        """
        return self.__value

    def set_value(self, value):
        """Sets the value of this element
        :type value: str
        """
        self.__value = value

    @property
    def crlf(self) -> str:
        """Returns the line ending used for this element."""
        return self.__crlf

    def get_multi_line_value(self):
        """Returns the value of this element including concatenations or continuations
        :rtype: str
        """
        result = self.get_value()
        last_crlf = self.__crlf
        for element in self.get_child_elements():
            tag = element.tag
            if tag == GEDCOM_TAG_CONCATENATION:
                result += element.get_value()
                last_crlf = element.crlf
            elif tag == GEDCOM_TAG_CONTINUED:
                result += last_crlf + element.get_value()
                last_crlf = element.crlf
        return result

    def __available_characters(self):
        """Get the number of available characters of the elements original string
        :rtype: int
        """
        element_characters = len(self.to_gedcom_string())
        return 0 if element_characters > 255 else 255 - element_characters

    def __line_length(self, line):
        """@TODO Write docs.
        :type line: str
        :rtype: int
        """
        total_characters = len(line)
        available_characters = self.__available_characters()
        if total_characters <= available_characters:
            return total_characters
        spaces = 0
        while spaces < available_characters and line[available_characters - spaces - 1] == ' ':
            spaces += 1
        if spaces == available_characters:
            return available_characters
        return available_characters - spaces

    def __set_bounded_value(self, value):
        """@TODO Write docs.
        :type value: str
        :rtype: int
        """
        line_length = self.__line_length(value)
        self.set_value(value[:line_length])
        return line_length

    def __add_bounded_child(self, tag, value):
        """@TODO Write docs.
        :type tag: str
        :type value: str
        :rtype: int
        """
        child = self.new_child_element(tag)
        return child.__set_bounded_value(value)

    def __add_concatenation(self, string):
        """@TODO Write docs.
        :rtype: str
        """
        index = 0
        size = len(string)
        while index < size:
            index += self.__add_bounded_child(GEDCOM_TAG_CONCATENATION, string[index:])

    def set_multi_line_value(self, value):
        """Sets the value of this element, adding concatenation and continuation lines when necessary
        :type value: str
        """
        self.set_value('')
        self.get_child_elements()[:] = [child for child in self.get_child_elements() if
                                        child.tag not in (GEDCOM_TAG_CONCATENATION, GEDCOM_TAG_CONTINUED)]

        lines = value.splitlines()
        if lines:
            line = lines.pop(0)
            n = self.__set_bounded_value(line)
            self.__add_concatenation(line[n:])

            for line in lines:
                n = self.__add_bounded_child(GEDCOM_TAG_CONTINUED, line)
                self.__add_concatenation(line[n:])

    def __getitem__(self,item):
        return self.sub_record(item)
    
    def sub_record(self, tag: str):
        for r in self.__children:
            if r.tag == tag: return r
        return None
    
    def sub_records(self, tag: str | None = None):
        if tag is None:
            return self.__children
        return [r for r in self.__children if r.tag == tag]
    
    def get_child_elements(self):
        """Returns the direct child elements of this element
        :rtype: list of Element
        """
        return self.__children

    def new_child_element(self, tag, pointer="", value=""):
        """Creates and returns a new child element of this element

        :type tag: str
        :type pointer: str
        :type value: str
        :rtype: Element
        """
        
        # Differentiate between the type of the new child element
        if tag == GEDCOM_TAG_FAMILY:
            child_element = FamilyRecord(self.level + 1, pointer, tag, value, self.__crlf)
        elif tag == GEDCOM_TAG_FILE:
            child_element = FileElement(self.level + 1, pointer, tag, value, self.__crlf)
        elif tag == GEDCOM_TAG_INDIVIDUAL:
            child_element = IndividualRecord(self.level + 1, pointer, tag, value, self.__crlf)
        elif tag == GEDCOM_TAG_OBJECT:
            child_element = ObjectRecord(self.level + 1, pointer, tag, value, self.__crlf)
        else:
            child_element = Element(self.level + 1, pointer, tag, value, self.__crlf)

        self.add_child_element(child_element)

        return child_element

    def add_child_element(self, element):
        """Adds a child element to this element

        :type element: Element
        """
        self.get_child_elements().append(element)
        element.set_parent_element(self)

        return element

    def get_parent_element(self):
        """Returns the parent element of this element
        :rtype: Element
        """
        return self.__parent

    def set_parent_element(self, element):
        """Adds a parent element to this element

        There's usually no need to call this method manually,
        `add_child_element()` calls it automatically.

        :type element: Element
        """
        self.__parent = element

    @deprecated
    def get_individual(self):
        """Returns this element and all of its sub-elements represented as a GEDCOM string
        ::deprecated:: As of version 1.0.0 use `to_gedcom_string()` method instead
        :rtype: str
        """
        return self.to_gedcom_string(True)

    def to_gedcom_string(self, recursive=False):
        """Formats this element and optionally all of its sub-elements into a GEDCOM string
        :type recursive: bool
        :rtype: str
        """

        result = str(self.level)

        if self.xref:
            result += ' ' + self.xref

        result += ' ' + self.tag

        if self.get_value() != "":
            result += ' ' + self.get_value()

        

        if self.level < 0:
            result = ''

        if recursive:
            for child_element in self.get_child_elements():
                result += self.__crlf
                result += child_element.to_gedcom_string(True)

        return result

    def __str__(self):
        """:rtype: str"""
        if version_info[0] >= 3:
            return self.to_gedcom_string()

        return self.to_gedcom_string().encode('utf-8-sig')

class RootElement(Element):
    """Virtual GEDCOM root element containing all logical records as children"""

    def __init__(self, level=-1, pointer="", tag="ROOT", value="", crlf="\n", multi_line=True):
        super(RootElement, self).__init__(level, pointer, tag, value, crlf, multi_line)

class HeaderRecord(Element):
    pass

class SubmitterRecord(Element):
    pass

class FamilyRecord(Element):

    def get_tag(self):
        return GEDCOM_TAG_FAMILY

class FileElement(Element):

    def get_tag(self):
        return GEDCOM_TAG_FILE

class IndividualRecord(Element):

    def get_tag(self):
        return GEDCOM_TAG_INDIVIDUAL

    def is_deceased(self):
        """Checks if this individual is deceased
        :rtype: bool
        """
        for child in self.get_child_elements():
            if child.tag == GEDCOM_TAG_DEATH:
                return True

        return False

    def is_child(self):
        """Checks if this element is a child of a family
        :rtype: bool
        """
        found_child = False

        for child in self.get_child_elements():
            if child.tag == GEDCOM_TAG_FAMILY_CHILD:
                found_child = True

        return found_child

    def is_private(self):
        """Checks if this individual is marked private
        :rtype: bool
        """
        for child in self.get_child_elements():
            if child.tag == GEDCOM_TAG_PRIVATE:
                private = child.get_value()
                if private == 'Y':
                    return True

        return False

    def get_name(self):
        """Returns an individual's names as a tuple: (`str` given_name, `str` surname)
        :rtype: tuple
        """
        given_name = ""
        surname = ""

        # Return the first GEDCOM_TAG_NAME that is found.
        # Alternatively as soon as we have both the GEDCOM_TAG_GIVEN_NAME and _SURNAME return those.
        found_given_name = False
        found_surname_name = False

        for child in self.get_child_elements():
            if child.tag == GEDCOM_TAG_NAME:
                # Some GEDCOM files don't use child tags but instead
                # place the name in the value of the NAME tag.
                if child.get_value() != "":
                    name = child.get_value().split('/')

                    if len(name) > 0:
                        given_name = name[0].strip()
                        if len(name) > 1:
                            surname = name[1].strip()

                    return given_name, surname

                for childOfChild in child.get_child_elements():

                    if childOfChild.tag == GEDCOM_TAG_GIVEN_NAME:
                        given_name = childOfChild.get_value()
                        found_given_name = True

                    if childOfChild.tag == GEDCOM_TAG_SURNAME:
                        surname = childOfChild.get_value()
                        found_surname_name = True

                if found_given_name and found_surname_name:
                    return given_name, surname

        # If we reach here we are probably returning empty strings
        return given_name, surname

    def get_all_names(self):
        return [a.get_value() for a in self.get_child_elements() if a.tag == GEDCOM_TAG_NAME]

    def surname_match(self, surname_to_match):
        """Matches a string with the surname of an individual
        :type surname_to_match: str
        :rtype: bool
        """
        (given_name, surname) = self.get_name()
        return bool(regex.search(surname_to_match, surname, regex.IGNORECASE))

    @deprecated
    def given_match(self, name):
        """Matches a string with the given name of an individual
        ::deprecated:: As of version 1.0.0 use `given_name_match()` method instead
        :type name: str
        :rtype: bool
        """
        return self.given_name_match(name)

    def given_name_match(self, given_name_to_match):
        """Matches a string with the given name of an individual
        :type given_name_to_match: str
        :rtype: bool
        """
        (given_name, surname) = self.get_name()
        return bool(regex.search(given_name_to_match, given_name, regex.IGNORECASE))

    def get_gender(self):
        """Returns the gender of a person in string format
        :rtype: str
        """
        gender = ""

        for child in self.get_child_elements():
            if child.tag == GEDCOM_TAG_SEX:
                gender = child.get_value()

        return gender

    def get_birth_data(self):
        """Returns the birth data of a person formatted as a tuple: (`str` date, `str` place, `list` sources)
        :rtype: tuple
        """
        date = ""
        place = ""
        sources = []

        for child in self.get_child_elements():
            if child.tag == GEDCOM_TAG_BIRTH:
                for childOfChild in child.get_child_elements():

                    if childOfChild.tag == GEDCOM_TAG_DATE:
                        date = childOfChild.get_value()

                    if childOfChild.tag == GEDCOM_TAG_PLACE:
                        place = childOfChild.get_value()

                    if childOfChild.tag == GEDCOM_TAG_SOURCE:
                        sources.append(childOfChild.get_value())

        return date, place, sources

    def get_birth_year(self):
        """Returns the birth year of a person as an integer, or ``None`` if unknown.
        :rtype: int or None
        """
        for child in self.get_child_elements():
            if child.tag == GEDCOM_TAG_BIRTH:
                for childOfChild in child.get_child_elements():
                    if childOfChild.tag == GEDCOM_TAG_DATE:
                        date_split = childOfChild.get_value().split()
                        if date_split:
                            try:
                                return int(date_split[-1])
                            except ValueError:
                                pass
        return None

    def get_death_data(self):
        """Returns the death data of a person formatted as a tuple: (`str` date, `str` place, `list` sources)
        :rtype: tuple
        """
        date = ""
        place = ""
        sources = []

        for child in self.get_child_elements():
            if child.tag == GEDCOM_TAG_DEATH:
                for childOfChild in child.get_child_elements():
                    if childOfChild.tag == GEDCOM_TAG_DATE:
                        date = childOfChild.get_value()
                    if childOfChild.tag == GEDCOM_TAG_PLACE:
                        place = childOfChild.get_value()
                    if childOfChild.tag == GEDCOM_TAG_SOURCE:
                        sources.append(childOfChild.get_value())

        return date, place, sources

    def get_death_year(self):
        """Returns the death year of a person as an integer, or ``None`` if unknown.
        :rtype: int or None
        """
        for child in self.get_child_elements():
            if child.tag == GEDCOM_TAG_DEATH:
                for childOfChild in child.get_child_elements():
                    if childOfChild.tag == GEDCOM_TAG_DATE:
                        date_split = childOfChild.get_value().split()
                        if date_split:
                            try:
                                return int(date_split[-1])
                            except ValueError:
                                pass
        return None

    @deprecated
    def get_burial(self):
        """Returns the burial data of a person formatted as a tuple: (`str` date, `str` place, `list` sources)
        ::deprecated:: As of version 1.0.0 use `get_burial_data()` method instead
        :rtype: tuple
        """
        return self.get_burial_data()

    def get_burial_data(self):
        """Returns the burial data of a person formatted as a tuple: (`str` date, `str` place, `list` sources)
        :rtype: tuple
        """
        date = ""
        place = ""
        sources = []

        for child in self.get_child_elements():
            if child.tag == GEDCOM_TAG_BURIAL:
                for childOfChild in child.get_child_elements():

                    if childOfChild.tag == GEDCOM_TAG_DATE:
                        date = childOfChild.get_value()

                    if childOfChild.tag == GEDCOM_TAG_PLACE:
                        place = childOfChild.get_value()

                    if childOfChild.tag == GEDCOM_TAG_SOURCE:
                        sources.append(childOfChild.get_value())

        return date, place, sources

    @deprecated
    def get_census(self):
        """Returns a list of censuses of an individual formatted as tuples: (`str` date, `str` place, `list` sources)
        ::deprecated:: As of version 1.0.0 use `get_census_data()` method instead
        :rtype: list of tuple
        """
        return self.get_census_data()

    def get_census_data(self):
        """Returns a list of censuses of an individual formatted as tuples: (`str` date, `str` place, `list` sources)
        :rtype: list of tuple
        """
        census = []

        for child in self.get_child_elements():
            if child.tag == GEDCOM_TAG_CENSUS:

                date = ''
                place = ''
                sources = []

                for childOfChild in child.get_child_elements():

                    if childOfChild.tag == GEDCOM_TAG_DATE:
                        date = childOfChild.get_value()

                    if childOfChild.tag == GEDCOM_TAG_PLACE:
                        place = childOfChild.get_value()

                    if childOfChild.tag == GEDCOM_TAG_SOURCE:
                        sources.append(childOfChild.get_value())

                census.append((date, place, sources))

        return census

    def get_last_change_date(self):
        """Returns the date of when the person data was last changed formatted as a string
        :rtype: str
        """
        date = ""

        for child in self.get_child_elements():
            if child.tag == GEDCOM_TAG_CHANGE:
                for childOfChild in child.get_child_elements():
                    if childOfChild.tag == GEDCOM_TAG_DATE:
                        date = childOfChild.get_value()

        return date

    def get_occupation(self):
        """Returns the occupation of a person
        :rtype: str
        """
        occupation = ""

        for child in self.get_child_elements():
            if child.tag == GEDCOM_TAG_OCCUPATION:
                occupation = child.get_value()

        return occupation

    def birth_year_match(self, year):
        """Returns `True` if the given year matches the birth year of this person.
        Returns ``False`` if the birth year is unknown.
        :type year: int
        :rtype: bool
        """
        by = self.get_birth_year()
        return by is not None and by == year

    def birth_range_match(self, from_year, to_year):
        """Checks if the birth year of a person lies within the given range.
        Returns ``False`` if the birth year is unknown.
        :type from_year: int
        :type to_year: int
        :rtype: bool
        """
        birth_year = self.get_birth_year()
        return birth_year is not None and from_year <= birth_year <= to_year

    def death_year_match(self, year):
        """Returns `True` if the given year matches the death year of this person.
        Returns ``False`` if the death year is unknown.
        :type year: int
        :rtype: bool
        """
        dy = self.get_death_year()
        return dy is not None and dy == year

    def death_range_match(self, from_year, to_year):
        """Checks if the death year of a person lies within the given range.
        Returns ``False`` if the death year is unknown.
        :type from_year: int
        :type to_year: int
        :rtype: bool
        """
        death_year = self.get_death_year()
        return death_year is not None and from_year <= death_year <= to_year

    def criteria_match(self, criteria):
        """Checks if this individual matches all of the given criteria

        `criteria` is a colon-separated list, where each item in the
        list has the form [name]=[value]. The following criteria are supported:

        surname=[name]
             Match a person with [name] in any part of the `surname`.
        given_name=[given_name]
             Match a person with [given_name] in any part of the given `given_name`.
        birth=[year]
             Match a person whose birth year is a four-digit [year].
        birth_range=[from_year-to_year]
             Match a person whose birth year is in the range of years from
             [from_year] to [to_year], including both [from_year] and [to_year].

        :type criteria: str
        :rtype: bool
        """

        # Check if criteria is a valid criteria and can be split by `:` and `=` characters
        try:
            for criterion in criteria.split(':'):
                criterion.split('=')
        except ValueError:
            return False

        match = True

        for criterion in criteria.split(':'):
            key, value = criterion.split('=', 1)

            if key == "surname" and not self.surname_match(value):
                match = False
            elif key == "name" and not self.given_name_match(value):
                match = False
            elif key == "birth":

                try:
                    year = int(value)
                    if not self.birth_year_match(year):
                        match = False
                except ValueError:
                    match = False

            elif key == "birth_range":

                try:
                    from_year, to_year = value.split('-')
                    from_year = int(from_year)
                    to_year = int(to_year)
                    if not self.birth_range_match(from_year, to_year):
                        match = False
                except ValueError:
                    match = False

            elif key == "death":

                try:
                    year = int(value)
                    if not self.death_year_match(year):
                        match = False
                except ValueError:
                    match = False

            elif key == "death_range":

                try:
                    from_year, to_year = value.split('-')
                    from_year = int(from_year)
                    to_year = int(to_year)
                    if not self.death_range_match(from_year, to_year):
                        match = False
                except ValueError:
                    match = False

        return match

    def describe(self) -> str:
        """
        Return a human-readable description of this individual.
        Includes name, gender, birth/death data, and occupation if available.
        """
        given, surname = self.get_name()
        full_name = f"{given} {surname}".strip() or "(no name)"

        gender = self.get_gender()

        birth_date, birth_place, _ = self.get_birth_data()
        death_date, death_place, _ = self.get_death_data()
        occupation = self.get_occupation()

        parts = [f"Name: {full_name}"]
        if gender:
            parts.append(f"Gender: {gender}")

        if birth_date or birth_place:
            birth_str = f"Born: {birth_date or ''}".strip()
            if birth_place:
                birth_str += f" in {birth_place}"
            parts.append(birth_str)

        if death_date or death_place:
            death_str = f"Died: {death_date or ''}".strip()
            if death_place:
                death_str += f" in {death_place}"
            parts.append(death_str)

        if occupation:
            parts.append(f"Occupation: {occupation}")

        return "; ".join(parts)
    
class ObjectRecord(Element):

    def is_object(self):
        """Checks if this element is an actual object
        :rtype: bool
        """
        return self.tag == GEDCOM_TAG_OBJECT

class RepositoryRecord(Element):
    pass

class SourceRecord(Element):
    pass

