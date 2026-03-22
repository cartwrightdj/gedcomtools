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
from pydantic.fields import FieldInfo

from .validation import ValidationResult


def _rebuild_subclasses(cls: type, name: str, fi: "FieldInfo") -> None:
    """Recursively propagate a FieldInfo to subclasses and rebuild their schemas.

    Pydantic v2 ``model_rebuild()`` only rebuilds the called class.  When a
    field is added to a base class we must push the FieldInfo (with its
    default) into every subclass's ``__pydantic_fields__`` and then rebuild,
    otherwise pydantic infers the field as required from the bare annotation.
    """
    for sub in cls.__subclasses__():
        if not hasattr(sub, "model_rebuild"):
            continue
        # Copy __pydantic_fields__ so we don't mutate the parent's dict.
        if "__pydantic_fields__" not in vars(sub):
            sub.__pydantic_fields__ = dict(getattr(sub, "__pydantic_fields__", {}))
        sub.__pydantic_fields__.setdefault(name, fi)
        sub.model_rebuild(force=True)
        _rebuild_subclasses(sub, name, fi)


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

    # Tracks field names registered via define_ext() per class.
    # Each class gets its own set (never mutate the parent's).
    _ext_field_names: ClassVar[set] = set()

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
        annotated_type = Optional[field_type]

        # Ensure this class has its *own* __annotations__ dict.
        if "__annotations__" not in vars(cls):
            cls.__annotations__ = dict(getattr(cls, "__annotations__", {}))
        cls.__annotations__[name] = annotated_type

        # Ensure this class has its own __pydantic_fields__ dict so we don't
        # mutate a parent's dict, then add the FieldInfo entry directly.
        # model_rebuild() alone does NOT pick up annotations added post-hoc in
        # pydantic v2 — __pydantic_fields__ must be updated explicitly.
        if "__pydantic_fields__" not in vars(cls):
            cls.__pydantic_fields__ = dict(getattr(cls, "__pydantic_fields__", {}))
        cls.__pydantic_fields__[name] = FieldInfo(annotation=annotated_type, default=default)

        # Record the field name in this class's own _ext_field_names set.
        if "_ext_field_names" not in vars(cls):
            cls._ext_field_names = set()
        cls._ext_field_names.add(name)

        cls.model_rebuild(force=True)
        # Pydantic only rebuilds the called class; subclasses keep their old
        # cached schema.  Push the FieldInfo into each subclass and rebuild.
        _rebuild_subclasses(cls, name, cls.__pydantic_fields__[name])

    @classmethod
    def declared_extras(cls) -> Dict[str, Any]:
        """Fields added via :meth:`define_ext` (not built into the original model).

        Returns a mapping of field-name → FieldInfo for fields that were
        registered dynamically via ``define_ext()``.
        """
        # Collect all names registered via define_ext() across the MRO.
        ext_names: set = set()
        for klass in cls.__mro__:
            if klass is object:
                break
            if "_ext_field_names" in vars(klass):
                ext_names.update(vars(klass)["_ext_field_names"])
        return {k: v for k, v in cls.model_fields.items() if k in ext_names}

    # ------------------------------------------------------------------
    # Validation API
    # ------------------------------------------------------------------

    def validate(self, _visited: Optional[set] = None) -> ValidationResult:  # pylint: disable=arguments-renamed
        """Recursively validate this model and all nested GedcomXModel children.

        Returns a :class:`ValidationResult` containing errors and warnings.
        Errors mean spec violations; warnings are completeness/quality hints.

        Subclasses add type-specific checks by overriding :meth:`_validate_self`.
        """
        if _visited is None:
            _visited = set()
        oid = id(self)
        if oid in _visited:
            return ValidationResult()
        _visited.add(oid)

        result = ValidationResult()
        self._validate_self(result)
        for fname in type(self).model_fields:
            fval = getattr(self, fname, None)
            if fval is None:
                continue
            if isinstance(fval, GedcomXModel):
                result.merge(fval.validate(_visited), prefix=fname)
            elif isinstance(fval, list):
                for i, item in enumerate(fval):
                    if isinstance(item, GedcomXModel):
                        result.merge(item.validate(_visited), prefix=f"{fname}[{i}]")
        return result

    def _validate_self(self, result: ValidationResult) -> None:
        """Override in subclasses to add model-specific validation checks.

        Add issues via ``result.error(path, message)`` or
        ``result.warn(path, message)``.  *path* should be the field name
        or dotted sub-path relative to this model (e.g. ``"type"`` or
        ``"nameForms[0].fullText"``).
        """
