import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class DocType(str, enum.Enum):
    federal = "federal"
    regional = "regional"


class DocStatus(str, enum.Enum):
    uploaded = "uploaded"
    analyzing = "analyzing"
    done = "done"
    error = "error"


class Confidence(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"


class VerificationStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    needs_clarification = "needs_clarification"
    rejected = "rejected"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    original_name: Mapped[str] = mapped_column(String(512), nullable=False)
    doc_type: Mapped[DocType] = mapped_column(
        SAEnum(DocType, name="doc_type"), nullable=False
    )
    gemini_file_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[DocStatus] = mapped_column(
        SAEnum(DocStatus, name="doc_status"),
        nullable=False,
        default=DocStatus.uploaded,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    directions: Mapped[list["Direction"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Direction(Base):
    __tablename__ = "directions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    federal_match: Mapped[str | None] = mapped_column(String(512), nullable=True)
    fragment: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    confidence: Mapped[Confidence] = mapped_column(
        SAEnum(Confidence, name="confidence"),
        nullable=False,
        default=Confidence.medium,
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        SAEnum(VerificationStatus, name="verification_status"),
        nullable=False,
        default=VerificationStatus.pending,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped["Document"] = relationship(back_populates="directions")
