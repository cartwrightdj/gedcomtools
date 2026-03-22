"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/zip.py
 Author:  David J. Cartwright
 Purpose: Read and write Gedcom-X ZIP file packages with manifest and resource entries

 Created: 2025-08-25
 Updated:

======================================================================
"""
import json
import os
import tempfile
import zipfile
from pathlib import Path

from .gedcomx import GedcomX
from .schemas import SCHEMA
from .serialization import Serialization

GX_MANIFEST_FILE_NAME = "META-INF/MANIFEST.MF"


class GedcomHeaderField:
    def __init__(self, key: str, value: str) -> None:
        self.key = key
        self.value = value


X_DC_CONFORMSTO_FIELD = GedcomHeaderField(
    key="X-DC-conformsTo",
    value="http://gedcomx.org/file/v1",
)


class GedcomResource:
    def __init__(
        self,
        path: str,
        headers: list[GedcomHeaderField] | None = None,
    ) -> None:
        # placeholder for future use
        self.path = path
        self.headers = headers or []


class GedcomManifest:
    def __init__(self) -> None:
        # placeholder for future use
        self.resources: list[GedcomResource] = []


class GedcomZip:
    def __init__(self, path: str | None = None) -> None:
        """
        Initialize a zipfile.

        If `path` is provided:
            - The path is resolved to an absolute path to prevent traversal attacks.
            - The parent directory is created only if it is a direct child of an
              existing directory (no recursive ``parents=True`` on untrusted input).
            - Raises ``ValueError`` for paths that contain ``..`` components.
            - Raises ``OSError`` if the directory cannot be created.
        If `path` is None:
            - Creates a zip in the system temp directory.

        Result:
            self.path  -> Path to the zip file
            self.zip   -> zipfile.ZipFile instance (write mode)
        """
        self.path: Path = self._resolve_zip_path(path)
        self.zip: zipfile.ZipFile = zipfile.ZipFile(  # pylint: disable=consider-using-with
            self.path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
        )

    # ────────────────────────────────────────────────
    # Internal helpers
    # ────────────────────────────────────────────────
    def _resolve_zip_path(self, path: str | None) -> Path:
        if path is None:
            return self._create_temp_zip_path()

        p = Path(path)

        # Reject any path containing ".." components before resolving
        if ".." in p.parts:
            raise ValueError(
                f"Path traversal detected in zip path: {path!r}. "
                "Use an absolute path or a path without '..' components."
            )

        # Resolve to absolute to catch symlink-based traversal
        p = p.resolve()

        # Create the immediate parent directory if it doesn't exist.
        # We intentionally do NOT use parents=True to avoid creating an
        # arbitrary directory tree from untrusted input.
        parent = p.parent
        if not parent.exists():
            parent.mkdir(exist_ok=True)

        return p

    def _create_temp_zip_path(self) -> Path:
        fd, temp_path = tempfile.mkstemp(suffix=".zip", prefix="gedcomx_")
        os.close(fd)  # We only want the path; ZipFile will reopen it
        return Path(temp_path)

    # ────────────────────────────────────────────────
    # Public API
    # ────────────────────────────────────────────────
    def add_object_as_resource(self, obj: object) -> str | None:
        """
        Serialize *obj* and store it as a JSON entry inside the zip.

        - If *obj* is a ``GedcomX`` instance it is written as ``tree.json``
          and the method returns immediately — no second serialization pass.
        - For any other registered top-level type, the entry is named after
          the object's ``id`` or class name.
        - Returns the internal archive name on success, or ``None`` if *obj*
          is not a recognised top-level type.
        """
        if isinstance(obj, GedcomX):
            arcname = "tree.json"
            self.zip.writestr(arcname, obj.json)
            return arcname

        if not SCHEMA.is_toplevel(obj.__class__):
            return None

        class_name = obj.__class__.__name__.lower() + "s"
        data = {class_name: Serialization.serialize(obj)}

        uri = getattr(obj, "_uri", None) or getattr(obj, "id", None) or class_name
        safe_uri = str(uri).replace("/", "_").replace("\\", "_")
        arcname = f"{safe_uri}.json"

        self.zip.writestr(arcname, json.dumps(data, ensure_ascii=False, indent=2))
        return arcname

    def close(self) -> None:
        """
        Close the underlying zip file if it's still open.
        Safe to call multiple times.
        """
        if getattr(self, "zip", None) is not None:
            if self.zip.fp is not None:
                self.zip.close()

    # ────────────────────────────────────────────────
    # Context manager support
    # ────────────────────────────────────────────────
    def __enter__(self) -> "GedcomZip":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
