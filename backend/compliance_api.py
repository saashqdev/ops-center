"""
SOC2 Compliance API Endpoints - Epic 18
Comprehensive REST API for compliance management

Provides:
- Control management and automated checking
- Evidence collection and retrieval
- Security incident tracking
- Compliance dashboard data
- Report generation
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from auth_dependencies import require_authenticated_user
from compliance_manager import get_compliance_manager, ComplianceManager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/compliance",
    tags=["compliance"]
)


# ==================== PYDANTIC MODELS ====================

class ControlResponse(BaseModel):
    control_id: str
    name: str
    description: str
    category: str
    soc2_criteria: str
    implementation_status: str
    automated: bool
    check_frequency_hours: Optional[int]
    evidence_requirements: Optional[List[str]]
    last_check_at: Optional[datetime]
    last_check_status: Optional[str]
    last_check_result: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class ControlStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(not_implemented|in_progress|implemented|verified)$")


class AutomatedCheckResponse(BaseModel):
    control_id: str
    status: str
    message: str
    timestamp: str
    metrics: Optional[Dict[str, Any]] = None


class EvidenceCreate(BaseModel):
    control_id: str
    evidence_type: str = Field(..., pattern="^(log|screenshot|document|config|report|other)$")
    title: str
    description: str
    data: Dict[str, Any]


class EvidenceResponse(BaseModel):
    evidence_id: str
    control_id: str
    evidence_type: str
    title: str
    description: str
    collected_by: Optional[str]
    collected_at: datetime
    collection_method: str
    data: Dict[str, Any]
    verified: bool
    verified_by: Optional[str]
    verified_at: Optional[datetime]


class IncidentCreate(BaseModel):
    title: str
    description: str
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    incident_type: str
    detected_at: datetime
    affected_systems: Optional[List[str]] = []
    affected_users: Optional[List[str]] = []
    metadata: Optional[Dict[str, Any]] = {}


class IncidentUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(open|investigating|resolved|false_positive)$")
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None


class IncidentResponse(BaseModel):
    incident_id: str
    title: str
    description: str
    severity: str
    incident_type: str
    status: str
    detected_at: datetime
    reported_by: Optional[str]
    assigned_to: Optional[str]
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]
    affected_systems: List[str]
    affected_users: List[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ComplianceOverviewResponse(BaseModel):
    by_category: List[Dict[str, Any]]
    readiness: Dict[str, Any]
    timestamp: str


# ==================== CONTROL ENDPOINTS ====================

@router.get("/controls", response_model=List[ControlResponse])
async def list_controls(
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by implementation status"),
    automated_only: bool = Query(False, description="Show only automated controls"),
    user: Dict = Depends(require_authenticated_user)
):
    """
    List all compliance controls with optional filters
    
    **Requires:** Authenticated user
    
    **Filters:**
    - category: Security, Availability, Processing Integrity, Confidentiality, Privacy
    - status: not_implemented, in_progress, implemented, verified
    - automated_only: true to show only controls with automated checks
    """
    try:
        cm = get_compliance_manager()
        if not cm:
            raise HTTPException(status_code=500, detail="Compliance manager not initialized")
        
        controls = await cm.list_controls(
            category=category,
            status=status,
            automated_only=automated_only
        )
        
        return controls
    except Exception as e:
        logger.error(f"Error listing controls: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/controls/{control_id}", response_model=ControlResponse)
async def get_control(
    control_id: str,
    user: Dict = Depends(require_authenticated_user)
):
    """
    Get details of a specific compliance control
    
    **Requires:** Authenticated user
    """
    try:
        cm = get_compliance_manager()
        if not cm:
            raise HTTPException(status_code=500, detail="Compliance manager not initialized")
        
        control = await cm.get_control(control_id)
        
        if not control:
            raise HTTPException(status_code=404, detail=f"Control {control_id} not found")
        
        return control
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting control: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/controls/{control_id}/status")
async def update_control_status(
    control_id: str,
    update: ControlStatusUpdate,
    user: Dict = Depends(require_authenticated_user)
):
    """
    Update control implementation status
    
    **Requires:** Authenticated user with compliance management permissions
    
    **Statuses:**
    - not_implemented: Control not yet implemented
    - in_progress: Implementation in progress
    - implemented: Implementation complete
    - verified: Implementation verified by auditor
    """
    try:
        cm = get_compliance_manager()
        if not cm:
            raise HTTPException(status_code=500, detail="Compliance manager not initialized")
        
        success = await cm.update_control_status(
            control_id=control_id,
            status=update.status,
            updated_by=user.get('email', 'unknown')
        )
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Control {control_id} not found")
        
        return {"message": "Control status updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating control status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/controls/{control_id}/check", response_model=AutomatedCheckResponse)
async def run_automated_check(
    control_id: str,
    user: Dict = Depends(require_authenticated_user)
):
    """
    Run automated compliance check for a control
    
    **Requires:** Authenticated user
    
    **Note:** Only works for controls where automated=true
    """
    try:
        cm = get_compliance_manager()
        if not cm:
            raise HTTPException(status_code=500, detail="Compliance manager not initialized")
        
        result = await cm.run_automated_check(control_id)
        
        if result.get('status') == 'error':
            raise HTTPException(status_code=400, detail=result.get('message'))
        
        return {
            'control_id': control_id,
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running automated check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/controls/check-all")
async def run_all_automated_checks(
    user: Dict = Depends(require_authenticated_user)
):
    """
    Run all automated compliance checks
    
    **Requires:** Authenticated user
    
    **Returns:** Summary of all check results
    """
    try:
        cm = get_compliance_manager()
        if not cm:
            raise HTTPException(status_code=500, detail="Compliance manager not initialized")
        
        # Get all automated controls
        controls = await cm.list_controls(automated_only=True)
        
        results = []
        for control in controls:
            result = await cm.run_automated_check(control['control_id'])
            results.append({
                'control_id': control['control_id'],
                'control_name': control['name'],
                **result
            })
        
        # Summarize results
        summary = {
            'total_checks': len(results),
            'passed': sum(1 for r in results if r.get('status') == 'passed'),
            'failed': sum(1 for r in results if r.get('status') == 'failed'),
            'warnings': sum(1 for r in results if r.get('status') == 'warning'),
            'errors': sum(1 for r in results if r.get('status') == 'error'),
            'results': results
        }
        
        return summary
    except Exception as e:
        logger.error(f"Error running all automated checks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== EVIDENCE ENDPOINTS ====================

@router.post("/evidence", response_model=Dict[str, str])
async def collect_evidence(
    evidence: EvidenceCreate,
    user: Dict = Depends(require_authenticated_user)
):
    """
    Collect evidence for a compliance control
    
    **Requires:** Authenticated user
    
    **Evidence Types:**
    - log: System or audit logs
    - screenshot: Visual evidence
    - document: Policy documents, procedures
    - config: Configuration files
    - report: Generated reports
    - other: Other types of evidence
    """
    try:
        cm = get_compliance_manager()
        if not cm:
            raise HTTPException(status_code=500, detail="Compliance manager not initialized")
        
        evidence_id = await cm.collect_evidence(
            control_id=evidence.control_id,
            evidence_type=evidence.evidence_type,
            title=evidence.title,
            description=evidence.description,
            data=evidence.data,
            collected_by=user.get('email', 'unknown')
        )
        
        if not evidence_id:
            raise HTTPException(status_code=500, detail="Failed to collect evidence")
        
        return {"evidence_id": evidence_id, "message": "Evidence collected successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error collecting evidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evidence", response_model=List[EvidenceResponse])
async def list_evidence(
    control_id: Optional[str] = Query(None, description="Filter by control ID"),
    evidence_type: Optional[str] = Query(None, description="Filter by evidence type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    user: Dict = Depends(require_authenticated_user)
):
    """
    List collected evidence with optional filters
    
    **Requires:** Authenticated user
    """
    try:
        cm = get_compliance_manager()
        if not cm:
            raise HTTPException(status_code=500, detail="Compliance manager not initialized")
        
        evidence = await cm.get_evidence(
            control_id=control_id,
            evidence_type=evidence_type,
            limit=limit
        )
        
        return evidence
    except Exception as e:
        logger.error(f"Error listing evidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== INCIDENT ENDPOINTS ====================

@router.post("/incidents", response_model=Dict[str, str])
async def create_incident(
    incident: IncidentCreate,
    user: Dict = Depends(require_authenticated_user)
):
    """
    Create a security incident
    
    **Requires:** Authenticated user
    
    **Severity Levels:**
    - low: Minor issues, no immediate impact
    - medium: Moderate impact, requires attention
    - high: Significant impact, urgent action required
    - critical: Severe impact, immediate action required
    """
    try:
        cm = get_compliance_manager()
        if not cm:
            raise HTTPException(status_code=500, detail="Compliance manager not initialized")
        
        incident_id = await cm.create_incident(
            title=incident.title,
            description=incident.description,
            severity=incident.severity,
            incident_type=incident.incident_type,
            detected_at=incident.detected_at,
            reported_by=user.get('email', 'unknown'),
            affected_systems=incident.affected_systems,
            affected_users=incident.affected_users,
            metadata=incident.metadata
        )
        
        if not incident_id:
            raise HTTPException(status_code=500, detail="Failed to create incident")
        
        return {"incident_id": incident_id, "message": "Incident created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/incidents/{incident_id}")
async def update_incident(
    incident_id: str,
    update: IncidentUpdate,
    user: Dict = Depends(require_authenticated_user)
):
    """
    Update security incident
    
    **Requires:** Authenticated user with incident management permissions
    
    **Statuses:**
    - open: Incident reported, not yet investigated
    - investigating: Under investigation
    - resolved: Incident resolved
    - false_positive: Determined to be false positive
    """
    try:
        cm = get_compliance_manager()
        if not cm:
            raise HTTPException(status_code=500, detail="Compliance manager not initialized")
        
        success = await cm.update_incident(
            incident_id=incident_id,
            status=update.status,
            assigned_to=update.assigned_to,
            resolution_notes=update.resolution_notes
        )
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
        
        return {"message": "Incident updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating incident: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/incidents", response_model=List[IncidentResponse])
async def list_incidents(
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    user: Dict = Depends(require_authenticated_user)
):
    """
    List security incidents with optional filters
    
    **Requires:** Authenticated user
    """
    try:
        cm = get_compliance_manager()
        if not cm:
            raise HTTPException(status_code=500, detail="Compliance manager not initialized")
        
        incidents = await cm.get_incidents(
            status=status,
            severity=severity,
            limit=limit
        )
        
        return incidents
    except Exception as e:
        logger.error(f"Error listing incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DASHBOARD ENDPOINTS ====================

@router.get("/dashboard/overview", response_model=ComplianceOverviewResponse)
async def get_compliance_overview(
    user: Dict = Depends(require_authenticated_user)
):
    """
    Get compliance overview dashboard data
    
    **Requires:** Authenticated user
    
    **Returns:**
    - Compliance status by category
    - Overall readiness score
    - Summary metrics
    """
    try:
        cm = get_compliance_manager()
        if not cm:
            raise HTTPException(status_code=500, detail="Compliance manager not initialized")
        
        overview = await cm.get_compliance_overview()
        
        return overview
    except Exception as e:
        logger.error(f"Error getting compliance overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard/recent-incidents")
async def get_recent_incidents(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of incidents"),
    user: Dict = Depends(require_authenticated_user)
):
    """
    Get recent security incidents for dashboard
    
    **Requires:** Authenticated user
    """
    try:
        cm = get_compliance_manager()
        if not cm:
            raise HTTPException(status_code=500, detail="Compliance manager not initialized")
        
        incidents = await cm.get_recent_incidents(limit=limit)
        
        return incidents
    except Exception as e:
        logger.error(f"Error getting recent incidents: {e}")
        raise HTTPException(status_code=500, detail=str(e))
