Using MCP With Agents
=====================

``gedcomtools-mcp`` is a local stdio MCP server. Agent clients start it as a
subprocess, discover its tools, and call those tools with local file paths.

Install the optional MCP extra before configuring an agent:

.. code-block:: bash

   pip install "gedcomtools[mcp]"

For a source checkout, install the checkout into the same Python environment
that the agent will use:

.. code-block:: bash

   pip install -e ".[mcp]"

Quick Smoke Test
----------------

Before wiring an agent to the server, make sure the command is available:

.. code-block:: bash

   gedcomtools-mcp

The command is a stdio server, so it waits for MCP JSON-RPC traffic and does
not print an interactive prompt. Stop it with ``Ctrl-C`` after confirming it
starts without an import error.

Codex
-----

Codex can manage MCP servers with its ``codex mcp`` subcommand. Add the local
stdio server with:

.. code-block:: bash

   codex mcp add gedcomtools -- gedcomtools-mcp

Then confirm that Codex knows about the server:

.. code-block:: bash

   codex mcp list
   codex mcp get gedcomtools

You can also configure Codex manually in ``~/.codex/config.toml``:

.. code-block:: toml

   [mcp_servers.gedcomtools]
   command = "gedcomtools-mcp"

If ``gedcomtools-mcp`` is installed in a virtual environment that is not on the
agent process ``PATH``, use the absolute executable path:

.. code-block:: toml

   [mcp_servers.gedcomtools]
   command = "/path/to/venv/bin/gedcomtools-mcp"

Start a new Codex session after changing MCP configuration. A useful first
prompt is:

.. code-block:: text

   Use the gedcomtools MCP server. Call man(), then summarize /path/to/tree.ged.

Claude Code
-----------

Claude Code can add the same local stdio server with:

.. code-block:: bash

   claude mcp add gedcomtools -- gedcomtools-mcp

For a project-shared configuration, use project scope:

.. code-block:: bash

   claude mcp add --scope project gedcomtools -- gedcomtools-mcp

Project scope writes a ``.mcp.json`` file at the project root. A minimal
shareable configuration looks like this:

.. code-block:: json

   {
     "mcpServers": {
       "gedcomtools": {
         "command": "gedcomtools-mcp",
         "args": [],
         "env": {}
       }
     }
   }

Claude Code prompts before using project-scoped MCP servers from ``.mcp.json``.
That approval is a client-side safety step; it does not change the
``gedcomtools-mcp`` server.

Claude Desktop And Other MCP Clients
------------------------------------

Most desktop MCP clients use the same ``mcpServers`` JSON shape:

.. code-block:: json

   {
     "mcpServers": {
       "gedcomtools": {
         "command": "gedcomtools-mcp",
         "args": [],
         "env": {}
       }
     }
   }

If the command is not on ``PATH``, replace ``gedcomtools-mcp`` with an absolute
path to the console script inside the environment where ``gedcomtools[mcp]`` is
installed.

Recommended Agent Workflow
--------------------------

Ask the agent to start with the built-in manual:

.. code-block:: text

   Call the gedcomtools MCP man() tool before choosing any other tool.

Then ask it to load or inspect a file:

.. code-block:: text

   Use load_gedcom("/absolute/path/to/family.ged"), then list the first 20
   individuals and show the parents, spouses, and children for @I1@.

Good agent prompts are explicit about:

* The absolute path to the GEDCOM, GEDCOM 7, or GEDCOM X JSON file.
* Whether the task is inspection, validation, conversion, or graph export.
* Whether output files may be overwritten when using export tools.
* How much data to return, such as list limits and ancestor/descendant depth.

Current Tool Surface
--------------------

The MCP server is currently read-oriented, with conversion and export tools.
It can inspect, summarize, validate, browse relationships, convert GEDCOM 5.x
to GEDCOM X JSON, and export graph JSONL files.

It does not currently expose write/edit tools such as setting sex, editing
records, deleting records, or merging two individual records into one survivor.
The project has CLI merge and repair functionality, but those operations are
not wrapped as MCP tools yet.

Safety Notes
------------

``gedcomtools-mcp`` works with local file paths available to the agent process.
Point it at files you are comfortable letting the agent read.

Conversion and export tools write only to the paths you pass in. Use a
scratch output directory for agent experiments, and leave ``overwrite`` false
unless replacing existing output is intentional.

For large trees, ask the agent to use limits first. For example, start with
``list_individuals(limit=20)`` and raise the limit only when needed.
