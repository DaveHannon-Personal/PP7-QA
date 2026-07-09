"""
QA Rule ORM model.

A Rule encodes a single compliance check:
  - target:     what PP7 object type this rule applies to
                (presentation | slide | look | theme | prop | macro | message)
  - condition:  JSON blob { field, operator, value }
                operators: equals | not_equals | contains | not_contains |
                           exists | not_exists | matches_regex
  - fix_action: JSON blob { type, field, value } — how to auto-correct the violation
                type: set_field | trigger_look | assign_theme | noop
  - severity:   "error" | "warning" | "info"
"""
import json
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Rule(Base):
    __tablename__ = "rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    target = Column(String(50), nullable=False)   # presentation | slide | look | …
    severity = Column(String(20), nullable=False, default="error")  # error|warning|info
    _condition = Column("condition", Text, nullable=False, default="{}")
    _fix_action = Column("fix_action", Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Many-to-many with Profile via association table
    profiles = relationship("ProfileRule", back_populates="rule", cascade="all, delete-orphan")

    @property
    def condition(self) -> dict:
        return json.loads(self._condition)

    @condition.setter
    def condition(self, value: dict) -> None:
        self._condition = json.dumps(value)

    @property
    def fix_action(self) -> dict:
        return json.loads(self._fix_action)

    @fix_action.setter
    def fix_action(self, value: dict) -> None:
        self._fix_action = json.dumps(value)
