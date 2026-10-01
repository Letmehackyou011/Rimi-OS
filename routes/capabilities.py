"""Discoverable agent skills and controlled tool capabilities."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/agents")
async def list_agents() -> dict:
    return {
        "execution": "LangGraph stateful pipeline",
        "agents": [
            {"name": "reconnaissance", "status": "enabled", "role": "collect scoped evidence"},
            {"name": "scanning", "status": "enabled", "role": "operate allowlisted scanners"},
            {"name": "validation", "status": "enabled", "role": "validate evidence without exploitation"},
            {"name": "reporting", "status": "enabled", "role": "write structured reports and PDFs"},
            {"name": "monitoring", "status": "limited", "role": "publish live stage/tool events"},
            {"name": "exploitation", "status": "human_review", "role": "no unattended exploit execution"},
        ],
    }


@router.get("/skills")
async def list_skills() -> dict:
    return {
        "skills": [
            {"name": "reconnaissance", "status": "enabled", "description": "Scoped host and HTTP evidence collection"},
            {"name": "scanning", "status": "enabled", "description": "Allowlisted nmap/curl/tcpdump execution"},
            {"name": "validation", "status": "enabled", "description": "Evidence-backed finding validation without exploit execution"},
            {"name": "reporting", "status": "enabled", "description": "Structured JSON and PDF report generation"},
            {"name": "monitoring", "status": "limited", "description": "In-process scan event telemetry"},
            {"name": "exploitation", "status": "review_required", "description": "No unattended exploit or credential attack execution"},
        ]
    }


@router.get("/tools")
async def list_tools() -> dict:
    return {
        "tools": [
            {"name": "nmap", "status": "enabled", "mode": "safe", "description": "Bounded TCP-connect reconnaissance"},
            {"name": "curl", "status": "enabled", "mode": "safe", "description": "Bounded HTTP/HTTPS header checks"},
            {"name": "tcpdump", "status": "guarded", "mode": "guarded", "description": "Bounded packet capture on POSIX systems"},
            {"name": "burpsuite", "status": "review_required", "mode": "human_review", "description": "Proxy workflows require explicit operator approval"},
            {"name": "sqlmap", "status": "review_required", "mode": "human_review", "description": "Active injection testing is not unattended"},
            {"name": "metasploit", "status": "disabled", "mode": "human_review", "description": "No remote exploit execution"},
            {"name": "hydra/hashcat/john", "status": "disabled", "mode": "human_review", "description": "No credential attack automation"},
        ]
    }
