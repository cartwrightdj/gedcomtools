"""
======================================================================
 Project: Gedcom-X
 File:    gx_base.py
 Purpose: Pydantic base class for all GedcomX models.

 Replaces the hand-rolled system in schemas.py / extensible.py:
   @extensible()     → inherit from GedcomXModel
   accept_extras()   → model_config extra='allow'
   SCHEMA registry   → pydantic model_fields (built-in)
   define_ext()      → GedcomXModel.define_ext() + model_rebuild()
   import_plugins()  → re-exported unchanged from extensible.py

 Created: 2026-03-19
======================================================================
"""
from __future__ import annotations

from typing import Any, ClassVar, Dict, Optional

from pydantic import BaseModel, ConfigDict


class GedcomXModel(BaseModel):
    """Drop-in base for all GedcomX pydantic models.

    Configuration summary
    ---------------------
    extra='allow'
        Absorbs unknown kwargs at construction time and stores them in
        ``model_extra``.  This replaces ``accept_extras()`` / ``ExtrasAwareMeta``.
    arbitrary_types_allowed=True
        Permits non-pydantic types (URI, IdentifierList, enum instances …)
        to appear in field type annotations.
    populate_by_name=True
        Fields can be set using their Python name *or* a declared alias.
    """

    model_config = ConfigDict(
        extra="allow",
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    # ------------------------------------------------------------------
    # Plugin / extension API  (replaces Extensible.define_ext)
    # ------------------------------------------------------------------

    @classmethod
    def define_ext(
        cls,
        name: str,
        *,
        typ: type | None = None,
        default: Any = None,
        overwrite: bool = False,
    ) -> None:
        """Declare a dynamic field on this class (plugin API).

        Replaces ``Extensible.define_ext()``.  Adds an annotation and calls
        ``model_rebuild()`` so pydantic picks up the new field.

        .. warning::
            Must be called **before** any instances of this class (or
            subclasses) are created.  If called after, existing instances
            will not gain the new field.

        Args:
            name:      Field name.
            typ:       Python type for schema registration.
            default:   Default value for new instances.
            overwrite: If *True*, replaces an existing field definition.
        """
        if name in cls.model_fields and not overwrite:
            return

        field_type: Any = (
            typ if typ is not None else (type(default) if default is not None else Any)
        )

        # Ensure this class has its *own* __annotations__ dict.
        if "__annotations__" not in vars(cls):
            cls.__annotations__ = dict(getattr(cls, "__annotations__", {}))

        cls.__annotations__[name] = Optional[field_type]

        if default is not None:
            setattr(cls, name, default)

        cls.model_rebuild(force=True)

    @classmethod
    def declared_extras(cls) -> Dict[str, Any]:
        """Fields added via :meth:`define_ext` (not inherited from GedcomXModel).

        Returns a mapping of field-name → FieldInfo for fields that were
        registered dynamically (i.e. not part of the core model).
        """
        base_fields = set(GedcomXModel.model_fields.keys())
        return {k: v for k, v in cls.model_fields.items() if k not in base_fields}
