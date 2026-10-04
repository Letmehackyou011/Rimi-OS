"""
Scanning Routes - Handle scan operations
"""

import logging
import uuid
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import AsyncSessionLocal, get_db
from database.models import Scan, ScanStatusEnum, Vulnerability
from agents.orchestrator import get_orchestrator
from config.settings import settings
from security.events import get_scan_events, mark_scan_cancelled, publish_scan_event
from security.scope import ScopeDocument, SecurityMode, scope_from_request

logger = logging.getLogger(__name__)
router = APIRouter()
_cancelled_scans: set[str] = set()
_scheduled_scans: dict[str, dict] = {}

class ScanRequest(BaseModel):
    """Scan request model"""
    target: str
    scope: ScopeDocument | str | None = None
    mode: SecurityMode = SecurityMode.SAFE
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None

class ScanResponse(BaseModel):
    """Scan response model"""
    scan_id: str
    target: str
    status: str
    created_at: str
    message: str

class ScanStatusResponse(BaseModel):
    """Scan status response"""
    scan_id: str
    target: str
    status: str
    stage: str
    progress_percentage: float
    vulnerabilities_found: int
    error: Optional[str] = None

class ScanResultsResponse(BaseModel):
    """Scan results response"""
    scan_id: str
    target: str
    status: str
    vulnerabilities: list
    recommendations: list
    risk_score: float
    error: Optional[str] = None


class ApprovalRequest(BaseModel):
    approval_token: str


class ScheduleRequest(BaseModel):
    run_at: datetime

@router.post("/start", response_model=ScanResponse)
async def start_scan(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Start a new security scan
    
    Parameters:
    - target: Target URL or IP address
    - scope: Optional scope specification
    - mode: Testing mode (normal/aggressive/stealth)
    - llm_provider: LLM provider to use (optional, uses default)
    - llm_model: Specific model to use (optional)
    """
    
    try:
        # Generate scan ID
        scan_id = str(uuid.uuid4())
        
        # Validate target
        if not request.target:
            raise HTTPException(status_code=400, detail="Target cannot be empty")
        
        try:
            scope_document = scope_from_request(request.target, request.scope, request.mode.value)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid authorization scope: {exc}") from exc

        # Use default LLM settings if not provided
        llm_provider = request.llm_provider or settings.ACTIVE_LLM
        llm_model = request.llm_model or settings.OLLAMA_MODEL
        awaiting_review = scope_document.mode == SecurityMode.HUMAN_REVIEW and not scope_document.approval_token
        
        # Create scan record
        scan = Scan(
            id=scan_id,
            target=request.target,
            scope=scope_document.model_dump_json(),
            mode=scope_document.mode.value,
            status=ScanStatusEnum.AWAITING_REVIEW if awaiting_review else ScanStatusEnum.PENDING,
            llm_provider=llm_provider,
            llm_model=llm_model,
            progress_percentage=0.0,
            current_stage="pending"
        )
        
        db.add(scan)
        await db.commit()
        
        logger.info(f"📌 Scan {scan_id} created for {request.target}")
        
        if awaiting_review:
            publish_scan_event(scan_id, "awaiting_human_review", target=request.target)
        else:
            background_tasks.add_task(
                _execute_scan_background,
                scan_id=scan_id,
                target=request.target,
                scope=scope_document.model_dump_json(),
                mode=scope_document.mode.value,
                llm_provider=llm_provider,
                llm_model=llm_model,
            )
        
        return ScanResponse(
            scan_id=scan_id,
            target=request.target,
            status="pending",
            created_at=scan.created_at.isoformat(),
            message="Scan is awaiting human approval" if awaiting_review else "Scan queued and will start shortly"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting scan: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start scan")

@router.get("/{scan_id}/status", response_model=ScanStatusResponse)
async def get_scan_status(
    scan_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get status of a running or completed scan
    """
    try:
        from sqlalchemy import select
        
        result = await db.execute(select(Scan).where(Scan.id == scan_id))
        scan = result.scalar_one_or_none()
        
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        return ScanStatusResponse(
            scan_id=scan.id,
            target=scan.target,
            status=scan.status.value if scan.status else "unknown",
            stage=scan.current_stage or "pending",
            progress_percentage=scan.progress_percentage,
            vulnerabilities_found=scan.vulnerabilities_found,
            error=scan.error_message
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting scan status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get scan status")

@router.get("/{scan_id}/results", response_model=ScanResultsResponse)
async def get_scan_results(
    scan_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get results of a scan.
    Returns results for completed scans, or current findings/error for in-progress and failed scans.
    """
    try:
        from sqlalchemy import select
        
        result = await db.execute(select(Scan).where(Scan.id == scan_id))
        scan = result.scalar_one_or_none()
        
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        # Get vulnerabilities (will return whatever has been discovered so far)
        vulns_result = await db.execute(
            select(Vulnerability).where(Vulnerability.scan_id == scan_id)
        )
        vulnerabilities = vulns_result.scalars().all()

        # Parse recommendations from findings_json if present
        recommendations = [
            "Review and patch vulnerabilities by severity",
            "Implement Web Application Firewall (WAF)",
            "Regular security assessments recommended"
        ]
        if scan.findings_json and isinstance(scan.findings_json, dict):
            recommendations = scan.findings_json.get("recommendations", recommendations)
        
        # Calculate comprehensive risk score based on severity weights
        crit = sum(1 for v in vulnerabilities if getattr(v.severity, "value", v.severity) == "critical")
        high = sum(1 for v in vulnerabilities if getattr(v.severity, "value", v.severity) == "high")
        med = sum(1 for v in vulnerabilities if getattr(v.severity, "value", v.severity) == "medium")
        low = sum(1 for v in vulnerabilities if getattr(v.severity, "value", v.severity) == "low")
        risk_score = min(10.0, round(crit * 3.5 + high * 2.5 + med * 1.5 + low * 0.5, 1))

        return ScanResultsResponse(
            scan_id=scan.id,
            target=scan.target,
            status=scan.status.value if scan.status else "unknown",
            vulnerabilities=[
                {
                    "id": v.id,
                    "title": v.title,
                    "severity": v.severity.value if hasattr(v.severity, "value") else str(v.severity or "unknown"),
                    "type": v.vulnerability_type,
                    "description": v.description,
                    "affected_endpoint": v.affected_endpoint,
                    "verified": v.verified,
                }
                for v in vulnerabilities
            ],
            recommendations=recommendations,
            risk_score=risk_score,
            error=scan.error_message
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting scan results: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get scan results")

@router.post("/{scan_id}/cancel")
async def cancel_scan(
    scan_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel a running scan
    """
    try:
        from sqlalchemy import select
        
        result = await db.execute(select(Scan).where(Scan.id == scan_id))
        scan = result.scalar_one_or_none()
        
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        if scan.status in [ScanStatusEnum.COMPLETED, ScanStatusEnum.FAILED]:
            raise HTTPException(status_code=400, detail="Cannot cancel completed scan")
        
        mark_scan_cancelled(scan_id)
        _cancelled_scans.add(scan_id)
        scan.status = ScanStatusEnum.CANCELLED
        await db.commit()
        
        logger.info(f"Scan {scan_id} cancelled")
        return {"message": "Scan cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling scan: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cancel scan")


class ExploitRequest(BaseModel):
    mode: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None


@router.post("/{scan_id}/exploit")
async def run_exploitation(
    scan_id: str,
    request: ExploitRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    On-demand Exploitation Agent execution for a scan.
    Verifies vulnerabilities with the assigned AI model (e.g. Gemini, OpenAI, Claude, Ollama)
    and attaches proof-of-concept evidence.
    """
    from sqlalchemy import select
    from agents.exploitation_agent import ExploitationVerificationAgent
    from security.scope import ScopeDocument, ScopeTarget

    scan_res = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = scan_res.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    vulns_res = await db.execute(select(Vulnerability).where(Vulnerability.scan_id == scan_id))
    vulns = list(vulns_res.scalars().all())

    if not vulns:
        return {
            "scan_id": scan_id,
            "status": "no_findings",
            "message": "No vulnerabilities recorded to exploit or verify.",
            "verified_count": 0,
        }

    vuln_dicts = [
        {
            "id": v.id,
            "title": v.title,
            "type": v.vulnerability_type,
            "description": v.description,
            "severity": v.severity.value if v.severity else "medium",
            "affected_endpoint": v.affected_endpoint or scan.target,
        }
        for v in vulns
    ]

    try:
        scope_doc = ScopeDocument.model_validate_json(scan.scope or "{}")
    except Exception:
        scope_doc = ScopeDocument(targets=[ScopeTarget(host=scan.target)])

    exploit_agent = ExploitationVerificationAgent()
    provider = (request.llm_provider if request else None) or scan.llm_provider or settings.ACTIVE_LLM
    model = (request.llm_model if request else None) or scan.llm_model

    verification_result = await exploit_agent.verify_findings(
        scan_id=scan_id,
        target=scan.target,
        scope_document=scope_doc,
        discovered_vulnerabilities=vuln_dicts,
        recon_data={"open_ports": [], "http_security": {}},
        preferred_provider=provider,
        preferred_model=model,
    )

    verified = verification_result.get("verified", [])
    verified_map = {v["title"].lower(): v for v in verified}

    for v_row in vulns:
        if v_row.title.lower() in verified_map:
            v_row.verified = True
            v_row.proof_of_concept = verified_map[v_row.title.lower()].get("poc", "")

    await db.commit()

    publish_scan_event(scan_id, "exploitation_completed", verified=len(verified))

    return {
        "scan_id": scan_id,
        "status": "completed",
        "verified_count": len(verified),
        "total_findings": len(vulns),
        "verified_findings": verified,
        "message": f"Exploitation agent completed verification: {len(verified)} / {len(vulns)} verified.",
    }



@router.post("/{scan_id}/rescan")
async def rescan(
    scan_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Create a new scan from the original immutable authorization scope."""
    from sqlalchemy import select

    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail="Scan not found")
    new_scan_id = str(uuid.uuid4())
    scan = Scan(
        id=new_scan_id,
        target=original.target,
        scope=original.scope,
        mode=original.mode,
        status=ScanStatusEnum.PENDING,
        llm_provider=original.llm_provider,
        llm_model=original.llm_model,
        current_stage="pending",
    )
    db.add(scan)
    await db.commit()
    background_tasks.add_task(
        _execute_scan_background,
        scan_id=new_scan_id,
        target=scan.target,
        scope=scan.scope or "",
        mode=scan.mode,
        llm_provider=scan.llm_provider,
        llm_model=scan.llm_model,
    )
    return {"scan_id": new_scan_id, "status": "pending", "message": "Rescan queued"}


@router.post("/{scan_id}/schedule")
async def schedule_scan(
    scan_id: str,
    request: ScheduleRequest,
    db: AsyncSession = Depends(get_db),
):
    """Schedule a one-shot rescan without changing the original scope."""
    from sqlalchemy import select

    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail="Scan not found")
    run_at = request.run_at if request.run_at.tzinfo else request.run_at.replace(tzinfo=timezone.utc)
    run_at = run_at.astimezone(timezone.utc)
    if run_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="run_at must be in the future")
    schedule_id = str(uuid.uuid4())
    _scheduled_scans[schedule_id] = {"scan_id": scan_id, "run_at": run_at.isoformat(), "status": "scheduled"}
    asyncio.create_task(_run_scheduled_scan(schedule_id, run_at, original))
    return {"schedule_id": schedule_id, **_scheduled_scans[schedule_id]}


async def _run_scheduled_scan(schedule_id: str, run_at: datetime, original: Scan) -> None:
    await asyncio.sleep(max(0, (run_at - datetime.now(timezone.utc)).total_seconds()))
    async with AsyncSessionLocal() as db_session:
        new_scan_id = str(uuid.uuid4())
        scan = Scan(
            id=new_scan_id,
            target=original.target,
            scope=original.scope,
            mode=original.mode,
            status=ScanStatusEnum.PENDING,
            llm_provider=original.llm_provider,
            llm_model=original.llm_model,
            current_stage="pending",
        )
        db_session.add(scan)
        await db_session.commit()
        _scheduled_scans[schedule_id].update({"status": "queued", "new_scan_id": new_scan_id})
        await _execute_scan_background(
            new_scan_id, scan.target, scan.scope or "", scan.mode, scan.llm_provider, scan.llm_model
        )


@router.get("/{scan_id}/events")
async def get_scan_event_stream(scan_id: str, after: int = 0):
    """Return recent live orchestration and tool events for a scan."""
    return {"events": get_scan_events(scan_id, after)}


@router.post("/{scan_id}/approve")
async def approve_scan(
    scan_id: str,
    request: ApprovalRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Release a human-review scan only after an explicit reviewer token."""
    from sqlalchemy import select

    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scan.status != ScanStatusEnum.AWAITING_REVIEW:
        raise HTTPException(status_code=400, detail="Scan is not awaiting human review")
    try:
        scope_document = ScopeDocument.model_validate_json(scan.scope or "{}")
        scope_document = scope_document.model_copy(update={"approval_token": request.approval_token})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid stored scope: {exc}") from exc
    scan.scope = scope_document.model_dump_json()
    scan.status = ScanStatusEnum.PENDING
    await db.commit()
    background_tasks.add_task(
        _execute_scan_background,
        scan_id=scan.id,
        target=scan.target,
        scope=scan.scope,
        mode=scope_document.mode.value,
        llm_provider=scan.llm_provider,
        llm_model=scan.llm_model,
    )
    publish_scan_event(scan.id, "human_review_approved")
    return {"scan_id": scan.id, "status": "pending", "message": "Human approval recorded"}

@router.get("/list/all")
async def list_scans(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    List all scans with pagination
    """
    try:
        from sqlalchemy import select, desc
        
        result = await db.execute(
            select(Scan)
            .order_by(desc(Scan.created_at))
            .offset(skip)
            .limit(limit)
        )
        scans = result.scalars().all()
        
        return {
            "scans": [
                {
                    "scan_id": s.id,
                    "target": s.target,
                    "status": s.status.value if s.status else "unknown",
                    "created_at": s.created_at.isoformat(),
                    "duration": s.duration_seconds,
                    "vulnerabilities": s.vulnerabilities_found
                }
                for s in scans
            ],
            "total": len(scans)
        }
    
    except Exception as e:
        logger.error(f"Error listing scans: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to list scans")

# Background task
async def _execute_scan_background(
    scan_id: str,
    target: str,
    scope: str,
    mode: str,
    llm_provider: str,
    llm_model: str,
):
    """Execute scan in background"""
    if scan_id in _cancelled_scans:
        return
    try:
        async with AsyncSessionLocal() as db_session:
            orchestrator = get_orchestrator(db_session)
            from sqlalchemy import update

            scan_update = update(Scan).where(Scan.id == scan_id).values(
                status=ScanStatusEnum.RUNNING,
                current_stage="reconnaissance"
            )
            await db_session.execute(scan_update)
            await db_session.commit()

            result = await orchestrator.execute_scan(
                scan_id=scan_id,
                target=target,
                scope=scope,
                mode=mode,
                llm_provider=llm_provider,
                llm_model=llm_model
            )

            if scan_id in _cancelled_scans:
                return

            scan_update = update(Scan).where(Scan.id == scan_id).values(
                status=(ScanStatusEnum.COMPLETED if result.get('status') == 'completed' else
                        ScanStatusEnum.CANCELLED if result.get('status') == 'cancelled' else
                        ScanStatusEnum.FAILED),
                vulnerabilities_found=len(result.get('discovered_vulnerabilities', [])) or len(result.get('verified_vulnerabilities', [])),
                progress_percentage=100.0 if result.get('status') == 'completed' else 0.0,
                error_message=result.get('error', '')
            )
            await db_session.execute(scan_update)
            await db_session.commit()
        
            logger.info(f"✅ Scan {scan_id} completed successfully")
    
    except Exception as e:
        logger.error(f"❌ Background scan failed: {str(e)}")
        async with AsyncSessionLocal() as db_session:
            try:
                from sqlalchemy import update
                scan_update = update(Scan).where(Scan.id == scan_id).values(
                    status=ScanStatusEnum.FAILED,
                    error_message=str(e)
                )
                await db_session.execute(scan_update)
                await db_session.commit()
            except Exception:
                logger.exception("Could not persist failed scan status for %s", scan_id)
