MCP Server
==========

``gedcomtools`` includes an optional stdio MCP server for exposing GEDCOM
tools to MCP-capable clients.

Installation
------------

Install the MCP extra:

.. code-block:: bash

   pip install "gedcomtools[mcp]"

From a source checkout:

.. code-block:: bash

   pip install -e ".[mcp]"

Run the server with:

.. code-block:: bash

   gedcomtools-mcp

The server uses stdio transport, which is the transport expected by many MCP
desktop and agent clients.

Client Configuration
--------------------

Example MCP client configuration:

.. code-block:: json

   {
     "mcpServers": {
       "gedcomtools": {
         "command": "gedcomtools-mcp"
       }
     }
   }

Recommended Workflow
--------------------

Start each session by calling:

.. code-block:: text

   man()

The ``man`` tool returns the server guide, a tool index, and recommended first
calls. Use ``man("tool_name")`` before using an unfamiliar tool to get the
exact parameters, output shape, caveats, and examples.

For GEDCOM files, a typical workflow is:

1. Call ``load_gedcom(file_path)`` to detect the file type and get summary
   counts.
2. For GEDCOM 5.x, use ``list_individuals`` to find an xref, then use
   relationship tools such as ``get_parents``, ``get_children``,
   ``get_spouses``, ``get_ancestors``, and ``get_descendants``.
3. For evidence and raw data, use ``get_individual``, ``get_family``,
   ``get_sources``, and ``get_record_tree``.
4. For GEDCOM 7, use ``validate_gedcom7`` and ``inspect_gedcom7``.
5. For GEDCOM X JSON, use ``list_gedcomx_collections``,
   ``search_gedcomx_persons``, ``get_gedcomx_object``, and schema/reference
   tools.

Tool Groups
-----------

Help and runtime:

* ``man``
* ``server_info``

File loading and format detection:

* ``load_gedcom``
* ``get_gedcom_version``
* ``summarize_gedcom5x``
* ``summarize_gedcomx_json``

GEDCOM 5.x people and family navigation:

* ``list_individuals``
* ``get_individual``
* ``get_person_families``
* ``get_parents``
* ``get_children``
* ``get_spouses``
* ``get_siblings``
* ``get_ancestors``
* ``get_descendants``
* ``get_family``
* ``find_relationship_path``

GEDCOM 5.x records and evidence:

* ``get_sources``
* ``get_record_tree``

Conversion and graph export:

* ``convert_gedcom5x_to_gedcomx``
* ``export_raw_gedcom_json``
* ``export_arango_graph``

``export_raw_gedcom_json`` returns the faithful GEDCOM 5.x or GEDCOM 7 parse
tree as JSON, optionally writing the same document to disk. Use it when an
agent needs the complete GEDCOM structure rather than a normalized summary or
GEDCOM X conversion.

``export_arango_graph`` writes ``nodes.jsonl`` and ``edges.jsonl``. Despite the
legacy tool name, the node file contains all graph node types, not only people.

GEDCOM 7:

* ``validate_gedcom7``
* ``inspect_gedcom7``

GEDCOM X JSON browsing:

* ``list_gedcomx_collections``
* ``list_gedcomx_objects``
* ``get_gedcomx_object``
* ``search_gedcomx_persons``
* ``get_gedcomx_person_relationships``
* ``resolve_gedcomx_reference``

GEDCOM X schema inspection:

* ``get_gedcomx_schema_class``
* ``search_gedcomx_schema``

Notes
-----

Parsed GEDCOM and GEDCOM X files are cached in-process during a normal MCP
session, so repeated calls against the same file reuse loaded data.
