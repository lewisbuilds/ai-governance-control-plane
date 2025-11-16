from typing import Any

from pydantic import BaseModel, Field


class LineageIn(BaseModel):
    model_id: str = Field(..., min_length=1, max_length=200)
    version: str = Field(..., min_length=1, max_length=100)
    artifacts: list[str] = Field(default_factory=list)
    created_by: str = Field(..., min_length=1, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)
    aibom: dict[str, Any] | None = None


class LineageRecord(LineageIn):
    id: int
    created_at: str
