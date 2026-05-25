CLI Reference
=============

``gedcomtools`` can inspect, validate, convert, repair, diff, merge, and export
GEDCOM 5.x and GEDCOM 7 files.

Raw JSON and stdout export
--------------------------

Use ``export --to raw-json`` to preserve the parsed GEDCOM record tree as JSON
without converting it to GEDCOM X:

.. code-block:: bash

   gedcomtools export family.ged --to raw-json --out family.raw.json
   gedcomtools export family7.ged --to raw-json --out family7.raw.json

``--to json`` is accepted as an alias for ``raw-json``. The JSON document
contains the source file, detected GEDCOM format/version, and a ``records``
array. Each node includes ``level``, ``xref``, ``tag``, ``value``, ``pointer``,
``line``, and ``children``. GEDCOM 7 nodes also include ``uri`` and
``extension`` metadata when available.

Use ``--out -`` to send generated output to stdout:

.. code-block:: bash

   gedcomtools export family.ged --to raw-json --out - | jq '.records | length'
   gedcomtools convert family.ged --to gx --out - > family.gedcomx.json
   gedcomtools convert family.ged --to g7 --out - > family7.ged

When stdout carries the generated payload, progress/status text is written to
stderr. CSV export normally creates several files; with ``--out -`` it emits a
JSON envelope containing each CSV document as a string.

For scripts and agent integrations, add ``--quiet`` to suppress status text and
``--compact`` to emit compact JSON:

.. code-block:: bash

   gedcomtools convert family.ged --to gx --out - --quiet --compact
   gedcomtools export family.ged --to raw-json --out - --compact

.. automodule:: gedcomtools.gedcomx.cli
   :members:

.. automodule:: gedcomtools.gedcom7.g7cli
   :members:

gxcli Guide
-----------

.. toctree::
   :maxdepth: 2

   ../gxcli
