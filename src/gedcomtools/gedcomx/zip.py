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
            - Ensure directory exists or can be created
            - Use that path as the zip location
            - If any error occurs, fall back to a safe temp file
        If `path` is None:
            - Always create a zip in the system temp directory

        Result:
            self.path  -> Path to the zip file
            self.zip   -> zipfile.ZipFile instance (write mode)
        """
        self.path: Path = self._resolve_zip_path(path)
        self.zip: zipfile.ZipFile = zipfile.ZipFile(
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

        try:
            # Ensure directory exists
            if not p.parent.exists():
                p.parent.mkdir(parents=True, exist_ok=True)
            # ZipFile(..., "w") will create/truncate this path
            return p
        except Exception:
            # Fall back safely to temp
            return self._create_temp_zip_path()

    def _create_temp_zip_path(self) -> Path:
        fd, temp_path = tempfile.mkstemp(suffix=".zip", prefix="gedcomx_")
        os.close(fd)  # We only want the path; ZipFile will reopen it
        return Path(temp_path)

    # ────────────────────────────────────────────────
    # Public API
    # ────────────────────────────────────────────────
    def add_object_as_resource(self, obj: object) -> str | None:
        """
        If `obj` is a top-level schema object, serialize it and
        store it as JSON inside the zip.

        Returns the internal archive name (arcname) on success,
        or None if the object is not a top-level type.
        """
        if isinstance(obj,GedcomX):
            arcname = f"tree.json"
            
            self.zip.writestr(arcname, obj.json)

        if not hasattr(SCHEMA, "is_toplevel_obj"):
            # fallback: treat as top-level if its class name is registered as toplevel
            if not SCHEMA.is_toplevel(obj.__class__):
                return None
        else:
            if not SCHEMA.is_toplevel_obj(obj):
                return None

        class_name = obj.__class__.__name__.lower() + "s"
        data = {class_name: Serialization.serialize(obj)}

        # Prefer a URI-based filename, but sanitize it
        uri = getattr(obj, "_uri", None) or getattr(obj, "id", None) or class_name
        safe_uri = str(uri).replace("/", "_").replace("\\", "_")
        arcname = f"{safe_uri}.json"

        # Add resource to zip as JSON
        self.zip.writestr(arcname, json.dumps(data, ensure_ascii=False, indent=2))

        # Optional debug:
        print("ZIP path:", self.path)
        print("Wrote entry:", arcname)
        #print("Data:", data)

        return arcname

    def close(self) -> None:
        """
        Close the underlying zip file if it's still open.
        Safe to call multiple times.
        """
        if getattr(self, "zip", None) is not None:
            # zipfile.ZipFile uses .fp to track open/closed
            if self.zip.fp is not None:
                self.zip.close()

    # ────────────────────────────────────────────────
    # Context manager support
    # ────────────────────────────────────────────────
    def __enter__(self) -> "GedcomZip":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
