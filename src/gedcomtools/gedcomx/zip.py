"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/zip.py
 Author:  David J. Cartwright
 Purpose: Read and write Gedcom-X ZIP file packages with manifest and resource entries

 Created: 2025-08-25
 Updated: 2026-03-27 — manifest writing, read() classmethod

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
GX_CONFORMSTO = "http://gedcomx.org/file/v1"
GX_CONTENT_TYPE = "application/x-gedcomx-v1+json"


class GedcomHeaderField:
    def __init__(self, key: str, value: str) -> None:
        self.key = key
        self.value = value


X_DC_CONFORMSTO_FIELD = GedcomHeaderField(
    key="X-DC-conformsTo",
    value=GX_CONFORMSTO,
)


class GedcomResource:
    def __init__(
        self,
        path: str,
        headers: list[GedcomHeaderField] | None = None,
    ) -> None:
        self.path = path
        self.headers = headers or []


class GedcomManifest:
    def __init__(self) -> None:
        self.resources: list[GedcomResource] = []

    def add(self, path: str, content_type: str = GX_CONTENT_TYPE) -> None:
        self.resources.append(GedcomResource(path, [
            GedcomHeaderField("Content-Type", content_type),
            GedcomHeaderField("X-DC-conformsTo", GX_CONFORMSTO),
        ]))

    def render(self) -> str:
        """Render as a MANIFEST.MF-style text block."""
        lines = [
            "Manifest-Version: 1.0",
            f"X-DC-conformsTo: {GX_CONFORMSTO}",
            "",
        ]
        for res in self.resources:
            lines.append(f"Name: {res.path}")
            for h in res.headers:
                lines.append(f"{h.key}: {h.value}")
            lines.append("")
        return "\n".join(lines)


class GedcomZip:
    def __init__(self, path: str | None = None) -> None:
        """
        Open a new GedcomX ZIP archive for writing.

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
        self._manifest = GedcomManifest()

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
    # Public API — write
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
            self._manifest.add(arcname)
            return arcname

        if not SCHEMA.is_toplevel(obj.__class__):
            return None

        class_name = obj.__class__.__name__.lower() + "s"
        data = {class_name: Serialization.serialize(obj)}

        uri = getattr(obj, "_uri", None) or getattr(obj, "id", None) or class_name
        safe_uri = str(uri).replace("/", "_").replace("\\", "_")
        arcname = f"{safe_uri}.json"

        self.zip.writestr(arcname, json.dumps(data, ensure_ascii=False, indent=2))
        self._manifest.add(arcname)
        return arcname

    def write_manifest(self) -> None:
        """Write ``META-INF/MANIFEST.MF`` based on all added resources."""
        self.zip.writestr(GX_MANIFEST_FILE_NAME, self._manifest.render())

    def close(self) -> None:
        """Write the manifest and close the zip.  Safe to call multiple times."""
        if getattr(self, "zip", None) is not None:
            if self.zip.fp is not None:
                self.write_manifest()
                self.zip.close()

    # ────────────────────────────────────────────────
    # Public API — read
    # ────────────────────────────────────────────────
    @classmethod
    def read(cls, path: str | Path) -> GedcomX:
        """
        Read a GedcomX ZIP archive and return a merged ``GedcomX`` instance.

        Looks for all ``.json`` entries (excluding the manifest), deserializes
        each one, and merges them into a single ``GedcomX`` object.  The primary
        entry ``tree.json`` is processed first.

        Raises:
            FileNotFoundError: If *path* does not exist.
            ValueError:        If no GedcomX JSON entries are found in the archive.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(p)

        merged = GedcomX()

        with zipfile.ZipFile(p, "r") as zf:
            names = zf.namelist()

            # Process tree.json first, then all other .json entries
            ordered = (
                [n for n in names if n == "tree.json"]
                + sorted(n for n in names if n.endswith(".json") and n != "tree.json"
                         and not n.startswith("META-INF/"))
            )

            if not ordered:
                raise ValueError(f"No GedcomX JSON entries found in {p}")

            for entry_name in ordered:
                data = json.loads(zf.read(entry_name))
                gx = GedcomX.from_dict(data)
                merged.extend(gx)

        return merged

    @classmethod
    def list_entries(cls, path: str | Path) -> list[dict]:
        """
        Return a list of entry info dicts from a GedcomX ZIP archive.

        Each dict has ``name``, ``size``, ``compress_size``.
        Manifest entries are included.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(p)
        with zipfile.ZipFile(p, "r") as zf:
            return [
                {"name": i.filename, "size": i.file_size, "compress_size": i.compress_size}
                for i in zf.infolist()
            ]

    # ────────────────────────────────────────────────
    # Context manager support
    # ────────────────────────────────────────────────
    def __enter__(self) -> "GedcomZip":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
