from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class Document(BaseModel):
    """Legacy demo metadata contract; persisted records use DocumentList."""
    id: str
    filename: str
    reference: str | None = None
    vendor: str | None = None
    type: Literal["Invoice", "Purchase order"]
    uploaded_at: datetime
    status: Literal["Pending", "Processed", "Needs review"]
    total: float | None = Field(default=None, ge=0)
    currency: str = "INR"
    issues: int = Field(default=0, ge=0)


class DocumentList(BaseModel):
    mode: Literal["persistent"] = "persistent"
    items: list[dict] = Field(default_factory=list)
    total: int = Field(default=0, ge=0)
    processing_available: bool = True
    message: str = "Local persisted analyses; fictional demo documents are excluded."


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "doculens-api"
    phase: int = 4
    processing_available: bool = False


class ExtractedField(BaseModel):
    value: str | None = None
    evidence: str | None = None
    method: str


class InvoiceLine(BaseModel):
    description: str
    quantity: str | None = None
    unit_rate: str | None = None
    line_total: str | None = None
    tax_amount: str | None = None
    tax_rate: str | None = None
    evidence: str


class ArithmeticCheck(BaseModel):
    name: str
    status: Literal["pass", "mismatch", "unknown"]
    calculated: str | None = None
    extracted: str | None = None
    explanation: str


class InvoiceValidation(BaseModel):
    tolerance: str
    checks: list[ArithmeticCheck]
    mismatches: int
    unknown: int
    passed: int


class GSTINCandidate(BaseModel):
    value: str
    party: Literal["supplier", "buyer", "unknown"]
    evidence: str
    method: str
    line: int


class InvoiceAnalysis(BaseModel):
    filename: str
    status: Literal["analyzed", "needs_ocr"]
    method: str
    pages: int
    fields: dict[str, ExtractedField]
    gstin_candidates: list[GSTINCandidate] = Field(default_factory=list)
    line_items: list[InvoiceLine]
    validation: InvoiceValidation
    warnings: list[str]
    text_excerpt: str
    ocr_used: bool = False
    ocr_pages: list[dict] = Field(default_factory=list)
    review_required: bool = True
    stored: bool = False
    document_id: str | None = None
    version: int | None = None
    review_status: str | None = None
    duplicate_candidates: list[dict] = Field(default_factory=list)


class ReviewRequest(BaseModel):
    version: int = Field(ge=1)
    fields: dict[str,str | None] = Field(default_factory=dict)
    notes: str = Field(min_length=5,max_length=2000)
    status: Literal["pending","approved","rejected"] = "pending"

class ReconcileRequest(BaseModel):
    expected_id: str
    observed_id: str

class ReportReviewRequest(BaseModel):
    version: int = Field(ge=1)
    decisions: dict[str,str]

