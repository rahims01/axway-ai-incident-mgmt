from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.database import Base


# ── Enums ──────────────────────────────────────────────────────────────────

class Severity(str, Enum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class IncidentStatus(str, Enum):
    NEW = "NEW"
    ANALYZING = "ANALYZING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    REMEDIATING = "REMEDIATING"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


class Category(str, Enum):
    SFTP_KEY = "SFTP_KEY"
    SFTP_AUTH = "SFTP_AUTH"
    TLS_CERT = "TLS_CERT"
    TLS_HANDSHAKE = "TLS_HANDSHAKE"
    AS2_MDN = "AS2_MDN"
    AS2_ENCRYPT = "AS2_ENCRYPT"
    NETWORK = "NETWORK"
    JVM = "JVM"
    DISK = "DISK"
    QUEUE = "QUEUE"
    PARTNER_SILENCE = "PARTNER_SILENCE"
    COMPLIANCE = "COMPLIANCE"
    UNKNOWN = "UNKNOWN"


# ── ORM Model ──────────────────────────────────────────────────────────────

class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_number: Mapped[str] = mapped_column(String(30), unique=True)
    category: Mapped[str] = mapped_column(String(30))
    severity: Mapped[str] = mapped_column(String(4))
    status: Mapped[str] = mapped_column(String(25), default=IncidentStatus.NEW)

    partner_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    partner_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    protocol: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)

    root_cause: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[int]] = mapped_column(nullable=True)
    fix_steps: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    auto_fixable: Mapped[Optional[bool]] = mapped_column(nullable=True)
    auto_fix_action: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    source_check: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    fingerprint: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


# ── Pydantic Schemas ───────────────────────────────────────────────────────

class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    incident_number: str
    category: str
    severity: str
    status: str
    partner_id: Optional[str]
    partner_name: Optional[str]
    protocol: Optional[str]
    title: str
    description: str
    root_cause: Optional[str]
    confidence: Optional[int]
    fix_steps: Optional[list]
    auto_fixable: Optional[bool]
    auto_fix_action: Optional[str]
    resolution_notes: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]
    source_check: Optional[str]


class IncidentUpdate(BaseModel):
    status: Optional[str] = None
    resolution_notes: Optional[str] = None
