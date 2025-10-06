from __future__ import annotations

from datetime import date
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class ReportParameter(BaseModel):
    name: str
    type: Literal["date", "period", "select", "multi_select", "boolean"]
    required: bool
    options: list[str] | None = None
    default_value: Any | None = None


class ReportDefinition(BaseModel):
    id: str
    title: str
    description: str
    parameters: list[ReportParameter]
    formats: list[str]


class ReportDefinitionsResponse(BaseModel):
    reports: list[ReportDefinition]


class ReportFilters(BaseModel):
    animal_ids: list[UUID] | None = None
    buyer_ids: list[UUID] | None = None
    labels: list[str] | None = None
    breed_ids: list[UUID] | None = None
    lot_ids: list[UUID] | None = None
    status_ids: list[UUID] | None = None
    include_inactive: bool = False


class ReportRequest(BaseModel):
    date_from: date
    date_to: date
    period: Literal["daily", "weekly", "monthly"] = "daily"
    format: Literal["pdf", "json"] = "pdf"
    filters: ReportFilters | None = None


class ReportResponse(BaseModel):
    report_id: str
    title: str
    generated_at: str
    format: str
    content: str | None = None  # base64 for PDF, JSON for data
    data: dict[str, Any] | None = None  # structured data when format=json
    file_name: str | None = None
