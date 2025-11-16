"""
DEPRECATED SCHEMA
-----------------
Compatibility re-exports. Use `audit_schema` instead.
"""

from audit_schema import AuditEvent, AuditIn  # re-export

__all__ = ["AuditIn", "AuditEvent"]
