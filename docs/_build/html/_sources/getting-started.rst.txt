Getting Started
===============

Installation
------------

.. code-block:: bash

   pip install gedcomtools

Quick Example
-------------

Convert a GEDCOM 5.x file to GedcomX JSON:

.. code-block:: bash

   gedcomtools convert family.ged output.json -gx

Or use the Python API directly:

.. code-block:: python

   from gedcomtools.gedcom5.parser import Gedcom5x
   from gedcomtools.gedcomx.conversion import GedcomConverter

   parser = Gedcom5x()
   parser.parse_file("family.ged")

   converter = GedcomConverter()
   gx = converter.Gedcom5x_GedcomX(parser)

   print(f"Persons: {len(gx.persons)}")
   print(f"Relationships: {len(gx.relationships)}")

Working with GedcomX objects
-----------------------------

.. code-block:: python

   from gedcomtools.gedcomx.gedcomx import GedcomX
   from gedcomtools.gedcomx.person import Person, QuickPerson
   from gedcomtools.gedcomx.name import Name

   gx = GedcomX()

   # Create a person with a GEDCOM-style name
   person = QuickPerson("John /Smith/", dob="1900-01-01")
   gx.add_person(person)

   # Look up by id
   p = gx.get_person_by_id(person.id)
   print(p.name)   # "John Smith"

Serialization
-------------

.. code-block:: python

   from gedcomtools.gedcomx.serialization import Serialization
   import json

   data = Serialization.serialize(gx)
   with open("output.json", "w") as f:
       json.dump(data, f, indent=2)

CLI Exit Codes
--------------

.. list-table::
   :header-rows: 1

   * - Code
     - Constant
     - Meaning
   * - 0
     - ``OK``
     - Success
   * - 1
     - ``ERR_FILE_NOT_FOUND``
     - Source file does not exist
   * - 2
     - ``ERR_UNKNOWN_SOURCE_TYPE``
     - Cannot determine source format
   * - 3
     - ``ERR_UNSUPPORTED_CONV``
     - Conversion path not yet implemented
   * - 4
     - ``ERR_CONVERSION_FAILED``
     - Conversion raised an exception
   * - 5
     - ``ERR_IO``
     - Could not write output file
