import pytest

from orchestrator import SecurityAgentOrchestrator


class FakeLLM:
    async def generate(self, prompt: str) -> str:
        if "Verification task" in prompt:
            return '{"verified": true}'
        if "Generate a professional" not in prompt:
            return '{"vulnerabilities": [{"title": "Test finding", "type": "xss", "severity": "low", "description": "test"}]}'
        return '{"executive_summary": "ok", "vulnerability_count": 1, "overall_risk_score": 2.0}'


@pytest.mark.asyncio
async def test_scan_graph_runs_all_agents():
    orchestrator = SecurityAgentOrchestrator()
    orchestrator._client_for_state = lambda state: FakeLLM()

    result = await orchestrator.execute_scan(
        scan_id="test-scan",
        target="example.com",
        scope="",
        mode="normal",
        llm_provider="ollama",
        llm_model="mistral",
    )

    assert result["status"] == "completed"
    assert len(result["discovered_vulnerabilities"]) == 1
    assert len(result["verified_vulnerabilities"]) == 1
    assert result["report_findings"]["overall_risk_score"] == 2.0
