"""
Scanning Routes - Handle scan operations
"""

import logging
import uuid
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_db
from database.models import Scan, ScanStatusEnum
from agents.orchestrator import get_orchestrator
from config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()

class ScanRequest(BaseModel):
    """Scan request model"""
    target: str
    scope: Optional[str] = None
    mode: str = "normal"  # "normal", "aggressive", "stealth"
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
        
        # Use default LLM settings if not provided
        llm_provider = request.llm_provider or settings.ACTIVE_LLM
        llm_model = request.llm_model or settings.OLLAMA_MODEL
        
        # Create scan record
        scan = Scan(
            id=scan_id,
            target=request.target,
            scope=request.scope or "",
            mode=request.mode,
            status=ScanStatusEnum.PENDING,
            llm_provider=llm_provider,
            llm_model=llm_model,
            progress_percentage=0.0,
            current_stage="pending"
        )
        
        db.add(scan)
        await db.commit()
        
        logger.info(f"📌 Scan {scan_id} created for {request.target}")
        
        # Add background task to execute scan
        background_tasks.add_task(
            _execute_scan_background,
            scan_id=scan_id,
            target=request.target,
            scope=request.scope or "",
            mode=request.mode,
            llm_provider=llm_provider,
            llm_model=llm_model,
            db_session=db
        )
        
        return ScanResponse(
            scan_id=scan_id,
            target=request.target,
            status="pending",
            created_at=scan.created_at.isoformat(),
            message="Scan queued and will start shortly"
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
    Get results of a completed scan
    """
    try:
        from sqlalchemy import select
        
        result = await db.execute(select(Scan).where(Scan.id == scan_id))
        scan = result.scalar_one_or_none()
        
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
        
        if scan.status != ScanStatusEnum.COMPLETED:
            raise HTTPException(status_code=400, detail="Scan is not completed yet")
        
        # Get vulnerabilities
        vulns_result = await db.execute(
            select(Vulnerability).where(Vulnerability.scan_id == scan_id)
        )
        vulnerabilities = vulns_result.scalars().all()
        
        return ScanResultsResponse(
            scan_id=scan.id,
            target=scan.target,
            status=scan.status.value,
            vulnerabilities=[
                {
                    "id": v.id,
                    "title": v.title,
                    "severity": v.severity.value if v.severity else "unknown",
                    "type": v.vulnerability_type,
                    "description": v.description
                }
                for v in vulnerabilities
            ],
            recommendations=[
                "Review and patch vulnerabilities by severity",
                "Implement Web Application Firewall (WAF)",
                "Regular security assessments recommended"
            ],
            risk_score=len([v for v in vulnerabilities if v.severity in ["critical", "high"]]) * 2.5
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
        
        scan.status = ScanStatusEnum.CANCELLED
        await db.commit()
        
        logger.info(f"Scan {scan_id} cancelled")
        
        return {"message": "Scan cancelled successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling scan: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cancel scan")

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
    db_session: AsyncSession
):
    """Execute scan in background"""
    try:
        # Get orchestrator
        orchestrator = get_orchestrator(db_session)
        
        # Update scan status
        from sqlalchemy import select, update
        
        scan_update = update(Scan).where(Scan.id == scan_id).values(
            status=ScanStatusEnum.RUNNING,
            current_stage="reconnaissance"
        )
        await db_session.execute(scan_update)
        await db_session.commit()
        
        # Execute scan workflow
        result = await orchestrator.execute_scan(
            scan_id=scan_id,
            target=target,
            scope=scope,
            mode=mode,
            llm_provider=llm_provider,
            llm_model=llm_model
        )
        
        # Update scan with results
        scan_update = update(Scan).where(Scan.id == scan_id).values(
            status=ScanStatusEnum.COMPLETED if result.get('status') == 'completed' else ScanStatusEnum.FAILED,
            vulnerabilities_found=len(result.get('verified_vulnerabilities', [])),
            progress_percentage=100.0 if result.get('status') == 'completed' else 0.0,
            error_message=result.get('error', '')
        )
        await db_session.execute(scan_update)
        await db_session.commit()
        
        logger.info(f"✅ Scan {scan_id} completed successfully")
    
    except Exception as e:
        logger.error(f"❌ Background scan failed: {str(e)}")
        try:
            from sqlalchemy import update
            scan_update = update(Scan).where(Scan.id == scan_id).values(
                status=ScanStatusEnum.FAILED,
                error_message=str(e)
            )
            await db_session.execute(scan_update)
            await db_session.commit()
        except:
            pass
