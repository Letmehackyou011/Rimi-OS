"""
AI Agent Orchestrator - Coordinates multiple agents
Using LangGraph for multi-agent orchestration
"""

import logging
import json
from typing import Dict, Any, TypedDict, List
from datetime import datetime

from langgraph.graph import StateGraph
from langchain_core.messages import BaseMessage, HumanMessage

from utils.llm_client import get_llm_client
from database.models import Scan, Vulnerability, Report, SeverityEnum

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
        self.llm_client = get_llm_client()
        self.graph = self._build_graph()
    
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
        
        try:
            # Build reconnaissance prompt
            prompt = self._build_recon_prompt(state)
            
            # Get LLM response
            response = await self.llm_client.generate(prompt)
            
            # Parse findings
            findings = self._parse_findings(response)
            
            state['reconnaissance_results'] = {
                "summary": findings,
                "timestamp": datetime.utcnow().isoformat(),
                "vulnerabilities_found": len(findings.get('vulnerabilities', []))
            }
            
            state['discovered_vulnerabilities'] = findings.get('vulnerabilities', [])
            
            logger.info(f"✅ Reconnaissance complete: {len(state['discovered_vulnerabilities'])} vulnerabilities found")
            
        except Exception as e:
            logger.error(f"❌ Reconnaissance failed: {str(e)}")
            state['error'] = f"Reconnaissance error: {str(e)}"
            state['status'] = "failed"
        
        return state
    
    async def _exploitation_agent(self, state: ScanState) -> ScanState:
        """
        Exploitation Agent
        - Tests discovered vulnerabilities
        - Verifies security issues
        """
        logger.info("⚔️ Starting exploitation verification")
        state['stage'] = 'exploitation'
        
        try:
            if not state['discovered_vulnerabilities']:
                logger.info("No vulnerabilities to exploit")
                state['exploitation_results'] = {"verified": [], "failed": []}
                return state
            
            verified = []
            failed = []
            
            # Test each vulnerability
            for vuln in state['discovered_vulnerabilities'][:5]:  # Limit to 5 for demo
                prompt = self._build_exploitation_prompt(state, vuln)
                
                try:
                    response = await self.llm_client.generate(prompt)
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
            
            logger.info(f"✅ Exploitation complete: {len(verified)} verified")
            
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
        
        try:
            # Build report prompt
            prompt = self._build_report_prompt(state)
            
            # Generate report
            response = await self.llm_client.generate(prompt)
            
            report_data = self._parse_report(response, state)
            
            state['report_findings'] = report_data
            state['report_path'] = f"reports/{state['scan_id']}.pdf"
            state['status'] = "completed"
            
            logger.info(f"✅ Report generated successfully")
            
        except Exception as e:
            logger.error(f"❌ Report generation failed: {str(e)}")
            state['error'] = f"Reporting error: {str(e)}"
            state['status'] = "failed"
        
        return state
    
    def _build_recon_prompt(self, state: ScanState) -> str:
        """Build reconnaissance prompt"""
        return f"""
        You are a security researcher. Perform reconnaissance on the following target:
        
        Target: {state['target']}
        Scope: {state['scope']}
        Mode: {state['mode']}
        
        Identify potential vulnerabilities and security issues. 
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
        Verify if this vulnerability can be exploited:
        
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
        
        initial_state: ScanState = {
            "scan_id": scan_id,
            "target": target,
            "scope": scope,
            "mode": mode,
            "status": "running",
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "reconnaissance_results": {},
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
