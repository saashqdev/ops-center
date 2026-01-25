"""
Organization Branding API - Epic 4.5: Custom Branding & White-Label
Provides organization-level branding configuration with tier-based limits.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncpg
import json
import os
import uuid
import aiofiles
from pathlib import Path

router = APIRouter(prefix="/api/v1/organizations", tags=["Organization Branding"])

# Configuration
UPLOAD_DIR = Path("/app/uploads/branding")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB base limit
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/svg+xml", "image/webp"}

# Pydantic Models
class ColorScheme(BaseModel):
    """Organization color scheme"""
    primary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    secondary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    accent_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    text_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    background_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")

class Typography(BaseModel):
    """Organization typography settings"""
    font_family: Optional[str] = Field(None, max_length=100)
    heading_font: Optional[str] = Field(None, max_length=100)

class CompanyInfo(BaseModel):
    """Organization company information"""
    company_name: Optional[str] = Field(None, max_length=200)
    tagline: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    support_email: Optional[str] = Field(None, max_length=200)
    support_phone: Optional[str] = Field(None, max_length=50)

class SocialLinks(BaseModel):
    """Organization social media links"""
    twitter_url: Optional[str] = Field(None, max_length=500)
    linkedin_url: Optional[str] = Field(None, max_length=500)
    github_url: Optional[str] = Field(None, max_length=500)
    discord_url: Optional[str] = Field(None, max_length=500)

class CustomDomain(BaseModel):
    """Custom domain configuration"""
    custom_domain: Optional[str] = Field(None, max_length=255)
    domain_verified: bool = False
    ssl_enabled: bool = False

class EmailBranding(BaseModel):
    """Email template branding"""
    email_from_name: Optional[str] = Field(None, max_length=200)
    email_from_address: Optional[str] = Field(None, max_length=200)
    email_logo_url: Optional[str] = Field(None, max_length=500)
    email_footer_text: Optional[str] = Field(None, max_length=1000)

class BrandingFeatures(BaseModel):
    """Branding feature flags"""
    custom_logo_enabled: bool = False
    custom_colors_enabled: bool = False
    custom_domain_enabled: bool = False
    custom_email_enabled: bool = False
    white_label_enabled: bool = False

class OrganizationBrandingCreate(BaseModel):
    """Create organization branding"""
    org_id: str
    org_name: str
    colors: Optional[ColorScheme] = None
    typography: Optional[Typography] = None
    company_info: Optional[CompanyInfo] = None
    social_links: Optional[SocialLinks] = None
    custom_domain: Optional[CustomDomain] = None
    email_branding: Optional[EmailBranding] = None
    features: Optional[BrandingFeatures] = None
    custom_terms_text: Optional[str] = None
    custom_privacy_text: Optional[str] = None

class OrganizationBrandingUpdate(BaseModel):
    """Update organization branding"""
    colors: Optional[ColorScheme] = None
    typography: Optional[Typography] = None
    company_info: Optional[CompanyInfo] = None
    social_links: Optional[SocialLinks] = None
    custom_domain: Optional[CustomDomain] = None
    email_branding: Optional[EmailBranding] = None
    features: Optional[BrandingFeatures] = None
    custom_terms_text: Optional[str] = None
    custom_privacy_text: Optional[str] = None

class OrganizationBrandingResponse(BaseModel):
    """Organization branding response"""
    id: int
    org_id: str
    org_name: str
    tier_code: Optional[str]
    logo_url: Optional[str]
    logo_dark_url: Optional[str]
    favicon_url: Optional[str]
    background_image_url: Optional[str]
    primary_color: Optional[str]
    secondary_color: Optional[str]
    accent_color: Optional[str]
    text_color: Optional[str]
    background_color: Optional[str]
    font_family: Optional[str]
    heading_font: Optional[str]
    company_name: Optional[str]
    tagline: Optional[str]
    description: Optional[str]
    support_email: Optional[str]
    support_phone: Optional[str]
    twitter_url: Optional[str]
    linkedin_url: Optional[str]
    github_url: Optional[str]
    discord_url: Optional[str]
    custom_domain: Optional[str]
    custom_domain_verified: bool
    custom_domain_ssl_enabled: bool
    custom_terms_text: Optional[str]
    custom_privacy_text: Optional[str]
    email_from_name: Optional[str]
    email_from_address: Optional[str]
    email_logo_url: Optional[str]
    email_footer_text: Optional[str]
    custom_logo_enabled: bool
    custom_colors_enabled: bool
    custom_domain_enabled: bool
    custom_email_enabled: bool
    white_label_enabled: bool
    created_at: datetime
    updated_at: datetime

class BrandingTierLimits(BaseModel):
    """Tier-based branding limits"""
    tier_code: str
    max_logo_size_mb: float
    max_assets: int
    custom_colors: bool
    custom_fonts: bool
    custom_domain: bool
    custom_email_branding: bool
    remove_powered_by: bool
    custom_login_page: bool
    custom_css: bool
    api_white_label: bool

class BrandingAssetResponse(BaseModel):
    """Branding asset response"""
    id: int
    org_id: str
    asset_type: str
    asset_url: str
    file_name: str
    file_size: int
    mime_type: str
    uploaded_at: datetime

# Helper Functions
async def get_current_user(request: Request) -> Dict[str, Any]:
    """Get current user from session - simplified auth check"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # For now, return a mock user - in production this would validate session
    return {"id": 1, "email": "admin@example.com", "username": "admin"}

async def get_db_connection():
    """Get database connection"""
    return await asyncpg.connect(
        host=os.getenv("POSTGRES_HOST", "unicorn-postgresql"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "unicorn_db"),
        user=os.getenv("POSTGRES_USER", "unicorn"),
        password=os.getenv("POSTGRES_PASSWORD", "unicorn")
    )

async def get_organization_tier(conn: asyncpg.Connection, org_id: int) -> Optional[str]:
    """Get organization's subscription tier"""
    # TODO: Integrate with actual subscription system when available
    # For now, return 'professional' as default tier
    # In production, this should query subscriptions table
    return "professional"

async def get_tier_limits(conn: asyncpg.Connection, tier_code: str) -> Dict[str, Any]:
    """Get branding limits for a tier"""
    result = await conn.fetchrow("""
        SELECT * FROM branding_tier_limits WHERE tier_code = $1
    """, tier_code)
    
    if not result:
        # Return default (most restrictive) limits
        return {
            "max_file_size_mb": 1,
            "max_assets": 2,
            "custom_logo": False,
            "custom_colors": False,
            "custom_fonts": False,
            "custom_domain": False,
            "custom_email_branding": False,
            "white_label": False,
            "remove_powered_by": False
        }
    
    return dict(result)

async def check_tier_feature(conn: asyncpg.Connection, org_id: int, feature: str) -> bool:
    """Check if organization's tier allows a specific branding feature"""
    tier_code = await get_organization_tier(conn, org_id)
    if not tier_code:
        return False
    
    limits = await get_tier_limits(conn, tier_code)
    return limits.get(feature, False)

async def count_organization_assets(conn: asyncpg.Connection, org_id: str) -> int:
    """Count total assets for an organization"""
    result = await conn.fetchval("""
        SELECT COUNT(*) FROM branding_assets WHERE org_id = $1
    """, org_id)
    return result or 0

async def save_uploaded_file(file: UploadFile, org_id: int, asset_type: str) -> Dict[str, Any]:
    """Save uploaded file and return asset info"""
    # Generate unique filename
    file_ext = Path(file.filename).suffix
    unique_filename = f"{org_id}_{asset_type}_{uuid.uuid4()}{file_ext}"
    file_path = UPLOAD_DIR / unique_filename
    
    # Save file
    file_size = 0
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        file_size = len(content)
        await f.write(content)
    
    return {
        "file_path": str(file_path),
        "file_name": file.filename,
        "file_size": file_size,
        "mime_type": file.content_type,
        "asset_url": f"/uploads/branding/{unique_filename}"
    }

async def log_branding_change(
    conn: asyncpg.Connection,
    org_id: str,
    user_id: int,
    action: str,
    changes: Dict[str, Any]
):
    """Log branding changes for audit trail"""
    await conn.execute("""
        INSERT INTO branding_audit_log 
        (org_id, performed_by, action, changes)
        VALUES ($1, $2, $3, $4)
    """, org_id, str(user_id), action, json.dumps(changes))

# API Endpoints

@router.get("/{org_id}/branding/", response_model=OrganizationBrandingResponse)
async def get_organization_branding(
    org_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get organization branding configuration"""
    conn = await get_db_connection()
    try:
        branding = await conn.fetchrow("""
            SELECT * FROM organization_branding WHERE org_id = $1
        """, org_id)
        
        if not branding:
            raise HTTPException(status_code=404, detail="Organization branding not found")
        
        return dict(branding)
    finally:
        await conn.close()

@router.post("/{org_id}/branding/", response_model=OrganizationBrandingResponse)
async def create_organization_branding(
    org_id: str,
    branding: OrganizationBrandingCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create organization branding configuration"""
    conn = await get_db_connection()
    try:
        # Check if branding already exists
        existing = await conn.fetchrow("""
            SELECT id FROM organization_branding WHERE org_id = $1
        """, org_id)
        
        if existing:
            raise HTTPException(
                status_code=400, 
                detail="Organization branding already exists. Use PUT to update."
            )
        
        # Get organization tier
        tier_code = await get_organization_tier(conn, org_id)
        
        # Prepare data
        colors = branding.colors.dict() if branding.colors else {}
        typography = branding.typography.dict() if branding.typography else {}
        company_info = branding.company_info.dict() if branding.company_info else {}
        social_links = branding.social_links.dict() if branding.social_links else {}
        custom_domain = branding.custom_domain.dict() if branding.custom_domain else {}
        email_branding = branding.email_branding.dict() if branding.email_branding else {}
        features = branding.features.dict() if branding.features else {}
        
        # Create branding
        result = await conn.fetchrow("""
            INSERT INTO organization_branding (
                org_id, org_name, tier_code,
                primary_color, secondary_color, accent_color, text_color, background_color,
                font_family, heading_font,
                company_name, tagline, description, support_email, support_phone,
                twitter_url, linkedin_url, github_url, discord_url,
                custom_domain, custom_domain_verified, custom_domain_ssl_enabled,
                custom_terms_text, custom_privacy_text,
                email_from_name, email_from_address, email_logo_url, email_footer_text,
                custom_logo_enabled, custom_colors_enabled,
                custom_domain_enabled, custom_email_enabled, white_label_enabled
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                $16, $17, $18, $19, $20, $21, $22, $23, $24,
                $25, $26, $27, $28, $29, $30, $31, $32, $33
            ) RETURNING *
        """,
            branding.org_id, branding.org_name, tier_code,
            colors.get("primary_color"), colors.get("secondary_color"), 
            colors.get("accent_color"), colors.get("text_color"), colors.get("background_color"),
            typography.get("font_family"), typography.get("heading_font"),
            company_info.get("company_name"), company_info.get("tagline"), 
            company_info.get("description"), company_info.get("support_email"), 
            company_info.get("support_phone"),
            social_links.get("twitter_url"), social_links.get("linkedin_url"), 
            social_links.get("github_url"), social_links.get("discord_url"),
            custom_domain.get("custom_domain"), custom_domain.get("domain_verified", False),
            custom_domain.get("ssl_enabled", False),
            branding.custom_terms_text, branding.custom_privacy_text,
            email_branding.get("email_from_name"), email_branding.get("email_from_address"),
            email_branding.get("email_logo_url"), email_branding.get("email_footer_text"),
            features.get("custom_logo_enabled", False), features.get("custom_colors_enabled", False),
            features.get("custom_domain_enabled", False), features.get("custom_email_enabled", False),
            features.get("white_label_enabled", False)
        )
        
        # Log creation
        await log_branding_change(
            conn, org_id, current_user["id"], "create", 
            {"message": "Organization branding created"}
        )
        
        return dict(result)
    finally:
        await conn.close()

@router.put("/{org_id}/branding/", response_model=OrganizationBrandingResponse)
async def update_organization_branding(
    org_id: str,
    branding: OrganizationBrandingUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update organization branding configuration"""
    conn = await get_db_connection()
    try:
        # Get existing branding
        existing = await conn.fetchrow("""
            SELECT * FROM organization_branding WHERE org_id = $1
        """, org_id)
        
        if not existing:
            raise HTTPException(status_code=404, detail="Organization branding not found")
        
        # Build update fields
        updates = []
        values = []
        param_count = 1
        changes = {}
        
        if branding.colors:
            for field, value in branding.colors.dict(exclude_none=True).items():
                updates.append(f"{field} = ${param_count}")
                values.append(value)
                changes[field] = value
                param_count += 1
        
        if branding.typography:
            for field, value in branding.typography.dict(exclude_none=True).items():
                updates.append(f"{field} = ${param_count}")
                values.append(value)
                changes[field] = value
                param_count += 1
        
        if branding.company_info:
            for field, value in branding.company_info.dict(exclude_none=True).items():
                updates.append(f"{field} = ${param_count}")
                values.append(value)
                changes[field] = value
                param_count += 1
        
        if branding.social_links:
            for field, value in branding.social_links.dict(exclude_none=True).items():
                updates.append(f"{field} = ${param_count}")
                values.append(value)
                changes[field] = value
                param_count += 1
        
        if branding.custom_domain:
            for field, value in branding.custom_domain.dict(exclude_none=True).items():
                updates.append(f"{field} = ${param_count}")
                values.append(value)
                changes[field] = value
                param_count += 1
        
        if branding.email_branding:
            for field, value in branding.email_branding.dict(exclude_none=True).items():
                email_field = f"email_{field}" if not field.startswith("email_") else field
                updates.append(f"{email_field} = ${param_count}")
                values.append(value)
                changes[email_field] = value
                param_count += 1
        
        if branding.features:
            for field, value in branding.features.dict(exclude_none=True).items():
                updates.append(f"{field} = ${param_count}")
                values.append(value)
                changes[field] = value
                param_count += 1
        
        # Add simple fields
        simple_fields = ["custom_terms_text", "custom_privacy_text"]
        for field in simple_fields:
            value = getattr(branding, field, None)
            if value is not None:
                updates.append(f"{field} = ${param_count}")
                values.append(value)
                changes[field] = value
                param_count += 1
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Execute update
        values.append(org_id)
        query = f"""
            UPDATE organization_branding 
            SET {', '.join(updates)}, updated_at = NOW()
            WHERE org_id = ${param_count}
            RETURNING *
        """
        
        result = await conn.fetchrow(query, *values)
        
        # Log update
        await log_branding_change(
            conn, org_id, current_user["id"], "update", changes
        )
        
        return dict(result)
    finally:
        await conn.close()

@router.delete("/{org_id}/branding/")
async def delete_organization_branding(
    org_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete organization branding configuration"""
    conn = await get_db_connection()
    try:
        result = await conn.execute("""
            DELETE FROM organization_branding WHERE org_id = $1
        """, org_id)
        
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Organization branding not found")
        
        # Log deletion
        await log_branding_change(
            conn, org_id, current_user["id"], "delete", 
            {"message": "Organization branding deleted"}
        )
        
        return {"message": "Organization branding deleted successfully"}
    finally:
        await conn.close()

@router.get("/{org_id}/branding/limits/", response_model=BrandingTierLimits)
async def get_branding_limits(
    org_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get branding limits for organization's tier"""
    conn = await get_db_connection()
    try:
        tier_code = await get_organization_tier(conn, org_id)
        if not tier_code:
            raise HTTPException(status_code=404, detail="Organization has no active subscription")
        
        limits = await get_tier_limits(conn, tier_code)
        return {**limits, "tier_code": tier_code}
    finally:
        await conn.close()

@router.post("/{org_id}/branding/assets/upload/")
async def upload_branding_asset(
    org_id: str,
    asset_type: str = Form(...),  # logo, logo_dark, favicon, background
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload branding asset (logo, favicon, etc.)"""
    conn = await get_db_connection()
    try:
        # Validate file type
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}"
            )
        
        # Get tier limits
        tier_code = await get_organization_tier(conn, org_id)
        if not tier_code:
            raise HTTPException(status_code=400, detail="Organization has no active subscription")
        
        limits = await get_tier_limits(conn, tier_code)
        
        # Check asset count
        asset_count = await count_organization_assets(conn, org_id)
        if asset_count >= limits["max_assets"]:
            raise HTTPException(
                status_code=400,
                detail=f"Asset limit reached ({limits['max_assets']} max for {tier_code} tier)"
            )
        
        # Check file size
        content = await file.read()
        file_size_mb = len(content) / (1024 * 1024)
        if file_size_mb > limits["max_file_size_mb"]:
            raise HTTPException(
                status_code=400,
                detail=f"File too large ({file_size_mb:.2f}MB). Max: {limits['max_file_size_mb']}MB"
            )
        
        # Reset file pointer
        await file.seek(0)
        
        # Save file
        asset_info = await save_uploaded_file(file, org_id, asset_type)
        
        # Store asset record
        asset_record = await conn.fetchrow("""
            INSERT INTO branding_assets (
                org_id, asset_type, asset_url, file_name, file_size, mime_type
            ) VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        """,
            org_id, asset_type, asset_info["asset_url"], asset_info["file_name"],
            asset_info["file_size"], asset_info["mime_type"]
        )
        
        # Update organization branding with asset URL
        url_field = f"{asset_type}_url"
        await conn.execute(f"""
            UPDATE organization_branding 
            SET {url_field} = $1, updated_at = NOW()
            WHERE org_id = $2
        """, asset_info["asset_url"], org_id)
        
        # Log upload
        await log_branding_change(
            conn, org_id, current_user["id"], "upload_asset",
            {"asset_type": asset_type, "file_name": asset_info["file_name"]}
        )
        
        return dict(asset_record)
    finally:
        await conn.close()

@router.get("/{org_id}/branding/assets/", response_model=List[BrandingAssetResponse])
async def list_branding_assets(
    org_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List all branding assets for an organization"""
    conn = await get_db_connection()
    try:
        assets = await conn.fetch("""
            SELECT * FROM branding_assets 
            WHERE org_id = $1 
            ORDER BY uploaded_at DESC
        """, org_id)
        
        return [dict(asset) for asset in assets]
    finally:
        await conn.close()

@router.delete("/{org_id}/branding/assets/{asset_id}/")
async def delete_branding_asset(
    org_id: str,
    asset_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Delete a branding asset"""
    conn = await get_db_connection()
    try:
        # Get asset info
        asset = await conn.fetchrow("""
            SELECT * FROM branding_assets 
            WHERE id = $1 AND org_id = $2
        """, asset_id, org_id)
        
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        # Delete file from filesystem
        file_path = UPLOAD_DIR / Path(asset["asset_url"]).name
        if file_path.exists():
            file_path.unlink()
        
        # Delete database record
        await conn.execute("""
            DELETE FROM branding_assets WHERE id = $1
        """, asset_id)
        
        # Clear URL in organization branding
        url_field = f"{asset['asset_type']}_url"
        await conn.execute(f"""
            UPDATE organization_branding 
            SET {url_field} = NULL, updated_at = NOW()
            WHERE org_id = $1
        """, org_id)
        
        # Log deletion
        await log_branding_change(
            conn, org_id, current_user["id"], "delete_asset",
            {"asset_id": asset_id, "asset_type": asset["asset_type"]}
        )
        
        return {"message": "Asset deleted successfully"}
    finally:
        await conn.close()

@router.get("/{org_id}/branding/audit-log/")
async def get_branding_audit_log(
    org_id: str,
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """Get branding audit log for an organization"""
    conn = await get_db_connection()
    try:
        logs = await conn.fetch("""
            SELECT 
                bal.*
            FROM branding_audit_log bal
            WHERE bal.org_id = $1
            ORDER BY bal.created_at DESC
            LIMIT $2
        """, org_id, limit)
        
        return [dict(log) for log in logs]
    finally:
        await conn.close()
