"""Plugin Management API

RESTful API endpoints for plugin marketplace, installation, and management.

Epic 11: Plugin/Extension Architecture
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Body, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from backend.database import get_db
from backend.auth_dependencies import get_current_user, require_admin
from backend.models import User
from backend.plugin_lifecycle_manager import (
    plugin_manager,
    PluginInstallRequest,
    PluginUpdateRequest,
    PluginConfigUpdate,
    PluginManifest
)

router = APIRouter(prefix="/api/v1/plugins", tags=["Plugins"])


# ==================== Data Models ====================

class PluginSummary(BaseModel):
    """Plugin summary for marketplace listing"""
    id: UUID
    slug: str
    name: str
    description: str
    author: str
    category: str
    type: str
    icon_url: Optional[str]
    is_official: bool
    is_verified: bool
    rating_average: Optional[float]
    rating_count: int
    total_installs: int
    price_monthly: Optional[float]
    is_free: bool
    tags: List[str]


class PluginDetail(PluginSummary):
    """Detailed plugin information"""
    author_email: Optional[str]
    author_url: Optional[str]
    license: Optional[str]
    homepage_url: Optional[str]
    repository_url: Optional[str]
    documentation_url: Optional[str]
    screenshots: List[str]
    keywords: List[str]
    min_platform_version: Optional[str]
    max_platform_version: Optional[str]
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]


class PluginVersionInfo(BaseModel):
    """Plugin version information"""
    id: UUID
    version: str
    changelog: Optional[str]
    is_stable: bool
    is_deprecated: bool
    file_size: Optional[int]
    downloads: int
    created_at: datetime


class PluginInstallationInfo(BaseModel):
    """Plugin installation info"""
    id: UUID
    plugin: PluginSummary
    version: str
    status: str
    enabled: bool
    auto_update: bool
    installed_at: datetime
    updated_at: datetime
    health_status: Optional[str]
    error_message: Optional[str]


class MarketplaceResponse(BaseModel):
    """Marketplace listing response"""
    plugins: List[PluginSummary]
    total: int
    page: int
    page_size: int
    has_more: bool


class PluginReviewCreate(BaseModel):
    """Create plugin review"""
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=200)
    review_text: Optional[str]


class PluginReview(BaseModel):
    """Plugin review"""
    id: UUID
    user_id: UUID
    user_name: str
    rating: int
    title: Optional[str]
    review_text: Optional[str]
    created_at: datetime
    updated_at: datetime


# ==================== Marketplace Endpoints ====================

@router.get("/marketplace", response_model=MarketplaceResponse)
async def list_marketplace_plugins(
    category: Optional[str] = Query(None, description="Filter by category"),
    type: Optional[str] = Query(None, description="Filter by type"),
    search: Optional[str] = Query(None, description="Search query"),
    featured: bool = Query(False, description="Show only featured plugins"),
    verified: bool = Query(False, description="Show only verified plugins"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Browse plugin marketplace
    
    - **category**: Filter by category (ai, monitoring, integration, analytics, etc.)
    - **type**: Filter by type (backend, frontend, hybrid, container, theme)
    - **search**: Search by name, description, or tags
    - **featured**: Show only official/featured plugins
    - **verified**: Show only verified plugins
    """
    offset = (page - 1) * page_size
    
    plugins, total = await plugin_manager.list_marketplace_plugins(
        db=db,
        category=category,
        type=type,
        search=search,
        featured=featured,
        verified=verified,
        limit=page_size,
        offset=offset
    )
    
    return MarketplaceResponse(
        plugins=[PluginSummary.from_orm(p) for p in plugins],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(plugins)) < total
    )


@router.get("/marketplace/featured", response_model=List[PluginSummary])
async def list_featured_plugins(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get featured plugins (official and highly rated)"""
    plugins, _ = await plugin_manager.list_marketplace_plugins(
        db=db,
        featured=True,
        limit=limit,
        offset=0
    )
    
    return [PluginSummary.from_orm(p) for p in plugins]


@router.get("/marketplace/trending", response_model=List[PluginSummary])
async def list_trending_plugins(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get trending plugins (most installed recently)"""
    # TODO: Implement trending algorithm based on recent installs
    plugins, _ = await plugin_manager.list_marketplace_plugins(
        db=db,
        limit=limit,
        offset=0
    )
    
    return [PluginSummary.from_orm(p) for p in plugins]


@router.get("/marketplace/categories", response_model=List[str])
async def list_categories():
    """Get list of plugin categories"""
    return [
        "ai",
        "monitoring",
        "integration",
        "analytics",
        "automation",
        "security",
        "development",
        "networking",
        "storage",
        "other"
    ]


@router.get("/marketplace/{slug}", response_model=PluginDetail)
async def get_plugin_details(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific plugin"""
    plugin = await plugin_manager.get_plugin_details(db, slug)
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    return PluginDetail.from_orm(plugin)


@router.get("/marketplace/{slug}/versions", response_model=List[PluginVersionInfo])
async def get_plugin_versions(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all available versions of a plugin"""
    plugin = await plugin_manager.get_plugin_details(db, slug)
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    versions = await plugin_manager.get_plugin_versions(db, plugin.id)
    
    return [PluginVersionInfo.from_orm(v) for v in versions]


@router.post("/marketplace/{slug}/reviews", response_model=PluginReview)
async def submit_plugin_review(
    slug: str,
    review: PluginReviewCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit a review for a plugin"""
    plugin = await plugin_manager.get_plugin_details(db, slug)
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    # TODO: Implement review submission
    # - Check if user has plugin installed
    # - Create or update review
    # - Recalculate plugin rating_average
    
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/marketplace/{slug}/reviews", response_model=List[PluginReview])
async def get_plugin_reviews(
    slug: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get reviews for a plugin"""
    plugin = await plugin_manager.get_plugin_details(db, slug)
    
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    # TODO: Implement review fetching with pagination
    
    return []


# ==================== Installation Management ====================

@router.get("/installed", response_model=List[PluginInstallationInfo])
async def list_installed_plugins(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get list of plugins installed for current user's tenant"""
    # TODO: Implement fetching installed plugins for user's tenant
    # - Join plugin_installations with plugins
    # - Filter by current_user.tenant_id
    # - Include plugin details and installation status
    
    return []


@router.post("/install")
async def install_plugin(
    request: PluginInstallRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Install a plugin for current tenant
    
    Requires admin privileges
    """
    # Require admin for plugin installation
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    # Set tenant_id and user_id from current user
    request.tenant_id = current_user.tenant_id
    request.user_id = current_user.id
    
    result = await plugin_manager.install_plugin(db, request)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/{installation_id}/uninstall")
async def uninstall_plugin(
    installation_id: UUID,
    permanent: bool = Query(False, description="Permanently delete plugin data"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Uninstall a plugin
    
    - **permanent=false**: Disable plugin but keep data (can reinstall later)
    - **permanent=true**: Permanently remove plugin and all data
    """
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    result = await plugin_manager.uninstall_plugin(
        db=db,
        installation_id=installation_id,
        user_id=current_user.id,
        permanent=permanent
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/{installation_id}/enable")
async def enable_plugin(
    installation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Enable a disabled plugin"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    result = await plugin_manager.enable_plugin(db, installation_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/{installation_id}/disable")
async def disable_plugin(
    installation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Disable an enabled plugin"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    result = await plugin_manager.disable_plugin(db, installation_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/{installation_id}/update")
async def update_plugin(
    installation_id: UUID,
    update: PluginUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update plugin to a newer version"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    # TODO: Implement plugin update
    # - Download new version
    # - Run migrations
    # - Update installation record
    # - Restart plugin services
    
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.put("/{installation_id}/config")
async def update_plugin_config(
    installation_id: UUID,
    config: PluginConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update plugin configuration"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    result = await plugin_manager.update_plugin_config(
        db=db,
        installation_id=installation_id,
        config_update=config
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("/{installation_id}/health")
async def get_plugin_health(
    installation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get plugin health status"""
    # TODO: Implement health check
    # - Check if plugin services are running
    # - Run plugin's health check endpoint
    # - Return status and metrics
    
    return {
        "status": "healthy",
        "checks": {
            "services": "running",
            "database": "connected",
            "api": "responsive"
        }
    }


@router.get("/{installation_id}/logs")
async def get_plugin_logs(
    installation_id: UUID,
    lines: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get plugin logs"""
    # TODO: Implement log retrieval
    # - Fetch logs from plugin container/process
    # - Parse and format
    # - Return recent entries
    
    return {
        "logs": [],
        "total_lines": 0
    }


# ==================== Developer Endpoints ====================

@router.post("/register")
async def register_plugin(
    manifest: PluginManifest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new plugin in the marketplace
    
    Admin only - for initial plugin registration
    """
    # TODO: Implement plugin registration
    # - Validate manifest
    # - Create plugin record
    # - Set as unpublished initially
    
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.post("/upload")
async def upload_plugin_package(
    file: UploadFile = File(...),
    version: str = Form(...),
    changelog: Optional[str] = Form(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a plugin package (.zip)
    
    Developer/Admin only
    """
    # TODO: Implement plugin upload
    # - Validate ZIP file
    # - Extract and validate manifest
    # - Calculate checksum
    # - Store in plugin storage
    # - Create plugin_version record
    
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/{plugin_id}/analytics")
async def get_plugin_analytics(
    plugin_id: UUID,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get plugin analytics
    
    Plugin developer/Admin only
    """
    # TODO: Implement analytics
    # - Fetch analytics events
    # - Aggregate by day/week/month
    # - Return installs, uninstalls, errors, etc.
    
    return {
        "plugin_id": str(plugin_id),
        "period_days": days,
        "metrics": {
            "total_installs": 0,
            "active_installs": 0,
            "total_downloads": 0,
            "daily_active_users": 0,
            "errors": 0
        },
        "timeseries": []
    }


# ==================== Admin Endpoints ====================

@router.put("/{plugin_id}/verify", dependencies=[Depends(require_admin)])
async def verify_plugin(
    plugin_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Mark plugin as verified (admin only)"""
    # TODO: Implement verification
    # - Code review completed
    # - Security scan passed
    # - Set is_verified = True
    
    return {"success": True, "message": "Plugin verified"}


@router.put("/{plugin_id}/feature", dependencies=[Depends(require_admin)])
async def feature_plugin(
    plugin_id: UUID,
    featured: bool = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Mark plugin as featured (admin only)"""
    # TODO: Implement featuring
    # - Set is_official = True (or featured flag)
    # - Show in featured section
    
    return {"success": True, "message": f"Plugin {'featured' if featured else 'unfeatured'}"}


@router.delete("/{plugin_id}/ban", dependencies=[Depends(require_admin)])
async def ban_plugin(
    plugin_id: UUID,
    reason: str = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Ban a malicious plugin (admin only)
    
    - Unpublishes plugin
    - Prevents new installs
    - Optionally disables existing installations
    """
    # TODO: Implement banning
    # - Set is_published = False
    # - Add to blacklist
    # - Notify existing users
    # - Optionally auto-uninstall
    
    return {"success": True, "message": "Plugin banned"}


@router.get("/admin/stats", dependencies=[Depends(require_admin)])
async def get_platform_plugin_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get platform-wide plugin statistics (admin only)"""
    # TODO: Implement platform stats
    # - Total plugins
    # - Total installs
    # - Top plugins
    # - Revenue metrics
    
    return {
        "total_plugins": 0,
        "published_plugins": 0,
        "verified_plugins": 0,
        "total_installations": 0,
        "active_installations": 0,
        "top_plugins": []
    }
