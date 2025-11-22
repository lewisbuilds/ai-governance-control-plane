"""
Vulture whitelist
-----------------

This file marks dynamic usages that Vulture can't detect statically
as "used" (e.g., FastAPI routes registered via decorators).

Guidelines:
- Keep this list minimal and focused on genuine false positives.
- Prefer fixing code (rename, remove) over whitelisting when possible.
- When adding items, include a brief comment explaining why.
"""

# FastAPI apps are referenced dynamically by uvicorn and decorators.
try:
    from services.mcp_audit import audit_app as _aud
    from services.mcp_gateway import gateway_app as _gw
    from services.mcp_lineage import lineage_app as _lin
    from services.mcp_policy import policy_app as _pol

    # Touch app objects so Vulture sees them as used.
    _ = (_gw.app, _pol.app, _aud.app, _lin.app)
except Exception:
    # Whitelist should never break imports; ignore if structure changes.
    pass

# Common FastAPI route handlers may be flagged as unused because
# they are invoked by the framework. If Vulture flags specific handlers,
# import and reference them here explicitly, e.g.:
#
# from services.mcp_policy.policy_app import validate
# _ = validate
#
# Repeat sparingly and remove when no longer needed.
