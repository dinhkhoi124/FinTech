"""Local, non-autonomous safe-degraded PayResolve service."""

from .app import create_app

__all__ = ["create_app"]
