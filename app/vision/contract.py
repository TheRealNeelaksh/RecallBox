from typing import List, Literal, Optional
from pydantic import BaseModel, field_validator

class VisionContract(BaseModel):
    activity: str
    setting: str
    social_context: str
    objects: List[str]
    people_count: str
    summary: str

    @field_validator("summary")
    def summary_must_be_non_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("summary must be non-empty")
        return v
