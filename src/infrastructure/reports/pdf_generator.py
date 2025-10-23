from __future__ import annotations

import base64
import io
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class PDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    @staticmethod
    def _thin_labels(labels: list[str], max_labels: int = 10) -> list[str]:
        """Return labels where only ~max_labels are shown; others blank to reduce clutter."""
        if not labels:
            return labels
        if len(labels) <= max_labels:
            return labels
        import math

        stride = max(1, math.ceil(len(labels) / max_labels))
        return [
            lbl if (i % stride == 0 or i == len(labels) - 1) else "" for i, lbl in enumerate(labels)
        ]

    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(
            ParagraphStyle(
                name="CustomTitle",
                parent=self.styles["Heading1"],
                fontSize=18,
                spaceAfter=30,
                textColor=colors.darkblue,
                alignment=1,  # Center
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="CustomHeading",
                parent=self.styles["Heading2"],
                fontSize=14,
                spaceAfter=12,
                textColor=colors.darkblue,
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="CustomSubheading",
                parent=self.styles["Heading3"],
                fontSize=12,
                spaceAfter=6,
                textColor=colors.darkgreen,
            )
        )

        # Table header style with white text for dark backgrounds
        self.styles.add(
            ParagraphStyle(
                name="TableHeaderWhite",
                parent=self.styles["Normal"],
                fontSize=9,
                textColor=colors.white,
                leading=11,
            )
        )

    def create_header(self, title: str, subtitle: str | None = None) -> list:
        """Create report header"""
        elements = []

        # Title
        elements.append(Paragraph(title, self.styles["CustomTitle"]))

        if subtitle:
            elements.append(Paragraph(subtitle, self.styles["CustomSubheading"]))

        # Generation date
        gen_date = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
        elements.append(Paragraph(f"Generado el: {gen_date}", self.styles["Normal"]))
        elements.append(Spacer(1, 20))

        return elements

    def create_kpi_section(self, title: str, kpis: dict[str, Any]) -> list:
        """Create KPI section with cards"""
        elements = []
        elements.append(Paragraph(title, self.styles["CustomHeading"]))

        # Create KPI table
        data = []
        # Mapping of known KPI keys to Spanish labels
        es_labels = {
            "total_liters_produced": "Total litros producidos",
            "total_liters_delivered": "Total litros entregados",
            "retention_difference": "Diferencia de retención",
            "retention_percentage": "Porcentaje de retención",
            "total_records": "Registros totales",
            "avg_per_record": "Promedio por registro",
            "period_days": "Días del período",
            # Financial
            "total_revenue": "Ingresos totales",
            "production_revenue": "Ingresos por producción",
            "delivery_revenue": "Ingresos por entregas",
            "avg_price_per_liter": "Precio promedio por litro",
            # Admin overview
            "total_liters": "Total de litros",
        }
        for key, value in kpis.items():
            formatted_key = es_labels.get(key, key.replace("_", " ").title())
            if isinstance(value, Decimal):
                formatted_value = f"{value:,.2f}"
            else:
                formatted_value = str(value)
            data.append([formatted_key, formatted_value])

        if data:
            table = Table(data, colWidths=[3 * inch, 2 * inch])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey),
                        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                        ("TOPPADDING", (0, 0), (-1, -1), 12),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            elements.append(table)

        elements.append(Spacer(1, 20))
        return elements

    def create_table_section(self, title: str, data: list[dict], columns: list[str]) -> list:
        """Create a table section"""
        elements = []
        elements.append(Paragraph(title, self.styles["CustomHeading"]))

        if not data:
            elements.append(Paragraph("No hay datos disponibles", self.styles["Normal"]))
            elements.append(Spacer(1, 20))
            return elements

        # Create table data
        table_data = [columns]  # Header row

        for row in data:
            table_row = []
            for col in columns:
                value = row.get(col.lower().replace(" ", "_"), "")
                if isinstance(value, Decimal):
                    table_row.append(f"{value:,.2f}")
                elif isinstance(value, (date, datetime)):
                    table_row.append(value.strftime("%d/%m/%Y"))
                else:
                    # Wrap long text using Paragraph so it doesn't overflow
                    text = "" if value is None else str(value)
                    table_row.append(Paragraph(text, self.styles["Normal"]))
            table_data.append(table_row)

        # Calculate column widths
        col_count = len(columns)
        col_width = 6.5 * inch / col_count

        table = Table(table_data, colWidths=[col_width] * col_count)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )

        elements.append(table)
        elements.append(Spacer(1, 20))
        return elements

    def create_chart_section(self, title: str, chart_data: dict, chart_type: str = "bar") -> list:
        """Create a chart section"""
        elements = []
        elements.append(Paragraph(title, self.styles["CustomHeading"]))

        try:
            if chart_type == "bar":
                chart = self._create_bar_chart(chart_data)
            elif chart_type == "line":
                chart = self._create_line_chart(chart_data)
            else:
                chart = self._create_bar_chart(chart_data)

            elements.append(chart)
        except Exception:
            elements.append(Paragraph("Error al generar gráfico", self.styles["Normal"]))

        elements.append(Spacer(1, 20))
        return elements

    def create_daily_detail_matrix(
        self,
        title: str,
        headers_animals: list[dict],
        rows: list[dict],
    ) -> list:
        """Create a wide matrix table for daily detail.
        headers_animals: list of { tag: str, name: str }
        rows: list of { date_label: str, cells: list[str], total_liters: str, revenue: str }
        """
        elements = []
        elements.append(Paragraph(title, self.styles["CustomHeading"]))

        # Build header row: Fecha | per-animal header | Total/Ingresos
        header = [Paragraph("<b>Fecha</b>", self.styles["TableHeaderWhite"])]
        for a in headers_animals:
            hdr = Paragraph(
                f"<b>{a.get('tag','')}</b><br/>{a.get('name','')}",
                self.styles["TableHeaderWhite"],
            )
            header.append(hdr)
        header.append(Paragraph("<b>Total/Ingresos</b>", self.styles["TableHeaderWhite"]))

        table_data = [header]
        for r in rows:
            row_cells = [Paragraph(r.get("date_label", ""), self.styles["Normal"])]
            # matrix cells already formatted as strings with possible line breaks
            for c in r.get("cells", []):
                row_cells.append(Paragraph(c or "", self.styles["Normal"]))
            row_cells.append(Paragraph(r.get("summary", ""), self.styles["Normal"]))
            table_data.append(row_cells)

        # Column widths: first wider for date, animals flexible, last two moderate
        col_count = len(header)
        # Page width minus margins roughly 6.5 inch; distribute
        if col_count > 0:
            date_w = 1.2 * inch
            tail_w = 1.5 * inch
            remaining = max(1, col_count - 3)
            animal_w = max(0.6 * inch, (6.5 * inch - (date_w + 2 * tail_w)) / remaining)
            col_widths = [date_w] + [animal_w] * (col_count - 3) + [tail_w, tail_w]
        else:
            col_widths = None

        table = Table(table_data, colWidths=col_widths)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    # Make the Total/Ingresos column bold across all data rows
                    ("FONTNAME", (-1, 1), (-1, -1), "Helvetica-Bold"),
                ]
            )
        )

        # If last row is a total row, bold it
        if rows:
            last_idx = len(table_data) - 1
            if rows[-1].get("is_total"):
                table.setStyle(
                    TableStyle(
                        [
                            ("FONTNAME", (0, last_idx), (-1, last_idx), "Helvetica-Bold"),
                            ("BACKGROUND", (0, last_idx), (-1, last_idx), colors.lightgrey),
                        ]
                    )
                )

        elements.append(table)
        elements.append(Spacer(1, 20))
        return elements

    def create_combined_chart_section(self, title: str, series_a: dict, series_b: dict) -> list:
        """Create a combined chart for two series (Producción vs Entregas).
        Uses grouped bars when <= 10 puntos; otherwise, two líneas.
        """
        elements = []
        elements.append(Paragraph(title, self.styles["CustomHeading"]))

        try:
            # Union of labels, preserve order from series_a then add missing from series_b
            labels = list(series_a.keys())
            for k in series_b.keys():
                if k not in labels:
                    labels.append(k)

            values_a = [float(series_a.get(lbl, 0.0)) for lbl in labels]
            values_b = [float(series_b.get(lbl, 0.0)) for lbl in labels]

            # Legend: green = Producción, blue = Entregas (use line markers)
            legend = Drawing(400, 24)
            from reportlab.graphics.shapes import Line, String

            # Producción (verde)
            legend.add(Line(10, 12, 60, 12, strokeColor=colors.green, strokeWidth=2))
            legend.add(String(65, 8, "Producción", fontName="Helvetica", fontSize=9))
            # Entregas (azul)
            legend.add(Line(140, 12, 190, 12, strokeColor=colors.blue, strokeWidth=2))
            legend.add(String(195, 8, "Entregas", fontName="Helvetica", fontSize=9))

            if len(labels) <= 10:
                chart_drawing = self._create_bar_chart_multi(labels, values_a, values_b)
            else:
                chart_drawing = self._create_line_chart_multi(labels, values_a, values_b)

            elements.append(legend)
            elements.append(chart_drawing)
        except Exception:
            elements.append(Paragraph("Error al generar gráfico combinado", self.styles["Normal"]))

        elements.append(Spacer(1, 20))
        return elements

    def _apply_value_axis_padding(self, chart, values: list[float], padding: float = 15.0):
        """Apply min/max padding to a chart's value axis to ensure small bars/lines are visible."""
        try:
            if not values:
                return
            vmin = min(values)
            vmax = max(values)
            # If all zero, keep small headroom so bars show
            if vmin == 0 and vmax == 0:
                chart.valueAxis.valueMin = 0
                chart.valueAxis.valueMax = padding
                return
            import math

            chart.valueAxis.valueMin = max(0.0, math.floor(vmin - padding))
            chart.valueAxis.valueMax = math.ceil(vmax + padding)
        except Exception:
            # Be permissive: if ReportLab internals differ, avoid crashing
            pass

    def _create_bar_chart_multi(
        self, labels: list[str], series_a: list[float], series_b: list[float]
    ) -> Drawing:
        drawing = Drawing(400, 220)
        chart = VerticalBarChart()
        chart.x = 40
        chart.y = 50
        chart.height = 140
        chart.width = 320

        chart.data = [series_a, series_b]
        chart.categoryAxis.categoryNames = labels

        # Colors for the two series (0 = Producción, 1 = Entregas)
        chart.bars[0].fillColor = colors.lightgreen
        chart.bars[1].fillColor = colors.lightblue

        # Apply Y-axis padding so low values aren't clipped
        all_vals = [v for v in series_a + series_b if v is not None]
        self._apply_value_axis_padding(chart, all_vals, padding=15.0)

        drawing.add(chart)
        return drawing

    def _create_line_chart_multi(
        self, labels: list[str], series_a: list[float], series_b: list[float]
    ) -> Drawing:
        drawing = Drawing(400, 220)
        chart = HorizontalLineChart()
        chart.x = 40
        chart.y = 50
        chart.height = 140
        chart.width = 320

        chart.data = [series_a, series_b]
        chart.categoryAxis.categoryNames = self._thin_labels(labels, 10)

        # Try tilting labels for readability
        try:
            chart.categoryAxis.labels.angle = 45
        except Exception:
            pass

        # Style (0 = Producción -> verde, 1 = Entregas -> azul)
        chart.lines[0].strokeColor = colors.green
        chart.lines[1].strokeColor = colors.blue

        # Apply Y-axis padding for line chart as well
        all_vals = [v for v in series_a + series_b if v is not None]
        self._apply_value_axis_padding(chart, all_vals, padding=15.0)

        drawing.add(chart)
        return drawing

    def _create_bar_chart(self, data: dict) -> Drawing:
        """Create a bar chart"""
        drawing = Drawing(400, 200)
        chart = VerticalBarChart()
        chart.x = 50
        chart.y = 50
        chart.height = 125
        chart.width = 300

        # Extract data
        labels = list(data.keys())[:10]  # Limit to 10 items
        values = [float(data[label]) for label in labels]

        chart.data = [values]
        chart.categoryAxis.categoryNames = labels
        chart.bars[0].fillColor = colors.lightblue

        drawing.add(chart)
        return drawing

    def _create_line_chart(self, data: dict) -> Drawing:
        """Create a line chart"""
        drawing = Drawing(400, 200)
        chart = HorizontalLineChart()
        chart.x = 50
        chart.y = 50
        chart.height = 125
        chart.width = 300

        # Extract data
        labels = list(data.keys())
        values = [float(data[label]) for label in labels]

        chart.data = [values]
        chart.categoryAxis.categoryNames = self._thin_labels(labels, 10)
        try:
            chart.categoryAxis.labels.angle = 45
        except Exception:
            pass
        chart.lines[0].strokeColor = colors.blue

        drawing.add(chart)
        return drawing

    def generate_pdf(self, elements: list) -> str:
        """Generate PDF and return as base64 string"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18
        )

        doc.build(elements)
        buffer.seek(0)

        pdf_data = buffer.getvalue()
        buffer.close()

        return base64.b64encode(pdf_data).decode("utf-8")
