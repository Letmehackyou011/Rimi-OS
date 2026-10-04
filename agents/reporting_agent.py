"""
Reporting Agent
Synthesizes multi-agent assessment results into executive summaries,
OWASP vulnerability breakdowns, prioritized remediation playbooks, and formats them into PDF and HTML reports.
"""

from __future__ import annotations

import asyncio
from functools import partial
import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, List
import uuid

from config.settings import settings
from utils.llm_router import get_llm_router

logger = logging.getLogger(__name__)


class ReportingAgent:
    """Specialized agent for executive and technical vulnerability reporting."""

    def __init__(self):
        self.router = get_llm_router()

    async def generate_report_narrative(
        self,
        target: str,
        mode: str,
        recon_data: Dict[str, Any],
        vulnerabilities: List[Dict[str, Any]],
        preferred_provider: str | None = None,
        preferred_model: str | None = None,
    ) -> Dict[str, Any]:
        """Synthesize findings with the reporting LLM."""
        verified_count = sum(1 for v in vulnerabilities if v.get("verified"))

        prompt = f"""
You are a lead cyber security consultant drafting an assessment report.
Synthesize the findings for target {target}:

TARGET: {target}
MODE: {mode}
DISCOVERED FINDINGS ({len(vulnerabilities)} total, {verified_count} verified):
{json.dumps([{ 'title': v.get('title'), 'severity': v.get('severity'), 'type': v.get('type'), 'owasp': v.get('owasp_category') } for v in vulnerabilities], indent=2)}

TECHNICAL EVIDENCE:
- Open Ports: {recon_data.get('open_ports', [])}
- Missing Headers: {recon_data.get('http_security', {}).get('missing_security_headers', [])}
- Server Banner: {recon_data.get('http_security', {}).get('server')}

Produce a polished, executive-ready security assessment summary.
Return ONLY a valid JSON object matching this schema:
{{
    "executive_summary": "1-2 paragraphs summarizing the security posture, key risks, and immediate concerns.",
    "overall_risk_score": 5.5,
    "primary_threat_vectors": ["Vector 1", "Vector 2"],
    "recommendations": [
        "Immediate Action: Enforce HSTS...",
        "Short-term Action: Add anti-clickjacking frame controls...",
        "Long-term Action: Establish continuous security monitoring..."
    ]
}}
"""
        result = await self.router.generate_for_agent(
            agent_name="reporting",
            prompt=prompt,
            preferred_provider=preferred_provider,
            preferred_model=preferred_model,
        )

        narrative = self._parse_narrative(result.get("content", ""))
        if not narrative.get("executive_summary"):
            narrative = {
                "executive_summary": f"Security assessment for {target}. The assessment identified {len(vulnerabilities)} finding(s) with {verified_count} verified issues across network and application security boundaries.",
                "overall_risk_score": min(10.0, len([v for v in vulnerabilities if v.get('severity') in ('critical', 'high')]) * 2.5 + len(vulnerabilities) * 0.5),
                "primary_threat_vectors": ["Web Application Misconfigurations", "Transport Layer Exposures"],
                "recommendations": [
                    "Enforce strict transport layer security with HSTS and SSL/TLS best practices.",
                    "Implement defense-in-depth HTTP security headers (CSP, X-Frame-Options).",
                    "Restrict exposed administration endpoints and services.",
                ]
            }
        return narrative

    async def create_pdf_report(
        self,
        report_id: str,
        scan_id: str,
        target: str,
        mode: str,
        vulnerabilities: List[Dict[str, Any]],
        narrative: Dict[str, Any],
        recon_data: Dict[str, Any],
    ) -> Path:
        """Create PDF document on disk using ReportLab."""
        output_dir = Path(settings.REPORT_STORAGE_PATH)
        output_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = output_dir / f"{report_id}.pdf"

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            partial(self._render_pdf_sync, pdf_path, scan_id, target, mode, vulnerabilities, narrative, recon_data)
        )
        return pdf_path

    def _render_pdf_sync(
        self,
        path: Path,
        scan_id: str,
        target: str,
        mode: str,
        vulnerabilities: List[Dict[str, Any]],
        narrative: Dict[str, Any],
        recon_data: Dict[str, Any],
    ) -> None:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(
            str(path), pagesize=letter,
            leftMargin=0.65 * inch, rightMargin=0.65 * inch,
            topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        )

        risk_score = narrative.get("overall_risk_score", 0.0)
        exec_summary = narrative.get("executive_summary", "")
        recommendations = narrative.get("recommendations", [])

        story = [
            Paragraph("AI Security Research OS — Assessment Report", styles["Title"]),
            Paragraph(f"Target: {target}", styles["Heading2"]),
            Paragraph(f"Mode: {mode.upper()}  |  Scan ID: {scan_id}", styles["Normal"]),
            Spacer(1, 0.2 * inch),
            Paragraph(f"Overall Risk Score: {risk_score:.1f} / 10.0", styles["Heading3"]),
            Spacer(1, 0.1 * inch),
            Paragraph("Executive Summary", styles["Heading2"]),
            Paragraph(str(exec_summary), styles["BodyText"]),
            Spacer(1, 0.2 * inch),
            Paragraph("Vulnerability Findings", styles["Heading2"]),
        ]

        rows = [["Severity", "Finding Title", "OWASP Category", "Verified"]]
        for v in vulnerabilities:
            rows.append([
                str(v.get("severity", "medium")).upper(),
                str(v.get("title", ""))[:80],
                str(v.get("owasp_category", v.get("type", "")))[:30],
                "YES" if v.get("verified") else "POTENTIAL",
            ])
        if len(rows) == 1:
            rows.append(["—", "No security findings recorded at this time.", "—", "—"])

        table = Table(rows, repeatRows=1, colWidths=[0.85 * inch, 2.7 * inch, 2.2 * inch, 0.9 * inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), "#131b2e"),
            ("TEXTCOLOR", (0, 0), (-1, 0), "white"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, "#888888"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), ["#fbfbfb", "#edf2f7"]),
        ]))
        story.extend([table, Spacer(1, 0.25 * inch)])

        story.append(Paragraph("Remediation Playbook", styles["Heading2"]))
        for rec in recommendations:
            story.append(Paragraph(f"• {rec}", styles["BodyText"]))

        story.extend([
            Spacer(1, 0.2 * inch),
            Paragraph("Reconnaissance Telemetry", styles["Heading2"]),
            Paragraph(
                f"Resolved IPs: {recon_data.get('dns', {}).get('ip_addresses', [])}  |  "
                f"Open Ports: {[p.get('port') for p in recon_data.get('open_ports', [])]}  |  "
                f"Server: {recon_data.get('http_security', {}).get('server', 'N/A')}",
                styles["BodyText"],
            ),
        ])

        doc.build(story)

    def _parse_narrative(self, raw_text: str) -> Dict[str, Any]:
        try:
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        return {}
