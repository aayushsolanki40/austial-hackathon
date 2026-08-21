"""Compliance-related background tasks -- Phase 8.

``generate_report_pdf_task``: renders a ``ComplianceReport``'s aggregated data to PDF, uploads to
S3, and updates ``file_storage_key``. Triggered asynchronously by
``ComplianceService.generate_quarterly_report``.
"""

from __future__ import annotations

import io
import os
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.jobs.celery_app import celery_app


@celery_app.task(name="jobs.generate_report_pdf")
def generate_report_pdf_task(report_id: int) -> str:
    """Generate PDF for ComplianceReport and upload to S3.

    Returns the S3 key where the PDF was stored.

    NOTE: this task runs in a separate Celery worker process, not the main FastAPI app process, so
    it can't use the app's DI container (no access to ``Repository``, ``ConfigService``, etc.).
    Instead, it reconstructs the minimal dependencies it needs (DB connection, S3 client) from env
    vars directly.
    """
    # Import inside task body (not at module top) to avoid circular import when celery_app loads
    # this module before the app is fully constructed.
    import boto3
    from sqlalchemy import create_engine, text

    # Read DB connection and S3 config from env (Celery worker doesn't have access to ConfigService).
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set in Celery worker environment")
    documents_bucket = os.environ.get("DOCUMENTS_S3_BUCKET")
    if not documents_bucket:
        raise RuntimeError("DOCUMENTS_S3_BUCKET not set in Celery worker environment")
    aws_region = os.environ.get("AWS_REGION", "us-east-1")

    # Fetch report from DB.
    engine = create_engine(database_url)
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM compliance_report WHERE id = :id"), {"id": report_id}
        ).fetchone()
        if not row:
            raise ValueError(f"No ComplianceReport with id={report_id}")

    # Build PDF in memory.
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=0.75 * inch, leftMargin=0.75 * inch)
    story = []
    styles = getSampleStyleSheet()

    # Title
    story.append(Paragraph(f"<b>{row.report_type} Report</b>", styles["Title"]))
    story.append(Spacer(1, 0.25 * inch))

    # Metadata
    story.append(Paragraph(f"<b>Period:</b> {row.period_start} to {row.period_end}", styles["Normal"]))
    story.append(
        Paragraph(f"<b>Generated:</b> {row.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}", styles["Normal"])
    )
    story.append(Spacer(1, 0.25 * inch))

    # Metrics table
    data = [
        ["Metric", "Value"],
        ["Total AUM (USD)", f"${row.aum_total_usd:,.2f}"],
        ["Investor Count", str(row.investor_count)],
        ["Active Issuances", str(row.active_issuances_count)],
    ]
    table = Table(data, colWidths=[3 * inch, 3 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), "#4a5568"),
                ("TEXTCOLOR", (0, 0), (-1, 0), "#ffffff"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), "#f7fafc"),
                ("GRID", (0, 0), (-1, -1), 0.5, "#cbd5e0"),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 0.25 * inch))

    # Currency breakdown
    story.append(Paragraph("<b>Currency Breakdown</b>", styles["Heading2"]))
    currency_data = [["Currency", "Total Amount"]]
    for currency, amount in row.currency_breakdown.items():
        currency_data.append([currency, f"${float(amount):,.2f}"])
    currency_table = Table(currency_data, colWidths=[3 * inch, 3 * inch])
    currency_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), "#4a5568"),
                ("TEXTCOLOR", (0, 0), (-1, 0), "#ffffff"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 12),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), "#f7fafc"),
                ("GRID", (0, 0), (-1, -1), 0.5, "#cbd5e0"),
            ]
        )
    )
    story.append(currency_table)

    # Build PDF.
    doc.build(story)
    buffer.seek(0)

    # Upload to S3.
    s3_client = boto3.client("s3", region_name=aws_region)
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    s3_key = f"compliance-reports/{row.report_type.lower()}-{report_id}-{timestamp}.pdf"
    s3_client.put_object(Bucket=documents_bucket, Key=s3_key, Body=buffer.getvalue(), ContentType="application/pdf")

    # Update report entity with file_storage_key and status=FINALIZED.
    with engine.connect() as conn:
        conn.execute(
            text(
                "UPDATE compliance_report SET file_storage_key = :key, status = :status WHERE id = :id"
            ),
            {"key": s3_key, "status": "FINALIZED", "id": report_id},
        )
        conn.commit()

    return s3_key
