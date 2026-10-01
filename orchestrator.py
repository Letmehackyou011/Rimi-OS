"""
AI Agent Orchestrator - Coordinates multiple agents
Using LangGraph for multi-agent orchestration
"""

import logging
import json
from typing import Dict, Any, TypedDict, List
from datetime import datetime

from langgraph.graph import StateGraph
from utils.llm_client import get_llm_client
from database.models import Scan, Vulnerability, Report, SeverityEnum
from security.events import is_scan_cancelled, publish_scan_event
from security.scope import ScopeDocument, ScopeTarget
from security.tool_runner import run_reconnaissance

logger = logging.getLogger(__name__)

class ScanState(TypedDict):
    """State for the scanning workflow"""
    scan_id: str
    target: str
    scope: str
    mode: str
    status: str
    llm_provider: str
    llm_model: str
    
    # Reconnaissance results
    reconnaissance_results: Dict[str, Any]
    tool_results: List[Dict[str, Any]]
    discovered_vulnerabilities: List[Dict[str, Any]]
    
    # Exploitation results
    exploitation_results: Dict[str, Any]
    verified_vulnerabilities: List[Dict[str, Any]]
    
    # Reporting results
    report_path: str
    report_findings: Dict[str, Any]
    
    # Metadata
    start_time: str
    stage: str
    error: str

class SecurityAgentOrchestrator:
    """Orchestrates security scanning agents"""
    
    def __init__(self, db_session=None):
        self.db_session = db_session
        self._llm_clients = {}
        self.graph = self._build_graph()

    def _client_for_state(self, state: ScanState):
        """Resolve and cache the LangChain model selected for this scan."""
        key = (state["llm_provider"], state["llm_model"])
        if key not in self._llm_clients:
            self._llm_clients[key] = get_llm_client(*key)
        return self._llm_clients[key]
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        graph = StateGraph(ScanState)
        
        # Add nodes
        graph.add_node("reconnaissance", self._reconnaissance_agent)
        graph.add_node("exploitation", self._exploitation_agent)
        graph.add_node("reporting", self._reporting_agent)
        
        # Add edges
        graph.add_edge("reconnaissance", "exploitation")
        graph.add_edge("exploitation", "reporting")
        
        # Set entry point
        graph.set_entry_point("reconnaissance")
        
        # Set finish point
        graph.set_finish_point("reporting")
        
        return graph.compile()
    
    async def _reconnaissance_agent(self, state: ScanState) -> ScanState:
        """
        Reconnaissance Agent
        - Scans target for vulnerabilities
        - Uses LLM to analyze findings
        """
        logger.info(f"🔍 Starting reconnaissance on {state['target']}")
        state['stage'] = 'reconnaissance'
        await self._persist_progress(state['scan_id'], 'reconnaissance', 10.0)
        if is_scan_cancelled(state['scan_id']):
            state['status'] = 'cancelled'
            return state
        publish_scan_event(state['scan_id'], "stage_started", stage="reconnaissance")
        
        try:
            scope_document = ScopeDocument.model_validate_json(state['scope'])
            tool_results = await run_reconnaissance(scope_document, state['scan_id'])
            state['tool_results'] = tool_results
            # Build reconnaissance prompt
            prompt = self._build_recon_prompt(state, tool_results)
            
            # Get LLM response
            response = await self._client_for_state(state).generate(prompt)
            
            # Parse findings
            findings = self._parse_findings(response)
            
            state['reconnaissance_results'] = {
                "summary": findings,
                "timestamp": datetime.utcnow().isoformat(),
                "vulnerabilities_found": len(findings.get('vulnerabilities', []))
            }
            
            state['discovered_vulnerabilities'] = findings.get('vulnerabilities', [])
            await self._persist_progress(state['scan_id'], 'reconnaissance', 35.0)
            
            logger.info(f"✅ Reconnaissance complete: {len(state['discovered_vulnerabilities'])} vulnerabilities found")
            publish_scan_event(
                state['scan_id'],
                "stage_finished",
                stage="reconnaissance",
                vulnerabilities=len(state['discovered_vulnerabilities']),
            )
            
        except Exception as e:
            logger.error(f"❌ Reconnaissance failed: {str(e)}")
            state['error'] = f"Reconnaissance error: {str(e)}"
            state['status'] = "failed"
            publish_scan_event(state['scan_id'], "stage_failed", stage="reconnaissance", error=str(e))
        
        return state
    
    async def _exploitation_agent(self, state: ScanState) -> ScanState:
        """
        Exploitation Agent
        - Tests discovered vulnerabilities
        - Verifies security issues
        """
        logger.info("⚔️ Starting exploitation verification")
        state['stage'] = 'exploitation'
        await self._persist_progress(state['scan_id'], 'validation', 45.0)
        if is_scan_cancelled(state['scan_id']):
            state['status'] = 'cancelled'
            return state
        publish_scan_event(state['scan_id'], "stage_started", stage="verification")
        
        try:
            if not state['discovered_vulnerabilities']:
                logger.info("No vulnerabilities to exploit")
                state['exploitation_results'] = {"verified": [], "failed": []}
                return state
            
            verified = []
            failed = []
            
            # Test each vulnerability
            for vuln in state['discovered_vulnerabilities'][:5]:  # Limit to 5 for demo
                if is_scan_cancelled(state['scan_id']):
                    state['status'] = 'cancelled'
                    return state
                prompt = self._build_exploitation_prompt(state, vuln)
                
                try:
                    response = await self._client_for_state(state).generate(prompt)
                    verification = self._parse_verification(response)
                    
                    if verification.get('verified', False):
                        verified.append(vuln)
                    else:
                        failed.append(vuln)
                
                except Exception as e:
                    logger.warning(f"Failed to verify {vuln.get('title')}: {str(e)}")
                    failed.append(vuln)
            
            state['exploitation_results'] = {
                "verified_count": len(verified),
                "failed_count": len(failed),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            state['verified_vulnerabilities'] = verified
            await self._persist_progress(state['scan_id'], 'validation', 65.0)
            
            logger.info(f"✅ Exploitation complete: {len(verified)} verified")
            publish_scan_event(state['scan_id'], "stage_finished", stage="verification", verified=len(verified))
            
        except Exception as e:
            logger.error(f"❌ Exploitation failed: {str(e)}")
            state['error'] = f"Exploitation error: {str(e)}"
            state['status'] = "failed"
        
        return state
    
    async def _reporting_agent(self, state: ScanState) -> ScanState:
        """
        Reporting Agent
        - Generates comprehensive security report
        """
        logger.info("📄 Generating security report")
        state['stage'] = 'reporting'
        await self._persist_progress(state['scan_id'], 'reporting', 80.0)
        if is_scan_cancelled(state['scan_id']):
            state['status'] = 'cancelled'
            return state
        publish_scan_event(state['scan_id'], "stage_started", stage="reporting")
        
        try:
            # Build report prompt
            prompt = self._build_report_prompt(state)
            
            # Generate report
            response = await self._client_for_state(state).generate(prompt)
            
            report_data = self._parse_report(response, state)
            
            state['report_findings'] = report_data
            state['report_path'] = f"reports/{state['scan_id']}.pdf"
            state['status'] = "completed"
            await self._persist_progress(state['scan_id'], 'completed', 100.0)
            
            logger.info(f"✅ Report generated successfully")
            publish_scan_event(state['scan_id'], "stage_finished", stage="reporting")
            
        except Exception as e:
            logger.error(f"❌ Report generation failed: {str(e)}")
            state['error'] = f"Reporting error: {str(e)}"
            state['status'] = "failed"
        
        return state

    async def _persist_progress(self, scan_id: str, stage: str, progress: float) -> None:
        """Persist stage checkpoints so clients see real execution progress."""
        try:
            from sqlalchemy import update
            from database.db import AsyncSessionLocal
            from database.models import Scan

            async with AsyncSessionLocal() as session:
                await session.execute(update(Scan).where(Scan.id == scan_id).values(
                    current_stage=stage,
                    progress_percentage=progress,
                ))
                await session.commit()
        except Exception:
            logger.warning("Could not persist progress for scan %s", scan_id, exc_info=True)
        publish_scan_event(scan_id, 'progress', stage=stage, progress=progress)
    
    def _build_recon_prompt(self, state: ScanState, tool_results: List[Dict[str, Any]]) -> str:
        """Build reconnaissance prompt"""
        return f"""
        You are a security researcher. Perform reconnaissance on the following target:
        
        Target: {state['target']}
        Scope: {state['scope']}
        Mode: {state['mode']}
        
        Analyze only the supplied reconnaissance evidence. Do not invent services or claim exploitation.
        Identify potential vulnerabilities and security issues.
        Tool evidence:
        {json.dumps(tool_results, indent=2)}
        Return a JSON response with:
        {{
            "summary": "brief summary",
            "vulnerabilities": [
                {{
                    "title": "vulnerability name",
                    "type": "type (sql_injection, xss, etc)",
                    "severity": "critical|high|medium|low",
                    "description": "detailed description",
                    "affected_endpoint": "endpoint if applicable"
                }}
            ]
        }}
        """
    
    def _build_exploitation_prompt(self, state: ScanState, vuln: Dict) -> str:
        """Build exploitation verification prompt"""
        return f"""
        Verification task: assess whether this finding is supported by the collected evidence. Do not execute exploitation,
        credential attacks, payloads, persistence, or proof-of-concept commands:
        
        Target: {state['target']}
        Vulnerability: {vuln.get('title')}
        Type: {vuln.get('type')}
        Description: {vuln.get('description')}
        
        Provide a JSON response with:
        {{
            "verified": true/false,
            "proof_of_concept": "PoC if possible",
            "risk_level": "high/medium/low",
            "notes": "additional notes"
        }}
        """
    
    def _build_report_prompt(self, state: ScanState) -> str:
        """Build report generation prompt"""
        verified_count = len(state.get('verified_vulnerabilities', []))
        total_count = len(state.get('discovered_vulnerabilities', []))
        
        return f"""
        Generate a professional security assessment report:
        
        Target: {state['target']}
        Vulnerabilities Discovered: {total_count}
        Vulnerabilities Verified: {verified_count}
        Mode: {state['mode']}
        
        Provide a detailed security report with:
        - Executive Summary
        - Vulnerability Details
        - Risk Assessment
        - Remediation Recommendations
        
        Return as JSON with these fields:
        {{
            "executive_summary": "summary",
            "vulnerability_count": {verified_count},
            "overall_risk_score": 0-10,
            "recommendations": ["recommendation 1", "recommendation 2"],
            "next_steps": "recommended next steps"
        }}
        """
    
    def _parse_findings(self, response: str) -> Dict[str, Any]:
        """Parse LLM response for findings"""
        try:
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"vulnerabilities": []}
        except Exception as e:
            logger.warning(f"Failed to parse findings: {str(e)}")
            return {"vulnerabilities": []}
    
    def _parse_verification(self, response: str) -> Dict[str, Any]:
        """Parse verification response"""
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"verified": False}
        except Exception as e:
            logger.warning(f"Failed to parse verification: {str(e)}")
            return {"verified": False}
    
    def _parse_report(self, response: str, state: ScanState) -> Dict[str, Any]:
        """Parse report response"""
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {
                "executive_summary": "Report generated",
                "vulnerability_count": len(state['verified_vulnerabilities']),
                "overall_risk_score": 5.0
            }
        except Exception as e:
            logger.warning(f"Failed to parse report: {str(e)}")
            return {}
    
    async def execute_scan(self, scan_id: str, target: str, scope: str, mode: str, 
                          llm_provider: str, llm_model: str) -> ScanState:
        """Execute complete scan workflow"""
        if not scope:
            scope = ScopeDocument(
                targets=[ScopeTarget(host=target)],
            ).model_dump_json()

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
            "exploitation_results": {},
            "verified_vulnerabilities": [],
            "report_path": "",
            "report_findings": {},
            "start_time": datetime.utcnow().isoformat(),
            "stage": "initializing",
            "error": ""
        }
        
        logger.info(f"🚀 Starting scan {scan_id} on {target}")
        
        # Execute workflow
        result = await self.graph.ainvoke(initial_state)
        
        return result

# Global orchestrator instance
_orchestrator: SecurityAgentOrchestrator = None

def get_orchestrator(db_session=None) -> SecurityAgentOrchestrator:
    """Get or create orchestrator"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SecurityAgentOrchestrator(db_session)
    return _orchestrator
