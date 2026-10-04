"""Professional JSON/PDF report generation for completed scans."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.db import get_db
from database.models import Report, Scan, ScanStatusEnum, SeverityEnum, Vulnerability

router = APIRouter()


class ReportRequest(BaseModel):
    scan_id: str
    format: str = "pdf"


@router.get("/")
async def list_reports(db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(Report).order_by(desc(Report.generated_at)))
    reports = result.scalars().all()
    return {
        "reports": [
            {
                "id": report.id,
                "scan_id": report.scan_id,
                "title": report.title,
                "format": report.report_format,
                "generated_at": report.generated_at.isoformat(),
                "risk_score": report.overall_risk_score,
                "download": f"/api/reports/{report.id}/download",
            }
            for report in reports
        ],
        "total": len(reports),
    }


@router.post("/generate")
async def generate_report(request: ReportRequest, db: AsyncSession = Depends(get_db)) -> dict:
    if request.format.lower() != "pdf":
        raise HTTPException(status_code=400, detail="Only PDF report generation is currently enabled")
    scan_result = await db.execute(select(Scan).where(Scan.id == request.scan_id))
    scan = scan_result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scan.status != ScanStatusEnum.COMPLETED:
        raise HTTPException(status_code=400, detail="Only completed scans can generate reports")
    vuln_result = await db.execute(select(Vulnerability).where(Vulnerability.scan_id == scan.id))
    vulnerabilities = list(vuln_result.scalars().all())
    output_dir = Path(settings.REPORT_STORAGE_PATH)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_id = str(uuid.uuid4())
    output_path = output_dir / f"{report_id}.pdf"
    _write_pdf(output_path, scan, vulnerabilities)
    counts = {severity: sum(1 for item in vulnerabilities if item.severity == severity) for severity in SeverityEnum}
    risk_score = min(10.0, counts[SeverityEnum.CRITICAL] * 4 + counts[SeverityEnum.HIGH] * 2.5 + counts[SeverityEnum.MEDIUM])
    report = Report(
        id=report_id,
        scan_id=scan.id,
        title=f"Security assessment: {scan.target}",
        report_format="pdf",
        report_path=str(output_path),
        total_vulnerabilities=len(vulnerabilities),
        critical_count=counts[SeverityEnum.CRITICAL],
        high_count=counts[SeverityEnum.HIGH],
        medium_count=counts[SeverityEnum.MEDIUM],
        low_count=counts[SeverityEnum.LOW],
        overall_risk_score=risk_score,
    )
    db.add(report)
    scan.report_generated = True
    scan.report_path = str(output_path)
    await db.commit()
    return {"id": report_id, "scan_id": scan.id, "format": "pdf", "download": f"/api/reports/{report_id}/download"}


@router.get("/{report_id}/download")
async def download_report(report_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report or not Path(report.report_path).is_file():
        raise HTTPException(status_code=404, detail="Report file not found")
    return FileResponse(report.report_path, media_type="application/pdf", filename=f"security-report-{report.scan_id}.pdf")


@router.get("/scan/{scan_id}/download")
async def download_report_by_scan_id(scan_id: str, db: AsyncSession = Depends(get_db)):
    """Directly download the PDF report for a scan by scan_id."""
    result = await db.execute(
        select(Report).where(Report.scan_id == scan_id).order_by(desc(Report.generated_at))
    )
    report = result.scalars().first()
    if report and Path(report.report_path).is_file():
        return FileResponse(
            report.report_path,
            media_type="application/pdf",
            filename=f"security-report-{scan_id}.pdf",
        )

    # Check for direct file in reports storage
    direct_file = Path(settings.REPORT_STORAGE_PATH) / f"{scan_id}.pdf"
    if direct_file.is_file():
        return FileResponse(
            str(direct_file),
            media_type="application/pdf",
            filename=f"security-report-{scan_id}.pdf",
        )

    # Auto-generate on-demand if scan is completed
    scan_result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = scan_result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scan.status != ScanStatusEnum.COMPLETED:
        raise HTTPException(status_code=400, detail="Scan is not completed yet")

    vuln_result = await db.execute(select(Vulnerability).where(Vulnerability.scan_id == scan.id))
    vulnerabilities = list(vuln_result.scalars().all())
    output_dir = Path(settings.REPORT_STORAGE_PATH)
    output_dir.mkdir(parents=True, exist_ok=True)
    new_report_id = str(uuid.uuid4())
    output_path = output_dir / f"{new_report_id}.pdf"
    _write_pdf(output_path, scan, vulnerabilities)

    counts = {severity: sum(1 for item in vulnerabilities if item.severity == severity) for severity in SeverityEnum}
    risk_score = min(10.0, counts[SeverityEnum.CRITICAL] * 4 + counts[SeverityEnum.HIGH] * 2.5 + counts[SeverityEnum.MEDIUM])
    new_report = Report(
        id=new_report_id,
        scan_id=scan.id,
        title=f"Security assessment: {scan.target}",
        report_format="pdf",
        report_path=str(output_path),
        total_vulnerabilities=len(vulnerabilities),
        critical_count=counts[SeverityEnum.CRITICAL],
        high_count=counts[SeverityEnum.HIGH],
        medium_count=counts[SeverityEnum.MEDIUM],
        low_count=counts[SeverityEnum.LOW],
        overall_risk_score=risk_score,
    )
    db.add(new_report)
    scan.report_generated = True
    scan.report_path = str(output_path)
    await db.commit()

    return FileResponse(
        str(output_path),
        media_type="application/pdf",
        filename=f"security-report-{scan_id}.pdf",
    )


def _write_pdf(path: Path, scan: Scan, vulnerabilities: list[Vulnerability]) -> None:
    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=0.65 * inch, leftMargin=0.65 * inch)
    story = [
        Paragraph("Security Assessment Report", styles["Title"]),
        Paragraph(f"Target: {scan.target}", styles["Heading2"]),
        Paragraph(f"Mode: {scan.mode} | Scan ID: {scan.id}", styles["Normal"]),
        Spacer(1, 0.2 * inch),
        Paragraph("Executive Summary", styles["Heading2"]),
        Paragraph(
            f"This report documents the evidence collected for {scan.target}. "
            f"The assessment recorded {len(vulnerabilities)} finding(s). "
            "Only tools and targets authorized by the submitted JSON scope were considered.",
            styles["BodyText"],
        ),
        Spacer(1, 0.18 * inch),
    ]
    rows = [["Severity", "Title", "Type", "Description"]]
    for vulnerability in vulnerabilities:
        rows.append([
            vulnerability.severity.value if vulnerability.severity else "unknown",
            vulnerability.title,
            vulnerability.vulnerability_type,
            vulnerability.description[:500],
        ])
    table = Table(rows, repeatRows=1, colWidths=[0.8 * inch, 1.55 * inch, 1.1 * inch, 3.2 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), "#202c2a"),
        ("TEXTCOLOR", (0, 0), (-1, 0), "white"),
        ("GRID", (0, 0), (-1, -1), 0.25, "#999999"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.extend([Paragraph("Findings", styles["Heading2"]), table, Spacer(1, 0.2 * inch)])
    story.extend([
        Paragraph("Recommendations", styles["Heading2"]),
        Paragraph("Prioritize remediation by severity, preserve the evidence associated with each finding, and repeat the scoped assessment after fixes are applied.", styles["BodyText"]),
    ])
    document.build(story)


