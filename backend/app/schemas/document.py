"""Document schemas"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class DocumentMetadata(BaseModel):
    doc_id: str
    filename: str
    file_type: str
    upload_date: datetime
    status: str  # pending, processing, completed, failed
    tags: List[str] = []
    uploader_id: str
    size_bytes: int
    num_chunks: Optional[int] = None
    num_images: Optional[int] = None


class DocumentUploadResponse(BaseModel):
    doc_id: str
    filename: str
    status: str
    message: str


class DocumentListResponse(BaseModel):
    documents: List[DocumentMetadata]
    total: int


class DocumentStatusResponse(BaseModel):
    doc_id: str
    status: str
    progress: Optional[float] = None
    error_message: Optional[str] = None


