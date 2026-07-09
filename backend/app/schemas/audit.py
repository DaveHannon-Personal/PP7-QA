from typing import Literal
from pydantic import BaseModel


class RuleConflict(BaseModel):
    conflict_type: str        # "duplicate" | "contradiction"
    rule_a_id: int
    rule_a_name: str
    rule_b_id: int
    rule_b_name: str
    target: str
    field: str
    description: str          # human-readable explanation


class AuditResultItem(BaseModel):
    item_id: str          # UUID or identifier from PP7
    item_name: str        # Human-readable name
    item_type: str        # presentation | slide | look | theme | …
    rule_id: int
    rule_name: str
    status: Literal["pass", "fail", "skipped"]
    details: str          # Human-readable explanation
    fix_available: bool   # Whether the fix_action can auto-correct this


class AuditReport(BaseModel):
    profile_id: int | None
    profile_name: str | None
    total_items_checked: int
    pass_count: int
    fail_count: int
    skip_count: int
    results: list[AuditResultItem]
    conflicts: list[RuleConflict] = []   # conflicts detected among the rules used


class AuditRunRequest(BaseModel):
    profile_id: int | None = None   # Run a specific profile
    rule_ids: list[int] | None = None  # Or a one-off list of rules


class FixRequest(BaseModel):
    result_ids: list[str]  # item_id values to fix ("all" = fix everything that failed)


class FixResponse(BaseModel):
    fixed_count: int
    failed_count: int
    details: list[dict]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    stream: bool = True
