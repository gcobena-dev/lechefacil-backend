from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Request

from src.application.errors import PermissionDenied
from src.infrastructure.auth.context import AuthContext
from src.infrastructure.reports.pdf_generator import PDFGenerator
from src.infrastructure.reports.report_service import ReportService
from src.interfaces.http.deps import get_auth_context, get_uow
from src.interfaces.http.schemas.reports import (
    ReportDefinition,
    ReportDefinitionsResponse,
    ReportParameter,
    ReportRequest,
    ReportResponse,
)

router = APIRouter(prefix="/reports", tags=["reports"])

# Initialize report service
pdf_generator = PDFGenerator()
report_service = ReportService(pdf_generator)


@router.get("/definitions", response_model=ReportDefinitionsResponse)
async def get_report_definitions(
    context: AuthContext = Depends(get_auth_context),
) -> ReportDefinitionsResponse:
    """Get available report definitions"""

    reports = [
        ReportDefinition(
            id="production",
            title="Reporte de Producción",
            description="Análisis de producción diaria, semanal y mensual de leche",
            parameters=[
                ReportParameter(name="date_from", type="date", required=True),
                ReportParameter(name="date_to", type="date", required=True),
                ReportParameter(
                    name="period",
                    type="select",
                    required=False,
                    options=["daily", "weekly", "monthly"],
                    default_value="daily",
                ),
                ReportParameter(
                    name="format",
                    type="select",
                    required=False,
                    options=["pdf", "json"],
                    default_value="pdf",
                ),
                # Advanced filters
                ReportParameter(name="animal_ids", type="multi_select", required=False),
                ReportParameter(name="labels", type="multi_select", required=False),
                ReportParameter(name="breed_ids", type="multi_select", required=False),
                ReportParameter(name="lot_ids", type="multi_select", required=False),
                ReportParameter(name="status_ids", type="multi_select", required=False),
                ReportParameter(name="buyer_ids", type="multi_select", required=False),
                ReportParameter(
                    name="include_inactive", type="boolean", required=False, default_value=False
                ),
            ],
            formats=["pdf", "json"],
        ),
        ReportDefinition(
            id="financial",
            title="Reporte Financiero",
            description="Ingresos, gastos y rentabilidad por período",
            parameters=[
                ReportParameter(name="date_from", type="date", required=True),
                ReportParameter(name="date_to", type="date", required=True),
                ReportParameter(
                    name="period",
                    type="select",
                    required=False,
                    options=["daily", "weekly", "monthly"],
                    default_value="daily",
                ),
                ReportParameter(
                    name="format",
                    type="select",
                    required=False,
                    options=["pdf", "json"],
                    default_value="pdf",
                ),
                # Advanced filters
                ReportParameter(name="buyer_ids", type="multi_select", required=False),
                ReportParameter(name="animal_ids", type="multi_select", required=False),
                ReportParameter(name="labels", type="multi_select", required=False),
                ReportParameter(name="breed_ids", type="multi_select", required=False),
                ReportParameter(name="lot_ids", type="multi_select", required=False),
                ReportParameter(name="status_ids", type="multi_select", required=False),
                ReportParameter(
                    name="include_inactive", type="boolean", required=False, default_value=False
                ),
            ],
            formats=["pdf", "json"],
        ),
        ReportDefinition(
            id="animals",
            title="Reporte de Animales",
            description="Inventario, rendimiento y estadísticas del ganado",
            parameters=[
                ReportParameter(name="date_from", type="date", required=True),
                ReportParameter(name="date_to", type="date", required=True),
                ReportParameter(
                    name="format",
                    type="select",
                    required=False,
                    options=["pdf", "json"],
                    default_value="pdf",
                ),
                # Advanced filters
                ReportParameter(name="animal_ids", type="multi_select", required=False),
                ReportParameter(name="labels", type="multi_select", required=False),
                ReportParameter(name="breed_ids", type="multi_select", required=False),
                ReportParameter(name="lot_ids", type="multi_select", required=False),
                ReportParameter(name="status_ids", type="multi_select", required=False),
                ReportParameter(
                    name="include_inactive", type="boolean", required=False, default_value=False
                ),
            ],
            formats=["pdf", "json"],
        ),
        ReportDefinition(
            id="health",
            title="Reporte de Salud",
            description="Estado sanitario del ganado y tratamientos aplicados",
            parameters=[
                ReportParameter(name="date_from", type="date", required=True),
                ReportParameter(name="date_to", type="date", required=True),
                ReportParameter(
                    name="format",
                    type="select",
                    required=False,
                    options=["pdf", "json"],
                    default_value="pdf",
                ),
            ],
            formats=["pdf", "json"],
        ),
    ]

    return ReportDefinitionsResponse(reports=reports)


@router.post("/production", response_model=ReportResponse)
async def generate_production_report(
    payload: ReportRequest,
    request: Request,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> ReportResponse:
    """Generate production report"""
    if not context.role.can_read():
        raise PermissionDenied("Role not allowed to generate reports")

    # Validate date range
    if payload.date_from > payload.date_to:
        from src.application.errors import ValidationError

        raise ValidationError("date_from must be before or equal to date_to")

    # Validate date range is not too large (max 1 year)
    from datetime import timedelta

    if (payload.date_to - payload.date_from) > timedelta(days=365):
        from src.application.errors import ValidationError

        raise ValidationError("Date range cannot exceed 365 days")

    async with uow:
        storage_svc = getattr(getattr(request.app, "state", None), "storage_service", None)
        return await report_service.generate_production_report(
            context.tenant_id, payload, uow, storage_service=storage_svc
        )


@router.post("/financial", response_model=ReportResponse)
async def generate_financial_report(
    request: ReportRequest,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> ReportResponse:
    """Generate financial report"""
    if not context.role.can_read():
        raise PermissionDenied("Role not allowed to generate reports")

    # Validate date range
    if request.date_from > request.date_to:
        from src.application.errors import ValidationError

        raise ValidationError("date_from must be before or equal to date_to")

    from datetime import timedelta

    if (request.date_to - request.date_from) > timedelta(days=365):
        from src.application.errors import ValidationError

        raise ValidationError("Date range cannot exceed 365 days")

    async with uow:
        return await report_service.generate_financial_report(context.tenant_id, request, uow)


@router.post("/animals", response_model=ReportResponse)
async def generate_animals_report(
    request: ReportRequest,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> ReportResponse:
    """Generate animals report"""
    if not context.role.can_read():
        raise PermissionDenied("Role not allowed to generate reports")

    # Validate date range
    if request.date_from > request.date_to:
        from src.application.errors import ValidationError

        raise ValidationError("date_from must be before or equal to date_to")

    from datetime import timedelta

    if (request.date_to - request.date_from) > timedelta(days=365):
        from src.application.errors import ValidationError

        raise ValidationError("Date range cannot exceed 365 days")

    async with uow:
        return await report_service.generate_animals_report(context.tenant_id, request, uow)


@router.post("/health", response_model=ReportResponse)
async def generate_health_report(
    request: ReportRequest,
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> ReportResponse:
    """Generate health report (placeholder)"""
    if not context.role.can_read():
        raise PermissionDenied("Role not allowed to generate reports")

    # TODO: Implement health report when health system is ready
    return ReportResponse(
        report_id="health-placeholder",
        title="Reporte de Salud",
        generated_at=datetime.now(timezone.utc).isoformat(),
        format=request.format,
        content="Reporte de salud aún no implementado",
        file_name=f"salud_{request.date_from}_{request.date_to}.{request.format}",
    )


@router.post("/export-all", response_model=list[ReportResponse])
async def export_all_reports(
    date_from: date,
    date_to: date,
    request: Request,
    format: Literal["pdf", "json"] = "pdf",
    context: AuthContext = Depends(get_auth_context),
    uow=Depends(get_uow),
) -> list[ReportResponse]:
    """Export all reports"""
    if not context.role.can_read():
        raise PermissionDenied("Role not allowed to generate reports")

    report_request = ReportRequest(date_from=date_from, date_to=date_to, format=format)

    async with uow:
        storage_svc = getattr(getattr(request.app, "state", None), "storage_service", None)
        # Generate all reports concurrently
        tasks = [
            report_service.generate_production_report(
                context.tenant_id, report_request, uow, storage_service=storage_svc
            ),
            report_service.generate_financial_report(context.tenant_id, report_request, uow),
            report_service.generate_animals_report(context.tenant_id, report_request, uow),
        ]

        reports = await asyncio.gather(*tasks)

    return reports
