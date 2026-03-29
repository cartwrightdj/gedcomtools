"""
Compatibility package for the legacy ``gedcomtools.gedcomx.extensions.test`` path.

The implementation now lives under ``ae_arango``; this module re-exports the
same symbols so existing plugin configuration and tests continue to work.
"""

from ..ae_arango import TestClass, ext_description_get

__all__ = ["TestClass", "ext_description_get"]
