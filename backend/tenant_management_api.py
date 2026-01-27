"""
Tenant Provisioning and Management API

Provides endpoints for creating, managing, and monitoring tenants (organizations)
in a multi-tenant Ops-Center deployment.
"""

import logging
import os
import secrets
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, EmailStr, validator
import asyncpg
from auth_dependencies import require_admin_user
from tenant_isolation import TenantIsolation, TenantQuotaManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/tenants", tags=["tenant-management"])


# Pydantic models
class TenantCreate(BaseModel):
    """Create new tenant"""
    name: str = Field(..., min_length=1, max_length=100, description="Organization name")
    plan_tier: str = Field("trial", description="Subscription tier")
    owner_email: EmailStr = Field(..., description="Primary admin email")
    owner_name: str = Field(..., min_length=1, max_length=100)
    subdomain: Optional[str] = Field(None, description="Subdomain for tenant")
    custom_domain: Optional[str] = Field(None, description="Custom domain")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @validator('plan_tier')
    def validate_tier(cls, v):
        allowed_tiers = ['trial', 'starter', 'professional', 'enterprise']
        if v not in allowed_tiers:
            raise ValueError(f"Invalid tier. Must be one of: {allowed_tiers}")
        return v
    
    @validator('subdomain')
    def validate_subdomain(cls, v):
        if v:
            # Only allow alphanumeric and hyphens
            if not v.replace('-', '').isalnum():
                raise ValueError("Subdomain must be alphanumeric (hyphens allowed)")
            # Reserved subdomains
            reserved = ['www', 'api', 'admin', 'app', 'dashboard', 'mail', 'smtp']
            if v.lower() in reserved:
                raise ValueError(f"Subdomain '{v}' is reserved")
        return v


class TenantUpdate(BaseModel):
    """Update tenant details"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    plan_tier: Optional[str] = None
    subdomain: Optional[str] = None
    custom_domain: Optional[str] = None
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class TenantResponse(BaseModel):
    """Tenant details response"""
    organization_id: str
    name: str
    plan_tier: str
    owner_email: str
    subdomain: Optional[str]
    custom_domain: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    member_count: int
    resource_counts: Dict[str, int]
    quota_status: Optional[Dict[str, Any]] = None


class TenantStats(BaseModel):
    """Tenant usage statistics"""
    organization_id: str
    name: str
    plan_tier: str
    user_count: int
    device_count: int
    webhook_count: int
    api_key_count: int
    alert_count: int
    storage_used_mb: float
    api_calls_30d: int
    last_activity: Optional[datetime]


class TenantListResponse(BaseModel):
    """List of tenants with pagination"""
    tenants: List[TenantResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# Database helpers
async def get_db_pool() -> asyncpg.Pool:
    """Get database connection pool"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="DATABASE_URL not configured"
        )
    
    try:
        pool = await asyncpg.create_pool(db_url)
        return pool
    except Exception as e:
        logger.error(f"Failed to create database pool: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection failed"
        )


async def check_subdomain_available(pool: asyncpg.Pool, subdomain: str, exclude_org_id: Optional[str] = None) -> bool:
    """Check if subdomain is available"""
    try:
        async with pool.acquire() as conn:
            if exclude_org_id:
                query = """
                    SELECT COUNT(*) FROM organizations
                    WHERE subdomain = $1 AND organization_id != $2
                """
                count = await conn.fetchval(query, subdomain, exclude_org_id)
            else:
                query = """
                    SELECT COUNT(*) FROM organizations
                    WHERE subdomain = $1
                """
                count = await conn.fetchval(query, subdomain)
            
            return count == 0
    except Exception as e:
        logger.error(f"Error checking subdomain availability: {e}")
        return False


async def get_resource_counts(pool: asyncpg.Pool, org_id: str) -> Dict[str, int]:
    """Get count of resources for organization"""
    counts = {}
    
    resource_types = ['users', 'devices', 'webhooks', 'api_keys', 'alerts']
    
    for resource_type in resource_types:
        count = await TenantIsolation.get_tenant_resource_count(pool, org_id, resource_type)
        counts[resource_type] = count
    
    return counts


# API endpoints
@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    user: dict = Depends(require_admin_user)
):
    """
    Create a new tenant (organization)
    
    This provisions a complete isolated tenant with:
    - Organization record
    - Admin user account
    - Default settings
    - Optional subdomain
    """
    pool = await get_db_pool()
    
    try:
        # Validate subdomain if provided
        if tenant_data.subdomain:
            available = await check_subdomain_available(pool, tenant_data.subdomain)
            if not available:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Subdomain '{tenant_data.subdomain}' is already taken"
                )
        
        async with pool.acquire() as conn:
            async with conn.transaction():
                # Generate organization ID
                org_id = f"org_{secrets.token_urlsafe(16)}"
                
                # Create organization
                org_query = """
                    INSERT INTO organizations (
                        organization_id, name, plan_tier, subdomain, custom_domain,
                        is_active, created_at, updated_at, metadata
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    RETURNING *
                """
                
                org_row = await conn.fetchrow(
                    org_query,
                    org_id,
                    tenant_data.name,
                    tenant_data.plan_tier,
                    tenant_data.subdomain,
                    tenant_data.custom_domain,
                    True,  # is_active
                    datetime.utcnow(),
                    datetime.utcnow(),
                    tenant_data.metadata
                )
                
                # Create admin user for tenant
                user_id = f"usr_{secrets.token_urlsafe(16)}"
                temp_password = secrets.token_urlsafe(16)
                
                user_query = """
                    INSERT INTO users (
                        user_id, email, name, organization_id,
                        subscription_tier, is_active, created_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING user_id
                """
                
                await conn.execute(
                    user_query,
                    user_id,
                    tenant_data.owner_email,
                    tenant_data.owner_name,
                    org_id,
                    tenant_data.plan_tier,
                    True,
                    datetime.utcnow()
                )
                
                logger.info(f"Created tenant {org_id} with admin user {user_id}")
                
                # Get resource counts (will be 0 for new tenant)
                resource_counts = {'users': 1, 'devices': 0, 'webhooks': 0, 'api_keys': 0, 'alerts': 0}
                
                return TenantResponse(
                    organization_id=org_row['organization_id'],
                    name=org_row['name'],
                    plan_tier=org_row['plan_tier'],
                    owner_email=tenant_data.owner_email,
                    subdomain=org_row['subdomain'],
                    custom_domain=org_row['custom_domain'],
                    is_active=org_row['is_active'],
                    created_at=org_row['created_at'],
                    updated_at=org_row['updated_at'],
                    member_count=1,
                    resource_counts=resource_counts
                )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating tenant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tenant: {str(e)}"
        )
    finally:
        await pool.close()


@router.get("/", response_model=TenantListResponse)
async def list_tenants(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    tier: Optional[str] = None,
    active_only: bool = True,
    search: Optional[str] = None,
    user: dict = Depends(require_admin_user)
):
    """
    List all tenants with pagination and filtering
    """
    pool = await get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            # Build query
            conditions = []
            params = []
            param_count = 1
            
            if active_only:
                conditions.append(f"is_active = ${param_count}")
                params.append(True)
                param_count += 1
            
            if tier:
                conditions.append(f"plan_tier = ${param_count}")
                params.append(tier)
                param_count += 1
            
            if search:
                conditions.append(f"(name ILIKE ${param_count} OR organization_id ILIKE ${param_count})")
                params.append(f"%{search}%")
                param_count += 1
            
            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            
            # Get total count
            count_query = f"SELECT COUNT(*) FROM organizations {where_clause}"
            total = await conn.fetchval(count_query, *params)
            
            # Get paginated results
            offset = (page - 1) * page_size
            params.extend([page_size, offset])
            
            list_query = f"""
                SELECT 
                    o.id,
                    o.name,
                    o.slug,
                    o.website,
                    o.is_active,
                    o.created_at,
                    o.updated_at,
                    (SELECT COUNT(*) FROM organization_members om WHERE om.organization_id = o.id) as member_count,
                    (SELECT user_id FROM organization_members om WHERE om.organization_id = o.id AND om.role = 'OWNER' LIMIT 1) as owner_id
                FROM organizations o
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_count} OFFSET ${param_count + 1}
            """
            
            rows = await conn.fetch(list_query, *params)
            
            tenants = []
            for row in rows:
                # Simple resource counts
                resource_counts = {
                    'users': row['member_count'],
                    'devices': 0,
                    'webhooks': 0,
                    'api_keys': 0,
                    'alerts': 0
                }
                
                # Get owner info - show user_id (could enhance to fetch email from Keycloak later)
                owner_display = row['owner_id'] if row['owner_id'] else 'unknown'
                
                tenants.append(TenantResponse(
                    organization_id=row['id'],
                    name=row['name'],
                    plan_tier='trial',  # Default since column doesn't exist
                    owner_email=owner_display,  # Showing user_id for now
                    subdomain=row['slug'],  # Use slug as subdomain
                    custom_domain=row['website'],
                    is_active=row['is_active'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    member_count=row['member_count'],
                    resource_counts=resource_counts
                ))
            
            return TenantListResponse(
                tenants=tenants,
                total=total,
                page=page,
                page_size=page_size,
                has_more=(page * page_size) < total
            )
        
    finally:
        await pool.close()


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    include_quota: bool = False,
    user: dict = Depends(require_admin_user)
):
    """
    Get detailed information about a specific tenant
    """
    pool = await get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            query = """
                SELECT 
                    o.*,
                    (SELECT COUNT(*) FROM users WHERE organization_id = o.organization_id) as member_count,
                    (SELECT email FROM users WHERE organization_id = o.organization_id ORDER BY created_at LIMIT 1) as owner_email
                FROM organizations o
                WHERE organization_id = $1
            """
            
            row = await conn.fetchrow(query, tenant_id)
            
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tenant {tenant_id} not found"
                )
            
            resource_counts = await get_resource_counts(pool, tenant_id)
            
            response_data = TenantResponse(
                organization_id=row['organization_id'],
                name=row['name'],
                plan_tier=row['plan_tier'],
                owner_email=row['owner_email'] or 'unknown',
                subdomain=row['subdomain'],
                custom_domain=row['custom_domain'],
                is_active=row['is_active'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                member_count=row['member_count'],
                resource_counts=resource_counts
            )
            
            # Add quota status if requested
            if include_quota:
                quota_manager = TenantQuotaManager(pool)
                quota_status = await quota_manager.get_quota_status(tenant_id)
                response_data.quota_status = quota_status
            
            return response_data
        
    finally:
        await pool.close()


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    tenant_update: TenantUpdate,
    user: dict = Depends(require_admin_user)
):
    """
    Update tenant details
    """
    pool = await get_db_pool()
    
    try:
        # Validate subdomain if being updated
        if tenant_update.subdomain:
            available = await check_subdomain_available(pool, tenant_update.subdomain, tenant_id)
            if not available:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Subdomain '{tenant_update.subdomain}' is already taken"
                )
        
        async with pool.acquire() as conn:
            # Build update query
            update_fields = []
            update_values = []
            param_count = 1
            
            if tenant_update.name is not None:
                update_fields.append(f"name = ${param_count}")
                update_values.append(tenant_update.name)
                param_count += 1
            
            if tenant_update.plan_tier is not None:
                update_fields.append(f"plan_tier = ${param_count}")
                update_values.append(tenant_update.plan_tier)
                param_count += 1
            
            if tenant_update.subdomain is not None:
                update_fields.append(f"subdomain = ${param_count}")
                update_values.append(tenant_update.subdomain)
                param_count += 1
            
            if tenant_update.custom_domain is not None:
                update_fields.append(f"custom_domain = ${param_count}")
                update_values.append(tenant_update.custom_domain)
                param_count += 1
            
            if tenant_update.is_active is not None:
                update_fields.append(f"is_active = ${param_count}")
                update_values.append(tenant_update.is_active)
                param_count += 1
            
            if tenant_update.metadata is not None:
                update_fields.append(f"metadata = ${param_count}")
                update_values.append(tenant_update.metadata)
                param_count += 1
            
            if not update_fields:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No fields to update"
                )
            
            update_fields.append(f"updated_at = ${param_count}")
            update_values.append(datetime.utcnow())
            param_count += 1
            
            update_values.append(tenant_id)
            
            query = f"""
                UPDATE organizations
                SET {', '.join(update_fields)}
                WHERE organization_id = ${param_count}
                RETURNING *
            """
            
            row = await conn.fetchrow(query, *update_values)
            
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tenant {tenant_id} not found"
                )
            
            # Get owner email
            owner_query = """
                SELECT email FROM users
                WHERE organization_id = $1
                ORDER BY created_at
                LIMIT 1
            """
            owner_email = await conn.fetchval(owner_query, tenant_id)
            
            # Get member count
            member_count_query = """
                SELECT COUNT(*) FROM users
                WHERE organization_id = $1
            """
            member_count = await conn.fetchval(member_count_query, tenant_id)
            
            resource_counts = await get_resource_counts(pool, tenant_id)
            
            return TenantResponse(
                organization_id=row['organization_id'],
                name=row['name'],
                plan_tier=row['plan_tier'],
                owner_email=owner_email or 'unknown',
                subdomain=row['subdomain'],
                custom_domain=row['custom_domain'],
                is_active=row['is_active'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                member_count=member_count or 0,
                resource_counts=resource_counts
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tenant: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tenant: {str(e)}"
        )
    finally:
        await pool.close()


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    hard_delete: bool = Query(False, description="Permanently delete all data"),
    user: dict = Depends(require_admin_user)
):
    """
    Delete a tenant
    
    - If hard_delete=False: Soft delete (mark as inactive)
    - If hard_delete=True: Permanently delete all tenant data
    """
    pool = await get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            # Check if tenant exists
            check_query = "SELECT name FROM organizations WHERE organization_id = $1"
            tenant_name = await conn.fetchval(check_query, tenant_id)
            
            if not tenant_name:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tenant {tenant_id} not found"
                )
            
            if hard_delete:
                # Hard delete - remove all data
                deleted_counts = await TenantIsolation.delete_tenant_data(pool, tenant_id)
                
                # Delete organization record
                org_delete_query = "DELETE FROM organizations WHERE organization_id = $1"
                await conn.execute(org_delete_query, tenant_id)
                
                logger.warning(f"Hard deleted tenant {tenant_id} ({tenant_name})")
                
                return {
                    "message": f"Tenant {tenant_name} permanently deleted",
                    "tenant_id": tenant_id,
                    "deleted_records": deleted_counts
                }
            else:
                # Soft delete - mark as inactive
                soft_delete_query = """
                    UPDATE organizations
                    SET is_active = FALSE, updated_at = $1
                    WHERE organization_id = $2
                """
                await conn.execute(soft_delete_query, datetime.utcnow(), tenant_id)
                
                logger.info(f"Soft deleted tenant {tenant_id} ({tenant_name})")
                
                return {
                    "message": f"Tenant {tenant_name} deactivated",
                    "tenant_id": tenant_id,
                    "note": "Data preserved. Set is_active=true to reactivate."
                }
        
    finally:
        await pool.close()


@router.get("/{tenant_id}/stats", response_model=TenantStats)
async def get_tenant_stats(
    tenant_id: str,
    user: dict = Depends(require_admin_user)
):
    """
    Get usage statistics for a tenant
    """
    pool = await get_db_pool()
    
    try:
        async with pool.acquire() as conn:
            # Get tenant info
            org_query = """
                SELECT name, plan_tier FROM organizations
                WHERE organization_id = $1
            """
            org_row = await conn.fetchrow(org_query, tenant_id)
            
            if not org_row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tenant {tenant_id} not found"
                )
            
            # Get resource counts
            resource_counts = await get_resource_counts(pool, tenant_id)
            
            # Get API calls (last 30 days) - placeholder
            # You'd need to implement actual API call tracking
            api_calls_30d = 0
            
            # Get storage used - placeholder
            storage_used_mb = 0.0
            
            # Get last activity
            last_activity_query = """
                SELECT MAX(created_at) FROM (
                    SELECT created_at FROM users WHERE organization_id = $1
                    UNION ALL
                    SELECT last_heartbeat FROM edge_devices WHERE organization_id = $1
                    UNION ALL
                    SELECT created_at FROM webhooks WHERE organization_id = $1
                ) activities
            """
            last_activity = await conn.fetchval(last_activity_query, tenant_id)
            
            return TenantStats(
                organization_id=tenant_id,
                name=org_row['name'],
                plan_tier=org_row['plan_tier'],
                user_count=resource_counts.get('users', 0),
                device_count=resource_counts.get('devices', 0),
                webhook_count=resource_counts.get('webhooks', 0),
                api_key_count=resource_counts.get('api_keys', 0),
                alert_count=resource_counts.get('alerts', 0),
                storage_used_mb=storage_used_mb,
                api_calls_30d=api_calls_30d,
                last_activity=last_activity
            )
        
    finally:
        await pool.close()


@router.get("/{tenant_id}/quota")
async def get_tenant_quota(
    tenant_id: str,
    user: dict = Depends(require_admin_user)
):
    """
    Get quota status for tenant
    """
    pool = await get_db_pool()
    
    try:
        quota_manager = TenantQuotaManager(pool)
        quota_status = await quota_manager.get_quota_status(tenant_id)
        
        return {
            "tenant_id": tenant_id,
            "quotas": quota_status
        }
        
    finally:
        await pool.close()
