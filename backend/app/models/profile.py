"""
Profile (rule collection) ORM model.
A Profile is a named group of Rules that can be run together as a batch audit.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    rules = relationship("ProfileRule", back_populates="profile", cascade="all, delete-orphan")


class ProfileRule(Base):
    """Association table linking Profiles to Rules (ordered by position)."""

    __tablename__ = "profile_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    rule_id = Column(Integer, ForeignKey("rules.id", ondelete="CASCADE"), nullable=False)
    position = Column(Integer, nullable=False, default=0)

    profile = relationship("Profile", back_populates="rules")
    rule = relationship("Rule", back_populates="profiles")
