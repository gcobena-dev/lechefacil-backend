from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from src.application.interfaces.unit_of_work import UnitOfWork
from src.infrastructure.reports.pdf_generator import PDFGenerator
from src.interfaces.http.schemas.reports import ReportRequest, ReportResponse


class ReportService:
    def __init__(self, pdf_generator: PDFGenerator):
        self.pdf_generator = pdf_generator

    async def generate_production_report(
        self, tenant_id: UUID, request: ReportRequest, uow: UnitOfWork
    ) -> ReportResponse:
        """Generate production report"""
        report_id = str(uuid.uuid4())

        # Get production data - if specific animals requested, process multiple queries
        if request.filters and request.filters.animal_ids:
            all_productions = []
            for animal_id in request.filters.animal_ids:
                animal_productions = await uow.milk_productions.list(
                    tenant_id,
                    date_from=request.date_from,
                    date_to=request.date_to,
                    animal_id=animal_id,
                )
                all_productions.extend(animal_productions)
            productions = all_productions
        else:
            # Get all productions
            productions = await uow.milk_productions.list(
                tenant_id, date_from=request.date_from, date_to=request.date_to, animal_id=None
            )

        # Get delivery data for the same period
        try:
            deliveries = await uow.milk_deliveries.list(
                tenant_id, date_from=request.date_from, date_to=request.date_to, buyer_id=None
            )
        except Exception:
            # If deliveries not available, use empty list
            deliveries = []

        # Calculate KPIs
        total_liters_produced = sum(p.volume_l for p in productions)
        total_liters_delivered = sum(d.volume_l for d in deliveries)
        total_records = len(productions)
        avg_per_record = (
            total_liters_produced / total_records if total_records > 0 else Decimal("0")
        )

        # Calculate difference (milk retained/lost)
        retention_difference = total_liters_produced - total_liters_delivered
        retention_percentage = (
            (total_liters_delivered / total_liters_produced * 100)
            if total_liters_produced > 0
            else Decimal("0")
        )

        # Group by period
        period_production_data = self._group_by_period(productions, request.period)
        period_delivery_data = self._group_deliveries_by_period(deliveries, request.period)

        # Get animals data for top producers
        animals = await uow.animals.list(tenant_id)
        animals_dict = {a.id: a for a in animals}

        # Calculate top producers
        animal_totals = {}
        for prod in productions:
            if prod.animal_id:
                if prod.animal_id not in animal_totals:
                    animal_totals[prod.animal_id] = Decimal("0")
                animal_totals[prod.animal_id] += prod.volume_l

        top_producers = []
        for animal_id, total_liters in sorted(
            animal_totals.items(), key=lambda x: x[1], reverse=True
        )[:10]:
            animal = animals_dict.get(animal_id)
            if animal:
                top_producers.append(
                    {
                        "animal_name": animal.name,
                        "animal_tag": animal.tag,
                        "total_liters": total_liters,
                        "avg_per_day": total_liters
                        / ((request.date_to - request.date_from).days + 1),
                    }
                )

        if request.format == "json":
            data = {
                "summary": {
                    "total_liters_produced": float(total_liters_produced),
                    "total_liters_delivered": float(total_liters_delivered),
                    "retention_difference": float(retention_difference),
                    "retention_percentage": float(retention_percentage),
                    "total_records": total_records,
                    "avg_per_record": float(avg_per_record),
                    "period_from": request.date_from.isoformat(),
                    "period_to": request.date_to.isoformat(),
                },
                "period_production_data": {k: float(v) for k, v in period_production_data.items()},
                "period_delivery_data": {k: float(v) for k, v in period_delivery_data.items()},
                "top_producers": [
                    {
                        "animal_name": tp["animal_name"],
                        "animal_tag": tp["animal_tag"],
                        "total_liters": float(tp["total_liters"]),
                        "avg_per_day": float(tp["avg_per_day"]),
                    }
                    for tp in top_producers
                ],
            }

            return ReportResponse(
                report_id=report_id,
                title="Reporte de Producción",
                generated_at=datetime.now(timezone.utc).isoformat(),
                format="json",
                data=data,
                file_name=f"produccion_{request.date_from}_{request.date_to}.json",
            )

        # Generate PDF
        elements = []

        # Header
        title = "Reporte de Producción de Leche"
        subtitle = f"Período: {request.date_from.strftime('%d/%m/%Y')} - "
        f"{request.date_to.strftime('%d/%m/%Y')}"
        elements.extend(self.pdf_generator.create_header(title, subtitle))

        # KPIs section
        kpis = {
            "total_liters_produced": total_liters_produced,
            "total_liters_delivered": total_liters_delivered,
            "retention_difference": retention_difference,
            "retention_percentage": f"{retention_percentage:.1f}%",
            "total_records": total_records,
            "avg_per_record": avg_per_record,
            "period_days": (request.date_to - request.date_from).days + 1,
        }
        elements.extend(self.pdf_generator.create_kpi_section("Resumen Ejecutivo", kpis))

        # Production chart
        if period_production_data:
            elements.extend(
                self.pdf_generator.create_chart_section(
                    f"Producción por {request.period.title()}",
                    {k: float(v) for k, v in period_production_data.items()},
                    "bar",
                )
            )

        # Delivery chart
        if period_delivery_data:
            elements.extend(
                self.pdf_generator.create_chart_section(
                    f"Entregas por {request.period.title()}",
                    {k: float(v) for k, v in period_delivery_data.items()},
                    "bar",
                )
            )

        # Top producers table
        if top_producers:
            columns = ["Animal", "Etiqueta", "Total Litros", "Promedio/Día"]
            table_data = []
            for producer in top_producers:
                table_data.append(
                    {
                        "animal": producer["animal_name"],
                        "etiqueta": producer["animal_tag"],
                        "total_litros": producer["total_liters"],
                        "promedio/día": producer["avg_per_day"],
                    }
                )

            elements.extend(
                self.pdf_generator.create_table_section(
                    "Top 10 Animales Productores", table_data, columns
                )
            )

        pdf_content = self.pdf_generator.generate_pdf(elements)

        return ReportResponse(
            report_id=report_id,
            title="Reporte de Producción",
            generated_at=datetime.now(timezone.utc).isoformat(),
            format="pdf",
            content=pdf_content,
            file_name=f"produccion_{request.date_from}_{request.date_to}.pdf",
        )

    async def generate_financial_report(
        self, tenant_id: UUID, request: ReportRequest, uow: UnitOfWork
    ) -> ReportResponse:
        """Generate financial report"""
        report_id = str(uuid.uuid4())

        # Get production data with amounts
        productions = await uow.milk_productions.list(
            tenant_id, date_from=request.date_from, date_to=request.date_to, animal_id=None
        )

        # Get delivery data - handle if deliveries table doesn't exist or is empty
        try:
            deliveries = await uow.milk_deliveries.list(
                tenant_id, date_from=request.date_from, date_to=request.date_to, buyer_id=None
            )
        except Exception:
            # If deliveries not available, use empty list
            deliveries = []

        # Calculate financial KPIs
        production_revenue = sum(p.amount for p in productions if p.amount) or Decimal("0")
        delivery_revenue = sum(d.amount for d in deliveries) or Decimal("0")
        total_revenue = production_revenue + delivery_revenue

        total_liters_produced = sum(p.volume_l for p in productions)
        total_liters_delivered = sum(d.volume_l for d in deliveries)

        avg_price_per_liter = (
            total_revenue / (total_liters_produced + total_liters_delivered)
            if (total_liters_produced + total_liters_delivered) > 0
            else Decimal("0")
        )

        # Group revenue by period
        period_revenue = self._group_financial_by_period(productions + deliveries, request.period)

        # Group by buyers - handle if buyers table doesn't exist or is empty
        try:
            buyers = await uow.buyers.list(tenant_id)
            buyers_dict = {b.id: b for b in buyers}

            buyer_revenue = {}
            for delivery in deliveries:
                if delivery.buyer_id not in buyer_revenue:
                    buyer_revenue[delivery.buyer_id] = Decimal("0")
                buyer_revenue[delivery.buyer_id] += delivery.amount

            buyer_breakdown = []
            for buyer_id, revenue in buyer_revenue.items():
                buyer = buyers_dict.get(buyer_id)
                buyer_name = buyer.name if buyer else f"Comprador {str(buyer_id)[:8]}"
                buyer_breakdown.append(
                    {
                        "buyer_name": buyer_name,
                        "total_revenue": revenue,
                        "percentage": (revenue / total_revenue * 100)
                        if total_revenue > 0
                        else Decimal("0"),
                    }
                )

            buyer_breakdown.sort(key=lambda x: x["total_revenue"], reverse=True)
        except Exception:
            # If buyers not available, use empty list
            buyer_breakdown = []

        if request.format == "json":
            data = {
                "summary": {
                    "total_revenue": float(total_revenue),
                    "production_revenue": float(production_revenue),
                    "delivery_revenue": float(delivery_revenue),
                    "total_liters_produced": float(total_liters_produced),
                    "total_liters_delivered": float(total_liters_delivered),
                    "avg_price_per_liter": float(avg_price_per_liter),
                    "period_from": request.date_from.isoformat(),
                    "period_to": request.date_to.isoformat(),
                },
                "period_revenue": {k: float(v) for k, v in period_revenue.items()},
                "buyer_breakdown": [
                    {
                        "buyer_name": bb["buyer_name"],
                        "total_revenue": float(bb["total_revenue"]),
                        "percentage": float(bb["percentage"]),
                    }
                    for bb in buyer_breakdown
                ],
            }

            return ReportResponse(
                report_id=report_id,
                title="Reporte Financiero",
                generated_at=datetime.now(timezone.utc).isoformat(),
                format="json",
                data=data,
                file_name=f"financiero_{request.date_from}_{request.date_to}.json",
            )

        # Generate PDF
        elements = []

        # Header
        title = "Reporte Financiero"
        subtitle = f"Período: {request.date_from.strftime('%d/%m/%Y')} - "
        f"{request.date_to.strftime('%d/%m/%Y')}"
        elements.extend(self.pdf_generator.create_header(title, subtitle))

        # Financial KPIs
        kpis = {
            "total_revenue": total_revenue,
            "production_revenue": production_revenue,
            "delivery_revenue": delivery_revenue,
            "total_liters": total_liters_produced + total_liters_delivered,
            "avg_price_per_liter": avg_price_per_liter,
        }
        elements.extend(self.pdf_generator.create_kpi_section("Resumen Financiero", kpis))

        # Revenue chart by period
        if period_revenue:
            elements.extend(
                self.pdf_generator.create_chart_section(
                    f"Ingresos por {request.period.title()}",
                    {k: float(v) for k, v in period_revenue.items()},
                    "line",
                )
            )

        # Buyer breakdown table
        if buyer_breakdown:
            columns = ["Comprador", "Ingresos", "Porcentaje"]
            table_data = []
            for buyer in buyer_breakdown:
                table_data.append(
                    {
                        "comprador": buyer["buyer_name"],
                        "ingresos": buyer["total_revenue"],
                        "porcentaje": f"{buyer['percentage']:.1f}%",
                    }
                )

            elements.extend(
                self.pdf_generator.create_table_section(
                    "Ingresos por Comprador", table_data, columns
                )
            )

        pdf_content = self.pdf_generator.generate_pdf(elements)

        return ReportResponse(
            report_id=report_id,
            title="Reporte Financiero",
            generated_at=datetime.now(timezone.utc).isoformat(),
            format="pdf",
            content=pdf_content,
            file_name=f"financiero_{request.date_from}_{request.date_to}.pdf",
        )

    async def generate_animals_report(
        self, tenant_id: UUID, request: ReportRequest, uow: UnitOfWork
    ) -> ReportResponse:
        """Generate animals report"""
        report_id = str(uuid.uuid4())

        # Get animals data with filters
        if request.filters and request.filters.animal_ids:
            # Filter specific animals
            all_animals = await uow.animals.list(tenant_id)
            animals = [a for a in all_animals if a.id in request.filters.animal_ids]
        else:
            # Get all animals
            animals = await uow.animals.list(tenant_id)

        # Load statuses for this tenant (including system defaults) to resolve status names
        try:
            statuses = await uow.animal_statuses.list_for_tenant(tenant_id)
            status_name_by_id = {s.id: s.get_name("es") for s in statuses}
            status_code_by_id = {s.id: s.code for s in statuses}
        except Exception:
            status_name_by_id = {}
            status_code_by_id = {}

        # Apply include_inactive filter
        # TODO: Update to use new status_id system
        if request.filters and not request.filters.include_inactive:
            # For now, include all animals until status migration is complete
            pass

        # TODO: Update active/inactive logic to use status_id
        active_animals = animals  # Temporary: treat all as active
        inactive_animals = []  # Temporary: no inactive animals

        # Get production data for performance analysis
        if request.filters and request.filters.animal_ids:
            all_productions = []
            for animal_id in request.filters.animal_ids:
                animal_productions = await uow.milk_productions.list(
                    tenant_id,
                    date_from=request.date_from,
                    date_to=request.date_to,
                    animal_id=animal_id,
                )
                all_productions.extend(animal_productions)
            productions = all_productions
        else:
            productions = await uow.milk_productions.list(
                tenant_id, date_from=request.date_from, date_to=request.date_to, animal_id=None
            )

        # Calculate animal performance
        animal_performance = {}
        for prod in productions:
            if prod.animal_id:
                if prod.animal_id not in animal_performance:
                    animal_performance[prod.animal_id] = {
                        "total_liters": Decimal("0"),
                        "records_count": 0,
                        "avg_per_record": Decimal("0"),
                    }
                animal_performance[prod.animal_id]["total_liters"] += prod.volume_l
                animal_performance[prod.animal_id]["records_count"] += 1

        # Calculate averages
        for _, perf in animal_performance.items():
            if perf["records_count"] > 0:
                perf["avg_per_record"] = perf["total_liters"] / perf["records_count"]

        # Create detailed animal list
        animal_details = []
        for animal in animals:
            perf = animal_performance.get(
                animal.id,
                {"total_liters": Decimal("0"), "records_count": 0, "avg_per_record": Decimal("0")},
            )

            # Resolve status name and code from status_id if present
            status_display = "Sin estado"
            status_code = None
            if getattr(animal, "status_id", None):
                status_display = status_name_by_id.get(animal.status_id, "Sin estado")
                status_code = status_code_by_id.get(animal.status_id)

            animal_details.append(
                {
                    "name": animal.name,
                    "tag": animal.tag,
                    "status": status_display,
                    "status_code": status_code,
                    "total_liters": perf["total_liters"],
                    "records_count": perf["records_count"],
                    "avg_per_record": perf["avg_per_record"],
                }
            )

        # Sort by performance
        animal_details.sort(key=lambda x: x["total_liters"], reverse=True)

        if request.format == "json":
            data = {
                "summary": {
                    "total_animals": len(animals),
                    "active_animals": len(active_animals),
                    "inactive_animals": len(inactive_animals),
                    "period_from": request.date_from.isoformat(),
                    "period_to": request.date_to.isoformat(),
                },
                "animals": [
                    {
                        "name": ad["name"],
                        "tag": ad["tag"],
                        "status": ad["status"],
                        "status_code": ad.get("status_code"),
                        "total_liters": float(ad["total_liters"]),
                        "records_count": ad["records_count"],
                        "avg_per_record": float(ad["avg_per_record"]),
                    }
                    for ad in animal_details
                ],
            }

            return ReportResponse(
                report_id=report_id,
                title="Reporte de Animales",
                generated_at=datetime.now(timezone.utc).isoformat(),
                format="json",
                data=data,
                file_name=f"animales_{request.date_from}_{request.date_to}.json",
            )

        # Generate PDF
        elements = []

        # Header
        title = "Reporte de Animales"
        subtitle = f"Período: {request.date_from.strftime('%d/%m/%Y')} - "
        f"{request.date_to.strftime('%d/%m/%Y')}"
        elements.extend(self.pdf_generator.create_header(title, subtitle))

        # Summary KPIs
        kpis = {
            "total_animals": len(animals),
            "active_animals": len(active_animals),
            "inactive_animals": len(inactive_animals),
            "active_percentage": (len(active_animals) / len(animals) * 100) if animals else 0,
        }
        elements.extend(self.pdf_generator.create_kpi_section("Resumen del Inventario", kpis))

        # Animals performance table
        columns = ["Nombre", "Etiqueta", "Estado", "Total Litros", "Registros", "Prom/Registro"]
        table_data = []
        for animal in animal_details:
            table_data.append(
                {
                    "nombre": animal["name"],
                    "etiqueta": animal["tag"],
                    "estado": animal["status"],
                    "total_litros": animal["total_liters"],
                    "registros": animal["records_count"],
                    "prom/registro": animal["avg_per_record"],
                }
            )

        elements.extend(
            self.pdf_generator.create_table_section(
                "Rendimiento Individual por Animal", table_data, columns
            )
        )

        pdf_content = self.pdf_generator.generate_pdf(elements)

        return ReportResponse(
            report_id=report_id,
            title="Reporte de Animales",
            generated_at=datetime.now(timezone.utc).isoformat(),
            format="pdf",
            content=pdf_content,
            file_name=f"animales_{request.date_from}_{request.date_to}.pdf",
        )

    def _group_by_period(self, productions: list, period: str) -> dict[str, Decimal]:
        """Group production data by period"""
        grouped = {}

        for prod in productions:
            if period == "daily":
                key = prod.date.strftime("%d/%m")
            elif period == "weekly":
                # Get week number
                week = prod.date.isocalendar()[1]
                key = f"Semana {week}"
            elif period == "monthly":
                key = prod.date.strftime("%m/%Y")
            else:
                key = prod.date.strftime("%d/%m")

            if key not in grouped:
                grouped[key] = Decimal("0")
            grouped[key] += prod.volume_l

        return grouped

    def _group_deliveries_by_period(self, deliveries: list, period: str) -> dict[str, Decimal]:
        """Group delivery data by period"""
        grouped = {}

        for delivery in deliveries:
            delivery_date = getattr(delivery, "date", getattr(delivery, "date_time", None))
            if not delivery_date:
                continue

            if hasattr(delivery_date, "date"):
                delivery_date = delivery_date.date()

            if period == "daily":
                key = delivery_date.strftime("%d/%m")
            elif period == "weekly":
                week = delivery_date.isocalendar()[1]
                key = f"Semana {week}"
            elif period == "monthly":
                key = delivery_date.strftime("%m/%Y")
            else:
                key = delivery_date.strftime("%d/%m")

            if key not in grouped:
                grouped[key] = Decimal("0")
            grouped[key] += delivery.volume_l

        return grouped

    def _group_financial_by_period(self, records: list, period: str) -> dict[str, Decimal]:
        """Group financial data by period"""
        grouped = {}

        for record in records:
            record_date = getattr(record, "date", getattr(record, "date_time", None))
            if not record_date:
                continue

            if hasattr(record_date, "date"):
                record_date = record_date.date()

            if period == "daily":
                key = record_date.strftime("%d/%m")
            elif period == "weekly":
                week = record_date.isocalendar()[1]
                key = f"Semana {week}"
            elif period == "monthly":
                key = record_date.strftime("%m/%Y")
            else:
                key = record_date.strftime("%d/%m")

            if key not in grouped:
                grouped[key] = Decimal("0")

            amount = getattr(record, "amount", Decimal("0"))
            if amount:
                grouped[key] += amount

        return grouped
