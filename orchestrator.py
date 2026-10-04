"""
AI Multi-Agent Security Orchestrator - Coordinates 4 specialized agents:
1. Reconnaissance Agent (OSINT, DNS, subdomain enumeration, port scanning, HTTP security)
2. Vulnerability Analysis Agent (CVE detection, OWASP Top-10 classification, CVSS scoring)
3. Exploitation Agent (Controlled testing with strict safety guardrails)
4. Reporting Agent (Automated ReportLab PDF & executive documentation)

Equipped with per-agent specialized model routing and cascading fallback chains.
"""

from __future__ import annotations

from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, TypedDict
import uuid

from langgraph.graph import StateGraph

from agents.exploitation_agent import ExploitationVerificationAgent
from agents.reporting_agent import ReportingAgent
from agents.vuln_analysis_agent import VulnerabilityAnalysisAgent
from config.settings import settings
from database.db import AsyncSessionLocal
from database.models import Report, Scan, SeverityEnum, Vulnerability
from security.events import is_scan_cancelled, publish_scan_event
from security.recon_tools import run_full_reconnaissance_native
from security.scope import ScopeDocument, ScopeTarget
from security.tool_runner import run_reconnaissance
from utils.llm_router import get_llm_router

logger = logging.getLogger(__name__)


class ScanState(TypedDict):
    """Workflow state passed through the LangGraph multi-agent pipeline."""
    scan_id: str
    target: str
    scope: str
    mode: str
    status: str
    llm_provider: str
    llm_model: str

    # Agent 1: Reconnaissance
    reconnaissance_results: Dict[str, Any]
    tool_results: List[Dict[str, Any]]

    # Agent 2: Vulnerability Analysis
    discovered_vulnerabilities: List[Dict[str, Any]]

    # Agent 3: Exploitation / Verification
    verified_vulnerabilities: List[Dict[str, Any]]
    exploitation_results: Dict[str, Any]

    # Agent 4: Reporting
    report_findings: Dict[str, Any]
    report_path: str

    # Metadata & Tracking
    start_time: str
    stage: str
    error: str
    models_used: Dict[str, str]


class SecurityAgentOrchestrator:
    """Coordinates the 4-agent security assessment workflow."""

    def __init__(self, db_session=None):
        self.db_session = db_session
        self.router = get_llm_router()
        self.vuln_agent = VulnerabilityAnalysisAgent()
        self.exploit_agent = ExploitationVerificationAgent()
        self.report_agent = ReportingAgent()
        self.graph = self._build_graph()

    def _build_graph(self) -> Any:
        """Construct the 4-agent LangGraph workflow."""
        graph = StateGraph(ScanState)

        # 4 Specialized Nodes
        graph.add_node("reconnaissance", self._reconnaissance_node)
        graph.add_node("vulnerability_analysis", self._vulnerability_analysis_node)
        graph.add_node("exploitation", self._exploitation_node)
        graph.add_node("reporting", self._reporting_node)

        # Sequential Pipeline Edges
        graph.add_edge("reconnaissance", "vulnerability_analysis")
        graph.add_edge("vulnerability_analysis", "exploitation")
        graph.add_edge("exploitation", "reporting")

        # Entry and Exit Points
        if hasattr(graph, "set_entry_point"):
            graph.set_entry_point("reconnaissance")
            graph.set_finish_point("reporting")
        else:
            from langgraph.graph import END, START
            graph.add_edge(START, "reconnaissance")
            graph.add_edge("reporting", END)

        return graph.compile()

    # ------------------------------------------------------------------
    # Agent 1: Reconnaissance
    # ------------------------------------------------------------------
    async def _reconnaissance_node(self, state: ScanState) -> ScanState:
        """Agent 1: OSINT, DNS resolution, port scanning, and HTTP security inspection."""
        scan_id = state["scan_id"]
        target = state["target"]
        logger.info(f"🔍 Agent 1 (Reconnaissance) starting on {target}")

        state["stage"] = "reconnaissance"
        await self._persist_progress(scan_id, "reconnaissance", 15.0)
        publish_scan_event(scan_id, "stage_started", stage="reconnaissance")

        if is_scan_cancelled(scan_id):
            state["status"] = "cancelled"
            return state

        try:
            # 1. Native OSINT & Network reconnaissance (DNS, Subdomains, Ports, HTTP)
            native_recon = await run_full_reconnaissance_native(target)
            state["reconnaissance_results"] = native_recon

            # 2. Scope-bounded external tools (nmap, curl if configured)
            try:
                scope_doc = ScopeDocument.model_validate_json(state["scope"])
                tool_results = await run_reconnaissance(scope_doc, scan_id)
                state["tool_results"] = tool_results
            except Exception as e:
                logger.warning(f"External tool execution skipped: {e}")
                state["tool_results"] = []

            # 3. AI synthesis of reconnaissance evidence
            prompt = f"""
Analyze the initial reconnaissance data for target {target}:
DNS: {native_recon.get('dns')}
OPEN PORTS: {native_recon.get('open_ports')}
HTTP HEADERS & SECURITY: {native_recon.get('http_security')}
Provide a concise overview of the external attack surface.
"""
            llm_res = await self.router.generate_for_agent(
                agent_name="reconnaissance",
                prompt=prompt,
                preferred_provider=state["llm_provider"],
                preferred_model=state["llm_model"],
            )
            state["models_used"]["reconnaissance"] = f"{llm_res.get('provider_used')}/{llm_res.get('model_used')}"

            await self._persist_progress(scan_id, "reconnaissance", 35.0)
            publish_scan_event(
                scan_id, "stage_finished", stage="reconnaissance",
                ports=len(native_recon.get("open_ports", [])),
                model=state["models_used"]["reconnaissance"],
            )
            logger.info(f"✅ Reconnaissance complete for {target}")

        except Exception as e:
            logger.error(f"❌ Reconnaissance node failed: {e}", exc_info=True)
            state["error"] = f"Reconnaissance error: {e}"

        return state

    # ------------------------------------------------------------------
    # Agent 2: Vulnerability Analysis
    # ------------------------------------------------------------------
    async def _vulnerability_analysis_node(self, state: ScanState) -> ScanState:
        """Agent 2: Deep CVE detection, OWASP Top-10 classification, and CVSS scoring."""
        scan_id = state["scan_id"]
        target = state["target"]
        logger.info(f"🧠 Agent 2 (Vulnerability Analysis) analyzing {target}")

        state["stage"] = "vulnerability_analysis"
        await self._persist_progress(scan_id, "vulnerability_analysis", 50.0)
        publish_scan_event(scan_id, "stage_started", stage="vulnerability_analysis")

        if is_scan_cancelled(scan_id):
            state["status"] = "cancelled"
            return state

        try:
            recon_data = state.get("reconnaissance_results", {})
            vulnerabilities = await self.vuln_agent.analyze(
                target=target,
                recon_data=recon_data,
                preferred_provider=state["llm_provider"],
                preferred_model=state["llm_model"],
            )
            state["discovered_vulnerabilities"] = vulnerabilities

            # Persist discovered vulnerabilities to DB
            await self._persist_vulnerabilities(scan_id, vulnerabilities)

            await self._persist_progress(scan_id, "vulnerability_analysis", 65.0)
            publish_scan_event(
                scan_id, "stage_finished", stage="vulnerability_analysis",
                vulnerabilities_found=len(vulnerabilities),
            )
            logger.info(f"✅ Vulnerability Analysis complete: {len(vulnerabilities)} findings identified")

        except Exception as e:
            logger.error(f"❌ Vulnerability Analysis failed: {e}", exc_info=True)
            state["error"] = f"Analysis error: {e}"

        return state

    # ------------------------------------------------------------------
    # Agent 3: Exploitation & Verification
    # ------------------------------------------------------------------
    async def _exploitation_node(self, state: ScanState) -> ScanState:
        """Agent 3: Controlled verification with safety guardrails and policy enforcement."""
        scan_id = state["scan_id"]
        target = state["target"]
        logger.info(f"⚔️ Agent 3 (Exploitation) executing verification on {target}")

        state["stage"] = "exploitation"
        await self._persist_progress(scan_id, "validation", 75.0)
        publish_scan_event(scan_id, "stage_started", stage="exploitation")

        if is_scan_cancelled(scan_id):
            state["status"] = "cancelled"
            return state

        try:
            scope_doc = ScopeDocument.model_validate_json(state["scope"])
            discovered = state.get("discovered_vulnerabilities", [])
            recon_data = state.get("reconnaissance_results", {})

            verification_result = await self.exploit_agent.verify_findings(
                scan_id=scan_id,
                target=target,
                scope_document=scope_doc,
                discovered_vulnerabilities=discovered,
                recon_data=recon_data,
                preferred_provider=state["llm_provider"],
                preferred_model=state["llm_model"],
            )

            state["exploitation_results"] = verification_result
            verified = verification_result.get("verified", [])
            state["verified_vulnerabilities"] = verified

            # Update verification flags in DB
            await self._update_verified_vulnerabilities(scan_id, verified)

            await self._persist_progress(scan_id, "validation", 85.0)
            publish_scan_event(
                scan_id, "stage_finished", stage="exploitation",
                verified_count=len(verified),
            )
            logger.info(f"✅ Exploitation verification complete: {len(verified)} findings verified")

        except Exception as e:
            logger.error(f"❌ Exploitation node failed: {e}", exc_info=True)
            state["error"] = f"Verification error: {e}"

        return state

    # ------------------------------------------------------------------
    # Agent 4: Reporting
    # ------------------------------------------------------------------
    async def _reporting_node(self, state: ScanState) -> ScanState:
        """Agent 4: Synthesize documentation, create PDF/HTML reports, and record in DB."""
        scan_id = state["scan_id"]
        target = state["target"]
        logger.info(f"📄 Agent 4 (Reporting) generating assessment report for {target}")

        state["stage"] = "reporting"
        await self._persist_progress(scan_id, "reporting", 90.0)
        publish_scan_event(scan_id, "stage_started", stage="reporting")

        if is_scan_cancelled(scan_id):
            state["status"] = "cancelled"
            return state

        try:
            report_id = str(uuid.uuid4())
            recon_data = state.get("reconnaissance_results", {})
            vulnerabilities = state.get("discovered_vulnerabilities", [])
            verified = state.get("verified_vulnerabilities", [])

            # Generate narrative
            narrative = await self.report_agent.generate_report_narrative(
                target=target,
                mode=state.get("mode", "safe"),
                recon_data=recon_data,
                vulnerabilities=vulnerabilities,
                preferred_provider=state["llm_provider"],
                preferred_model=state["llm_model"],
            )
            state["report_findings"] = narrative

            # Build official PDF report
            pdf_path = await self.report_agent.create_pdf_report(
                report_id=report_id,
                scan_id=scan_id,
                target=target,
                mode=state.get("mode", "safe"),
                vulnerabilities=vulnerabilities,
                narrative=narrative,
                recon_data=recon_data,
            )
            state["report_path"] = str(pdf_path)

            # Persist Report row into database
            await self._persist_report_db(
                report_id=report_id,
                scan_id=scan_id,
                target=target,
                pdf_path=str(pdf_path),
                narrative=narrative,
                vulnerabilities=vulnerabilities,
            )

            state["status"] = "completed"
            await self._persist_progress(scan_id, "completed", 100.0)
            publish_scan_event(
                scan_id, "stage_finished", stage="reporting",
                report_id=report_id, download=f"/api/reports/{report_id}/download"
            )
            logger.info(f"✅ Report generated successfully: {pdf_path}")

        except Exception as e:
            logger.error(f"❌ Reporting node failed: {e}", exc_info=True)
            state["error"] = f"Reporting error: {e}"
            state["status"] = "failed"

        return state

    # ------------------------------------------------------------------
    # Database Persistence Helpers
    # ------------------------------------------------------------------
    async def _persist_progress(self, scan_id: str, stage: str, progress: float) -> None:
        """Update scan progress percentage and stage."""
        try:
            from sqlalchemy import update
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(Scan).where(Scan.id == scan_id).values(
                        current_stage=stage,
                        progress_percentage=progress,
                    )
                )
                await session.commit()
        except Exception:
            logger.warning("Could not persist progress for %s", scan_id, exc_info=True)
        publish_scan_event(scan_id, "progress", stage=stage, progress=progress)

    async def _persist_vulnerabilities(self, scan_id: str, vulns: List[Dict[str, Any]]) -> None:
        """Persist discovered vulnerabilities into database table."""
        try:
            from sqlalchemy import update
            async with AsyncSessionLocal() as session:
                for v in vulns:
                    sev_str = str(v.get("severity", "medium")).lower()
                    sev_enum = getattr(SeverityEnum, sev_str.upper(), SeverityEnum.MEDIUM)

                    vuln_row = Vulnerability(
                        id=str(uuid.uuid4()),
                        scan_id=scan_id,
                        title=str(v.get("title", "Untitled finding")),
                        description=str(v.get("description", "")),
                        severity=sev_enum,
                        vulnerability_type=str(v.get("type", "misconfiguration")),
                        affected_endpoint=str(v.get("affected_endpoint", "")),
                        remediation=str(v.get("remediation", "")),
                        cvss_score=float(v.get("cvss_score", 5.0)),
                        verified=bool(v.get("verified", False)),
                    )
                    session.add(vuln_row)

                await session.execute(
                    update(Scan).where(Scan.id == scan_id).values(
                        vulnerabilities_found=len(vulns)
                    )
                )
                await session.commit()
                logger.info(f"Saved {len(vulns)} vulnerabilities to database for scan {scan_id}")
        except Exception as e:
            logger.warning(f"Could not persist vulnerabilities: {e}", exc_info=True)

    async def _update_verified_vulnerabilities(self, scan_id: str, verified_vulns: List[Dict[str, Any]]) -> None:
        """Update verified flags and safe PoC in database."""
        try:
            from sqlalchemy import select, update
            verified_titles = {v.get("title", "").lower(): v for v in verified_vulns}
            async with AsyncSessionLocal() as session:
                rows = (await session.execute(
                    select(Vulnerability).where(Vulnerability.scan_id == scan_id)
                )).scalars().all()

                for row in rows:
                    if row.title.lower() in verified_titles:
                        v_info = verified_titles[row.title.lower()]
                        row.verified = True
                        row.proof_of_concept = v_info.get("poc", "")
                await session.commit()
        except Exception as e:
            logger.warning(f"Could not update verified vulnerabilities: {e}", exc_info=True)

    async def _persist_report_db(
        self,
        report_id: str,
        scan_id: str,
        target: str,
        pdf_path: str,
        narrative: Dict[str, Any],
        vulnerabilities: List[Dict[str, Any]],
    ) -> None:
        """Insert Report row into DB."""
        try:
            counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
            for v in vulnerabilities:
                sev = str(v.get("severity", "low")).lower()
                if sev in counts:
                    counts[sev] += 1

            async with AsyncSessionLocal() as session:
                report = Report(
                    id=report_id,
                    scan_id=scan_id,
                    title=f"Security Assessment: {target}",
                    executive_summary=narrative.get("executive_summary", ""),
                    report_format="pdf",
                    report_path=pdf_path,
                    total_vulnerabilities=len(vulnerabilities),
                    critical_count=counts["critical"],
                    high_count=counts["high"],
                    medium_count=counts["medium"],
                    low_count=counts["low"],
                    overall_risk_score=float(narrative.get("overall_risk_score", 0.0)),
                )
                session.add(report)

                from sqlalchemy import update
                await session.execute(
                    update(Scan).where(Scan.id == scan_id).values(
                        report_generated=True,
                        report_path=pdf_path,
                    )
                )
                await session.commit()
        except Exception as e:
            logger.warning(f"Could not save Report to DB: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # Orchestrator Entrypoint
    # ------------------------------------------------------------------
    async def execute_scan(
        self,
        scan_id: str,
        target: str,
        scope: str,
        mode: str,
        llm_provider: str,
        llm_model: str,
    ) -> ScanState:
        """Execute the complete multi-agent assessment workflow."""
        if not scope:
            scope = ScopeDocument(targets=[ScopeTarget(host=target)]).model_dump_json()

        initial_state: ScanState = {
            "scan_id": scan_id,
            "target": target,
            "scope": scope,
            "mode": mode,
            "status": "running",
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "reconnaissance_results": {},
            "tool_results": [],
            "discovered_vulnerabilities": [],
            "verified_vulnerabilities": [],
            "exploitation_results": {},
            "report_path": "",
            "report_findings": {},
            "start_time": datetime.utcnow().isoformat(),
            "stage": "initializing",
            "error": "",
            "models_used": {},
        }

        logger.info(f"🚀 Launching multi-agent scan {scan_id} on {target}")
        result = await self.graph.ainvoke(initial_state)
        return result


# Singleton instance
_orchestrator: SecurityAgentOrchestrator | None = None

def get_orchestrator(db_session=None) -> SecurityAgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SecurityAgentOrchestrator(db_session)
    return _orchestrator
