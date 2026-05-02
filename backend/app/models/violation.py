import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID

from backend.app.core.database import Base


class ViolationType(str, PyEnum):
    HELMET_VIOLATION = "helmet_violation"
    SIGNAL_JUMP = "signal_jump"
    WRONG_WAY = "wrong_way"
    SPEEDING = "speeding"
    NO_SEATBELT = "no_seatbelt"
    ILLEGAL_PARKING = "illegal_parking"


class ViolationStatus(str, PyEnum):
    DETECTED = "detected"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    EVIDENCE_GENERATED = "evidence_generated"
    SENT_TO_AUTHORITY = "sent_to_authority"


class Violation(Base):
    __tablename__ = "violations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    camera_id = Column(String(100), nullable=False, index=True)
    violation_type = Column(Enum(ViolationType), nullable=False, index=True)
    status = Column(Enum(ViolationStatus), default=ViolationStatus.DETECTED, index=True)
    license_plate = Column(String(20), index=True)
    confidence = Column(Float, nullable=False)
    clip_url = Column(Text)
    thumbnail_url = Column(Text)
    evidence_package_url = Column(Text)
    location = Column(String(255))
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(Text)


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    stream_url = Column(Text, nullable=False)
    location = Column(String(255))
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
