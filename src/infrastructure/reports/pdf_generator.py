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
        for key, value in kpis.items():
            formatted_key = key.replace("_", " ").title()
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
                    table_row.append(str(value))
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
        labels = list(data.keys())[:10]  # Limit to 10 items
        values = [float(data[label]) for label in labels]

        chart.data = [values]
        chart.categoryAxis.categoryNames = labels
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
