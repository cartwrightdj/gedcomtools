================================
Extensibility & Extension System
================================

This guide shows how to extend **Gedcom-X** without forking the core library:
add new fields, attach methods, and load third-party extensions at import time.

.. contents::
   :local:
   :depth: 2


Quick Start
===========

1) Decorate your core classes so they self-register in the schema and accept
   registered “extra” fields at construction time.

.. code-block:: python

   from gedcomx.schemas import extensible  # combo of schema_class + accept_extras

   @extensible(toplevel=True)
   class Conclusion:
       def __init__(self, id: str | None = None, lang: str = "en"):
           self.id = id
           self.lang = lang

2) Create a extension module that registers an extra field (e.g., ``links``) and
   optional methods. extensions run at import time—no extra calls required.

.. code-block:: python

   # gedcomx_extensions/conclusion_links.py
   from gedcomx.schemas import SCHEMA

   # Add a new field to the base. It will propagate to subclasses automatically.
   SCHEMA.register_extra("Conclusion", "links", list[str])

3) Import extensions from a folder, a package, or an env var:

.. code-block:: python

   from gedcomx.extension_loader import import_extensions
   import_extensions(
       base_package="gedcomx",
       subpackage="extensions",     # import gedcomx.extensions.*
       local_dir="./extensions",       # import top-level .py or packages in ./extensions
       env_var="GEDCOMX_EXTENSIONS",   # extra module names or paths
       recursive=False,
   )

4) Done. New fields are now accepted by subclass constructors:

.. code-block:: python

   p = Person(links=["http://example.org/res/1"])  # no TypeError


What You Get
============

- **Schema registration**: Class fields recorded in a central registry.
- **Extras** (new fields) can be registered later and **inherit** down the class tree.
- **Safe constructors**: Unknown but **registered** keys are accepted and attached.
- **extensions**: Self-registering modules discovered by package/dir/env.


Core Concepts
=============

Schema Registration
-------------------

``schema_class`` inspects annotations (or ``__init__``) and registers fields in
``SCHEMA.field_type_table``. The convenience decorator ``extensible`` applies
``schema_class`` and then wraps the class so registered extras are accepted at
construction.

.. code-block:: python

   from gedcomx.schemas import extensible

   @extensible(toplevel=True)
   class Person(Conclusion):
       def __init__(self, id: str | None = None, names: list[str] | None = None):
           super().__init__(id=id)
           self.names = names or []

Registering Extras (New Fields)
-------------------------------

Use the central schema to add a field to a base class. It automatically
propagates to existing and future subclasses.

.. code-block:: python

   from gedcomx.schemas import SCHEMA

   # Add "links: list[str]" to Conclusion and all its subclasses
   SCHEMA.register_extra("Conclusion", "links", list[str])

Construction then accepts the field:

.. code-block:: python

   p = Person(links=["/u/1", "/u/2"])  # accepted and attached to the instance


Allow List (Safety)
-------------------

Only keys that appear in the schema (direct + inherited extras) are admitted.
``extensible`` configures this for you. If you roll your own:

.. code-block:: python

   from gedcomx.schemas import accept_extras, SCHEMA, schema_class

   @accept_extras(allow_only=lambda cls: set(SCHEMA.get_all_extras(cls).keys()))
   @schema_class()
   class Conclusion: ...
   

Adding Methods from Extensions (Optional)
-----------------------------------------

You can attach methods/properties at import time (if you included the optional
method decorators in your build). Example pattern:

.. code-block:: python

   # gedcomx_extensions/person_methods.py
   from gedcomx.schemas import schema_method
   from gedcomx.models import Person

   @schema_method(Person)
   def full_name(self) -> str:
       return " ".join(getattr(self, "names", [])[:1] or ["<unnamed>"])


Extension Discovery
===================

You can import extensions from three sources via ``extension_loader.import_extensions``:

- ``gedcomx.extensions`` subpackage
- ``./extensions`` filesystem directory
- ``GEDCOMX_EXTENSIONS`` env var (module names or paths)

.. code-block:: python

   from gedcomx.extension_loader import import_extensions

   result = import_extensions(
       "gedcomx",
       subpackage="extensions",
       local_dir="./extensions",
       env_var="GEDCOMX_EXTENSIONS",
       recursive=False,
   )
   print("Imported:", result["imported"])
   if result["errors"]:
       for name, err in result["errors"].items():
           print(f"[extension error] {name}: {err!r}")

**Env var format** (examples)::

   # Windows (uses ';')
   set GEDCOMX_EXTENSIONS=gedcomx_extra.nameparts;C:\myextensions\custom.py

   # Unix (uses ':')
   export GEDCOMX_EXTENSIONS="gedcomx_extra.nameparts:/srv/extensions/custom.py"


Entry Points (for third-party wheels)
-------------------------------------

If you distribute extensions as separate wheels, add an entry point group so your
host can discover them with standard tools (optional if you rely on the loader).

.. code-block:: toml

   # pyproject.toml of the extension package
   [project.entry-points."gedcomx.extensions"]
   nameparts = "gedcomx_nameparts"   # module imported at runtime


Design Notes
============

- **Inheritance of extras**: When you call ``SCHEMA.register_extra("Base", ...)``,
  the field is recorded on ``Base`` and pushed to all known subclasses. When a
  new subclass registers later, it inherits the extras from its bases.
- **Constructor safety**: The class wrapper (installed by ``extensible``) splits
  constructor kwargs into known vs extra; it passes only known kwargs to the
  original ``__init__`` and then attaches allowed extras. This prevents
  ``TypeError: __init__ got an unexpected keyword`` while avoiding silent typos.
- **Type checking**: Dynamically added attributes won’t be visible to static
  type checkers. Provide ``.pyi`` stubs or ``Protocol`` if you need editor hints.


Troubleshooting
===============

**“TypeError: Person.__init__() got an unexpected keyword argument 'links'”**

- Ensure the class is decorated correctly and in the right order:

  .. code-block:: python

     @extensible(toplevel=True)   # outermost
     class Person(Conclusion):    # your base is also @extensible or @schema_class
         ...

- Confirm the extra is registered on a base in Person’s MRO:

  .. code-block:: python

     SCHEMA.register_extra("Conclusion", "links", list[str])

- Verify that the extension actually imported (print ``result["imported"]``).

**Dataclasses**

If a subclass is a dataclass, decorator order must be:

.. code-block:: python

   from dataclasses import dataclass

   @extensible()
   @dataclass
   class SomeSubclass(Conclusion):
       ...

(``dataclass`` innermost, so the generated ``__init__`` is what gets wrapped.)

**Absolute vs relative imports**

Pass absolute module names to the loader, or when using relative names provide
the correct base package. The shipped loader resolves this for you.


Appendix: Minimal APIs
======================

Register a class
----------------

.. code-block:: python

   @schema_class(toplevel=True)
   class Document: ...

Register an extra field
-----------------------

.. code-block:: python

   SCHEMA.register_extra("Document", "doi", str)

Get schema as JSON
------------------

.. code-block:: python

   SCHEMA.json  # { "Document": {"doi": "str", ...}, ... }

