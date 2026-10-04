"""
Vulnerability Analysis Agent
Performs deep CVE matching, OWASP Top-10 classification, CVSS scoring,
and security misconfiguration identification using specialized LLM reasoning and rule engine.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

from utils.llm_router import get_llm_router

logger = logging.getLogger(__name__)

# Fallback rule-based findings when LLM is offline or template is used
RULE_BASED_CHECKS = {
    "Strict-Transport-Security": {
        "title": "Missing Strict-Transport-Security (HSTS) Header",
        "type": "misconfiguration",
        "severity": "medium",
        "owasp": "A02:2021-Cryptographic Failures",
        "description": "The web application does not enforce HTTPS connections using the Strict-Transport-Security header. Attackers on the same network may intercept or downgrade traffic to cleartext HTTP.",
        "remediation": "Add the 'Strict-Transport-Security: max-age=31536000; includeSubDomains; preload' header to all HTTPS responses.",
    },
    "X-Frame-Options": {
        "title": "Missing Anti-Clickjacking Header (X-Frame-Options)",
        "type": "clickjacking",
        "severity": "medium",
        "owasp": "A05:2021-Security Misconfiguration",
        "description": "The application does not include an X-Frame-Options or Content-Security-Policy frame-ancestors directive. This leaves the site susceptible to clickjacking attacks within an iframe.",
        "remediation": "Configure 'X-Frame-Options: DENY' or 'Content-Security-Policy: frame-ancestors 'none';'.",
    },
    "X-Content-Type-Options": {
        "title": "Missing MIME Sniffing Protection (X-Content-Type-Options)",
        "type": "misconfiguration",
        "severity": "low",
        "owasp": "A05:2021-Security Misconfiguration",
        "description": "The application omits the X-Content-Type-Options: nosniff header, which can cause browsers to misinterpret file content types and execute unauthorized scripts.",
        "remediation": "Set 'X-Content-Type-Options: nosniff' across all HTTP responses.",
    },
    "Referrer-Policy": {
        "title": "Missing Referrer-Policy Header",
        "type": "information_disclosure",
        "severity": "low",
        "owasp": "A01:2021-Broken Access Control",
        "description": "Without a Referrer-Policy header, sensitive request parameters in the URL may be leaked to external sites via the Referer header.",
        "remediation": "Configure 'Referrer-Policy: strict-origin-when-cross-origin'.",
    },
}


class VulnerabilityAnalysisAgent:
    """Specialized AI agent for vulnerability detection and CVSS/OWASP classification."""

    def __init__(self):
        self.router = get_llm_router()

    async def analyze(
        self,
        target: str,
        recon_data: Dict[str, Any],
        preferred_provider: str | None = None,
        preferred_model: str | None = None,
    ) -> List[Dict[str, Any]]:
        """Analyze reconnaissance evidence and return structured vulnerability findings."""
        logger.info(f"🧠 Vulnerability Analysis Agent evaluating target: {target}")

        http_sec = recon_data.get("http_security", {})
        open_ports = recon_data.get("open_ports", [])
        missing_headers = http_sec.get("missing_security_headers", [])
        server_banner = http_sec.get("server")

        prompt = f"""
You are an expert security analyst specializing in vulnerability assessment, OWASP Top-10, and CVSS scoring.
Analyze the following reconnaissance evidence collected from target {target}:

TARGET: {target}
RESOLVED IP: {recon_data.get('dns', {}).get('ip_addresses', [])}
OPEN PORTS: {json.dumps(open_ports)}
SERVER BANNER: {server_banner}
DETECTED TECHNOLOGIES: {http_sec.get('technologies', [])}
MISSING SECURITY HEADERS: {missing_headers}
PRESENT SECURITY HEADERS: {http_sec.get('present_security_headers', {})}

Identify genuine security vulnerabilities, misconfigurations, and exposure risks supported strictly by this evidence.
Do not invent fictional exploits or SQL injections if no database evidence exists.

Return ONLY a valid JSON object matching this schema:
{{
    "vulnerabilities": [
        {{
            "title": "Concise title",
            "type": "misconfiguration|information_disclosure|transport_security|service_exposure",
            "severity": "critical|high|medium|low|info",
            "cvss_score": 5.4,
            "owasp_category": "A05:2021-Security Misconfiguration",
            "description": "Detailed explanation of the flaw and attack vector",
            "affected_endpoint": "{target}",
            "remediation": "Clear actionable remediation advice"
        }}
    ]
}}
"""
        result = await self.router.generate_for_agent(
            agent_name="vulnerability_analysis",
            prompt=prompt,
            preferred_provider=preferred_provider,
            preferred_model=preferred_model,
        )

        content = result.get("content", "")
        vulnerabilities = self._parse_vulnerabilities(content)

        # Rule engine augmentation: ensure detected missing headers are recorded if LLM missed them
        existing_titles = {v.get("title", "").lower() for v in vulnerabilities}
        for missing in missing_headers:
            if missing in RULE_BASED_CHECKS:
                rule = RULE_BASED_CHECKS[missing]
                if rule["title"].lower() not in existing_titles:
                    vulnerabilities.append({
                        "title": rule["title"],
                        "type": rule["type"],
                        "severity": rule["severity"],
                        "cvss_score": 5.3 if rule["severity"] == "medium" else 3.1,
                        "owasp_category": rule["owasp"],
                        "description": rule["description"],
                        "affected_endpoint": target,
                        "remediation": rule["remediation"],
                    })

        # Cleartext HTTP check
        if any(p.get("port") == 80 for p in open_ports) and not any("port 80" in v.get("title", "").lower() for v in vulnerabilities):
            vulnerabilities.append({
                "title": "Cleartext HTTP Service Exposed (Port 80)",
                "type": "transport_security",
                "severity": "medium",
                "cvss_score": 5.3,
                "owasp_category": "A02:2021-Cryptographic Failures",
                "description": "Port 80 (HTTP) is open. If unencrypted HTTP traffic is accepted without immediate redirection to HTTPS, sensitive data can be eavesdropped.",
                "affected_endpoint": f"{target}:80",
                "remediation": "Implement an unconditional 301 Permanent Redirect from HTTP to HTTPS for all requests.",
            })

        logger.info(f"🧠 Vulnerability Analysis Agent identified {len(vulnerabilities)} vulnerabilities (Model used: {result.get('provider_used')}/{result.get('model_used')})")
        return vulnerabilities

    def _parse_vulnerabilities(self, raw_text: str) -> List[Dict[str, Any]]:
        """Safely extract JSON array of vulnerabilities from LLM output."""
        try:
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return data.get("vulnerabilities", [])
        except Exception as e:
            logger.warning(f"Could not parse LLM vulnerability response: {e}")
        return []
