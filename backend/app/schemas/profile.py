from datetime import datetime
from pydantic import BaseModel
from app.schemas.rule import RuleRead


class ProfileCreate(BaseModel):
    name: str
    description: str | None = None
    rule_ids: list[int] = []


class ProfileUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    rule_ids: list[int] | None = None  # full replacement of rule list


class ProfileRead(BaseModel):
    id: int
    name: str
    description: str | None
    rules: list[RuleRead]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProfileSummary(BaseModel):
    id: int
    name: str
    description: str | None
    rule_count: int
    created_at: datetime

    model_config = {"from_attributes": True}
