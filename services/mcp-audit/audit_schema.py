from typing import Any

from pydantic import BaseModel, Field


class AuditIn(BaseModel):
    event_type: str = Field(..., min_length=1, max_length=200)
    subject: str = Field(..., min_length=1, max_length=500)
    decision: bool
    details: dict[str, Any] = Field(default_factory=dict)


class AuditEvent(BaseModel):
    id: int
    event_type: str
    subject: str
    decision: bool
    details: dict[str, Any]
    prev_hash: str
    entry_hash: str
    created_at: str
