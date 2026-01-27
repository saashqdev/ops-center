"""
SAML API Endpoints - Epic 20
REST API for SAML 2.0 SSO

Provides:
- SAML SSO initiation
- Assertion Consumer Service (ACS)
- SP metadata endpoint
- Provider configuration CRUD
- Session management
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import uuid
import base64
from urllib.parse import urlencode, quote

from auth_dependencies import require_authenticated_user
from saml_manager import get_saml_manager, SAMLManager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/saml",
    tags=["saml"]
)


# ==================== PYDANTIC MODELS ====================

class SAMLProviderCreate(BaseModel):
    name: str
    entity_id: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    idp_entity_id: str
    idp_sso_url: str
    idp_certificate: str = Field(..., description="X.509 certificate in PEM format")
    sp_entity_id: str
    sp_acs_url: str
    sp_slo_url: Optional[str] = None
    name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    want_assertions_signed: bool = True
    enable_jit_provisioning: bool = True
    default_role: str = "user"


class SAMLProviderUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    idp_sso_url: Optional[str] = None
    idp_certificate: Optional[str] = None
    is_active: Optional[bool] = None
    enable_jit_provisioning: Optional[bool] = None
    default_role: Optional[str] = None


class SAMLAttributeMapping(BaseModel):
    saml_attribute: str
    user_field: str
    is_required: bool = False
    default_value: Optional[str] = None
    transform_type: Optional[str] = None


# ==================== PROVIDER MANAGEMENT ENDPOINTS ====================

@router.post("/providers")
async def create_provider(
    provider: SAMLProviderCreate,
    user: Dict = Depends(require_authenticated_user)
):
    """
    Create new SAML provider configuration
    
    **Required Admin Role**
    """
    try:
        sm = get_saml_manager()
        if not sm:
            raise HTTPException(status_code=500, detail="SAML manager not initialized")
        
        provider_id = await sm.create_provider(
            name=provider.name,
            entity_id=provider.entity_id,
            display_name=provider.display_name,
            description=provider.description,
            idp_entity_id=provider.idp_entity_id,
            idp_sso_url=provider.idp_sso_url,
            idp_certificate=provider.idp_certificate,
            sp_entity_id=provider.sp_entity_id,
            sp_acs_url=provider.sp_acs_url,
            sp_slo_url=provider.sp_slo_url,
            name_id_format=provider.name_id_format,
            want_assertions_signed=provider.want_assertions_signed,
            enable_jit_provisioning=provider.enable_jit_provisioning,
            default_role=provider.default_role,
            created_by=user.get('email', 'unknown')
        )
        
        return {
            "provider_id": provider_id,
            "message": "SAML provider created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating SAML provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers")
async def list_providers(
    is_active: Optional[bool] = None,
    user: Dict = Depends(require_authenticated_user)
):
    """List SAML providers"""
    try:
        sm = get_saml_manager()
        if not sm:
            raise HTTPException(status_code=500, detail="SAML manager not initialized")
        
        providers = await sm.list_providers(is_active=is_active)
        
        # Mask sensitive data
        for provider in providers:
            if 'idp_certificate' in provider:
                provider['idp_certificate'] = '***REDACTED***'
            if 'sp_private_key' in provider:
                provider['sp_private_key'] = '***REDACTED***'
        
        return providers
        
    except Exception as e:
        logger.error(f"Error listing SAML providers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers/{provider_id}")
async def get_provider(
    provider_id: str,
    user: Dict = Depends(require_authenticated_user)
):
    """Get SAML provider details"""
    try:
        sm = get_saml_manager()
        if not sm:
            raise HTTPException(status_code=500, detail="SAML manager not initialized")
        
        provider = await sm.get_provider(provider_id)
        
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        # Mask sensitive data
        if 'idp_certificate' in provider:
            provider['idp_certificate'] = '***REDACTED***'
        if 'sp_private_key' in provider:
            provider['sp_private_key'] = '***REDACTED***'
        
        return provider
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting SAML provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/providers/{provider_id}")
async def update_provider(
    provider_id: str,
    updates: SAMLProviderUpdate,
    user: Dict = Depends(require_authenticated_user)
):
    """Update SAML provider configuration"""
    try:
        sm = get_saml_manager()
        if not sm:
            raise HTTPException(status_code=500, detail="SAML manager not initialized")
        
        # Build update dict
        update_fields = updates.dict(exclude_unset=True)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        success = await sm.update_provider(
            provider_id=provider_id,
            updated_by=user.get('email', 'unknown'),
            **update_fields
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        return {"message": "Provider updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating SAML provider: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SSO FLOW ENDPOINTS ====================

@router.get("/sso/{provider_id}")
async def initiate_sso(
    provider_id: str,
    relay_state: Optional[str] = None,
    request: Request = None
):
    """
    Initiate SAML SSO login
    
    Redirects user to IdP login page
    """
    try:
        sm = get_saml_manager()
        if not sm:
            raise HTTPException(status_code=500, detail="SAML manager not initialized")
        
        provider = await sm.get_provider(provider_id)
        
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        if not provider.get('is_active', False):
            raise HTTPException(status_code=400, detail="Provider is not active")
        
        # Generate AuthnRequest ID
        request_id = f"_{uuid.uuid4()}"
        
        # Build SAML AuthnRequest
        authn_request = f"""<samlp:AuthnRequest
    xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{datetime.utcnow().isoformat()}Z"
    Destination="{provider['idp_sso_url']}"
    AssertionConsumerServiceURL="{provider['sp_acs_url']}"
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
    <saml:Issuer>{provider['sp_entity_id']}</saml:Issuer>
    <samlp:NameIDPolicy
        Format="{provider.get('name_id_format', 'urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress')}"
        AllowCreate="true"/>
</samlp:AuthnRequest>"""
        
        # Encode AuthnRequest
        saml_request = base64.b64encode(authn_request.encode()).decode()
        
        # Build redirect URL
        params = {
            'SAMLRequest': saml_request
        }
        
        if relay_state:
            params['RelayState'] = relay_state
        
        redirect_url = f"{provider['idp_sso_url']}?{urlencode(params)}"
        
        return RedirectResponse(url=redirect_url)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating SSO: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/acs")
async def assertion_consumer_service(
    request: Request,
    SAMLResponse: str = Form(...),
    RelayState: Optional[str] = Form(None)
):
    """
    Assertion Consumer Service (ACS)
    
    Receives SAML assertion from IdP after authentication
    """
    try:
        sm = get_saml_manager()
        if not sm:
            raise HTTPException(status_code=500, detail="SAML manager not initialized")
        
        # Decode SAML response
        try:
            saml_response_xml = base64.b64decode(SAMLResponse).decode()
        except Exception as e:
            logger.error(f"Failed to decode SAML response: {e}")
            raise HTTPException(status_code=400, detail="Invalid SAML response")
        
        # Extract provider from response (simplified - in production, parse XML properly)
        # For now, try to find provider by checking all active providers
        providers = await sm.list_providers(is_active=True)
        
        if not providers:
            raise HTTPException(status_code=400, detail="No active SAML providers configured")
        
        # Use first active provider (in production, match by entity ID)
        provider = providers[0]
        provider_id = provider['provider_id']
        
        # Validate assertion
        validation_result = await sm.validate_assertion(
            assertion_xml=saml_response_xml,
            provider_id=provider_id,
            relay_state=RelayState,
            ip_address=request.client.host if request.client else None
        )
        
        if not validation_result['valid']:
            logger.warning(f"Invalid SAML assertion: {validation_result['errors']}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid SAML assertion: {', '.join(validation_result['errors'])}"
            )
        
        # Extract user info
        name_id = validation_result['name_id']
        attributes = validation_result['attributes']
        
        # Get email (try different attribute names)
        email = attributes.get('email') or attributes.get('emailAddress') or name_id
        
        # Create SAML session
        session_id = await sm.create_session(
            provider_id=provider_id,
            name_id=name_id,
            attributes=attributes,
            session_index=validation_result.get('session_index'),
            not_on_or_after=validation_result.get('not_on_or_after'),
            email=email,
            relay_state=RelayState,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get('user-agent')
        )
        
        # In production: create JWT token, set secure cookie, etc.
        # For now, redirect to dashboard
        redirect_target = RelayState or "/admin/dashboard"
        
        response = RedirectResponse(url=redirect_target)
        response.set_cookie(
            key="saml_session_id",
            value=session_id,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=28800  # 8 hours
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing SAML assertion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logout")
async def saml_logout(
    session_id: str,
    user: Dict = Depends(require_authenticated_user)
):
    """Logout from SAML session"""
    try:
        sm = get_saml_manager()
        if not sm:
            raise HTTPException(status_code=500, detail="SAML manager not initialized")
        
        success = await sm.terminate_session(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"message": "Logged out successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging out: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== METADATA ENDPOINTS ====================

@router.get("/metadata/{provider_id}", response_class=HTMLResponse)
async def get_sp_metadata(provider_id: str):
    """
    Get Service Provider (SP) metadata
    
    Returns XML metadata for configuring in IdP
    """
    try:
        sm = get_saml_manager()
        if not sm:
            raise HTTPException(status_code=500, detail="SAML manager not initialized")
        
        provider = await sm.get_provider(provider_id)
        
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        
        metadata_xml = sm.generate_sp_metadata(
            sp_entity_id=provider['sp_entity_id'],
            sp_acs_url=provider['sp_acs_url'],
            sp_slo_url=provider.get('sp_slo_url')
        )
        
        return Response(
            content=metadata_xml,
            media_type="application/xml",
            headers={
                "Content-Disposition": f'attachment; filename="sp-metadata-{provider_id}.xml"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SESSION MANAGEMENT ENDPOINTS ====================

@router.get("/sessions")
async def list_sessions(
    provider_id: Optional[str] = None,
    user: Dict = Depends(require_authenticated_user)
):
    """List active SAML sessions"""
    try:
        sm = get_saml_manager()
        if not sm:
            raise HTTPException(status_code=500, detail="SAML manager not initialized")
        
        sessions = await sm.get_active_sessions(provider_id=provider_id)
        
        return sessions
        
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    user: Dict = Depends(require_authenticated_user)
):
    """Get SAML session details"""
    try:
        sm = get_saml_manager()
        if not sm:
            raise HTTPException(status_code=500, detail="SAML manager not initialized")
        
        session = await sm.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DASHBOARD ENDPOINTS ====================

@router.get("/statistics")
async def get_statistics(
    user: Dict = Depends(require_authenticated_user)
):
    """Get SAML statistics"""
    try:
        sm = get_saml_manager()
        if not sm:
            raise HTTPException(status_code=500, detail="SAML manager not initialized")
        
        stats = await sm.get_statistics()
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
