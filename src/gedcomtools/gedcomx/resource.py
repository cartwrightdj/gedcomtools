from __future__ import annotations
from typing import Any, Optional

from pydantic import PrivateAttr, model_serializer

from ..glog import get_logger
from .gx_base import GedcomXModel
from .uri import URI

log = get_logger(__name__)


class Resource(GedcomXModel):
    """Tracks and resolves URIs / references between data stores."""

    resource: Optional[URI] = None
    resourceId: Optional[str] = None

    # Internal state — not serialized
    _resolved: bool = PrivateAttr(default=False)
    _remote: Optional[bool] = PrivateAttr(default=None)
    _target: Optional[Any] = PrivateAttr(default=None)

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_instance, check_nonempty
        if self.resource is None and not self.resourceId:
            result.warn("", "Resource has neither resource URI nor resourceId")
        check_instance(result, "resource", self.resource, URI)
        if self.resourceId is not None:
            check_nonempty(result, "resourceId", self.resourceId)

    @model_serializer
    def _serialize(self) -> dict:
        out: dict = {}
        if self.resource is not None:
            out["resource"] = str(self.resource)
        if self.resourceId is not None:
            out["resourceId"] = self.resourceId
        return out

    @property
    def uri(self) -> Optional[URI]:
        return self.resource

    @property
    def value(self) -> Optional[dict]:
        res: dict = {}
        if self.resource:
            res["resource"] = self.resource
        return res if res else None

    @classmethod
    def _of_object(cls, target: Any) -> "Resource":
        if isinstance(target, Resource):
            resource = target.resource
        elif isinstance(target, URI):
            resource = target
        elif isinstance(target, dict):
            # Already-serialized resource reference: {"resource": "..."} or {"resourceId": "..."}
            raw = target.get("resource") or target.get("resourceId")
            resource = URI(value=str(raw)) if raw else None
        else:
            log.debug("Target of type: {}", type(target))
            if hasattr(target, "_uri"):
                resource = target._uri
            elif hasattr(target, "id") and target.id:
                resource = URI(fragment=target.id)
            else:
                log.warning(
                    "Resource._of_object: target {} has no id/uri — returning empty resource",
                    type(target).__name__,
                )
                resource = None
        log.debug("Resource '{}'", resource)
        return Resource(resource=resource)

    def __repr__(self) -> str:
        return (
            f"Resource(resource={self.resource}, "
            f"resourceId={self.resourceId}, target={self._target})"
        )

    def __str__(self) -> str:
        parts = [f"resource={self.resource}"]
        if self.resourceId:
            parts.append(f"resourceId={self.resourceId}")
        if self._target:
            parts.append(f"target={self._target}")
        return ", ".join(parts)
