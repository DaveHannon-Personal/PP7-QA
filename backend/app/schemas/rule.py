from datetime import datetime
from pydantic import BaseModel


class Condition(BaseModel):
    field: str
    operator: str  # equals | not_equals | contains | not_contains | exists | not_exists | matches_regex
    value: str | int | float | bool | None = None


class FixAction(BaseModel):
    type: str  # set_field | trigger_look | assign_theme | noop
    field: str | None = None
    value: str | int | float | bool | None = None


class RuleCreate(BaseModel):
    name: str
    description: str | None = None
    target: str  # presentation | slide | look | theme | prop | macro | message
    severity: str = "error"
    condition: Condition
    fix_action: FixAction = FixAction(type="noop")


class RuleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    target: str | None = None
    severity: str | None = None
    condition: Condition | None = None
    fix_action: FixAction | None = None


class RuleRead(BaseModel):
    id: int
    name: str
    description: str | None
    target: str
    severity: str
    condition: dict
    fix_action: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
