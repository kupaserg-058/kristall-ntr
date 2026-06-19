import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.models import (
    Confidence,
    DocStatus,
    DocType,
    VerificationStatus,
)


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    original_name: str
    doc_type: DocType
    gemini_file_uri: str | None
    status: DocStatus
    error_message: str | None
    uploaded_at: datetime
    directions_count: int = 0


class DirectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    title: str
    federal_match: str | None
    fragment: str
    confidence: Confidence
    verification_status: VerificationStatus
    created_at: datetime
    document_name: str | None = None


class AnalyzeResponse(BaseModel):
    status: str = "analyzing"


class StatusUpdate(BaseModel):
    status: VerificationStatus


class FederalDirectionStat(BaseModel):
    name: str
    count: int


class StatsOut(BaseModel):
    total_documents: int
    total_directions: int
    confirmed: int
    pending: int
    by_federal_direction: list[FederalDirectionStat]
