GedcomX
=======


1. Top Level Types
=======================

Person
--------------------------------

.. automodule:: gedcomx.Person
   :members:
   :show-inheritance: True
   :undoc-members: 

.. code-block:: python
   :linenos:
   :caption: Calling `Create a Person class with QuickPerson`

   from gedcomx import QuickPerson

   # Create a Person class with QuickPerson
   mother = QuickPerson('My Mothers Name',dob='1/5/1939')
   



Relationship
--------------------------------
.. automodule:: gedcomx.Relationship
   :members:
   :show-inheritance:
   :undoc-members:

SourceDescription
-----------------
.. automodule:: gedcomx.SourceDescription
   :members:
   :show-inheritance:
   :undoc-members:

Agent
-----------------
.. automodule:: gedcomx.agent
   :members:
   :show-inheritance:
   :undoc-members:

Event
-----------------
.. automodule:: gedcomx.Event
   :members:
   :show-inheritance:
   :undoc-members:

Document
-----------------
.. automodule:: gedcomx.document
   :members:
   :show-inheritance:
   :undoc-members:

PlaceDescription
----------------- 
.. automodule:: gedcomx.PlaceDescription
   :members:
   :show-inheritance:
   :undoc-members:



This example shows basic usage:

.. code-block:: python
   :linenos:
   :caption: Calling `my_function`

   from gedcomx import GedcomX, Attribution, Agent

   # get the answer
   answer = my_function(42, key="value")
   print(f"Answer is {answer}")

 
