"""
DEPRECATED MODULE
-----------------
This module is kept only as a compatibility shim. Use `gateway_app:app` instead.

It re-exports the `app` from `gateway_app` so accidental usages of
`uvicorn app:app` keep working during the transition.
"""

from gateway_app import app  # noqa: F401  # re-export
