"""
Tenant Provisioning and Management API

Provides endpoints for creating, managing, and monitoring tenants (organizations)
in a multi-tenant Ops-Center deployment.
"""

import logging
import os
import secrets
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, EmailStr, validator
import asyncpg
from auth_dependencies import require_admin_user
from tenant_isolation import TenantIsolation, TenantQuotaManager
from org_manager import org_manager, Organization, OrgUser
from keycloak_integration import get_user_by_id

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
    except Exception as exc:
        logger.error(f"Failed to create database pool: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection failed"
        )


async def resolve_owner_display(user_id: Optional[str]) -> str:
    """Resolve owner display name/email from Keycloak user ID."""
    if not user_id:
        return "unknown"

    try:
        user = await get_user_by_id(str(user_id))
        if not user:
            return str(user_id)

        email = user.get("email")
        username = user.get("username")
        first_name = user.get("firstName")
        last_name = user.get("lastName")
        full_name = " ".join([name for name in [first_name, last_name] if name])

        return email or full_name or username or str(user_id)
    except Exception as exc:
        logger.warning(f"Failed to resolve owner from Keycloak: {exc}")
        return str(user_id)


async def check_subdomain_available(pool: asyncpg.Pool, subdomain: str, exclude_org_id: Optional[str] = None) -> bool:
    """Check if subdomain is available"""
    try:
        async with pool.acquire() as conn:
            if exclude_org_id:
                query = """
                    SELECT COUNT(*) FROM organizations
                    WHERE slug = $1 AND id != $2
                """
                count = await conn.fetchval(query, subdomain, exclude_org_id)
            else:
                query = """
                    SELECT COUNT(*) FROM organizations
                    WHERE slug = $1
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
                
                # Prepare metadata with plan_tier
                metadata = tenant_data.metadata or {}
                metadata['plan_tier'] = tenant_data.plan_tier
                
                # Create organization using actual schema
                org_query = """
                    INSERT INTO organizations (
                        id, name, slug, website,
                        is_active, created_at, updated_at, metadata_json
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    RETURNING *
                """
                
                org_row = await conn.fetchrow(
                    org_query,
                    org_id,
                    tenant_data.name,
                    tenant_data.subdomain or f"tenant-{secrets.token_urlsafe(8)}",  # slug is required
                    tenant_data.custom_domain,
                    True,  # is_active
                    datetime.utcnow(),
                    datetime.utcnow(),
                    json.dumps(metadata)
                )
                
                # Create admin user for tenant in organization_members
                member_id = f"mem_{secrets.token_urlsafe(16)}"
                user_id = tenant_data.owner_email  # Use email as user_id for now
                
                member_query = """
                    INSERT INTO organization_members (
                        id, user_id, organization_id, role, is_active, joined_at, updated_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id
                """
                
                await conn.execute(
                    member_query,
                    member_id,
                    user_id,
                    org_id,
                    'OWNER',
                    True,
                    datetime.utcnow(),
                    datetime.utcnow()
                )
                
                logger.info(f"Created tenant {org_id} with admin user {user_id}")
                
                # Sync to org_manager JSON storage for organization list compatibility
                try:
                    logger.info(f"Starting sync for tenant {org_id} to org_manager...")
                    
                    # Manually add to org_manager storage
                    orgs = org_manager._load_organizations()
                    logger.info(f"Loaded {len(orgs)} existing organizations from org_manager")
                    
                    orgs[org_id] = Organization(
                        id=org_id,
                        name=tenant_data.name,
                        plan_tier=tenant_data.plan_tier,
                        subdomain=tenant_data.subdomain,
                        custom_domain=tenant_data.custom_domain,
                        created_at=datetime.utcnow(),
                        status='active'
                    )
                    org_manager._save_organizations(orgs)
                    logger.info(f"Saved organization {org_id} to org_manager storage")
                    
                    # Add owner to org_users
                    org_users = org_manager._load_org_users()
                    org_users[org_id] = [
                        OrgUser(
                            org_id=org_id,
                            user_id=user_id,
                            role='owner',
                            joined_at=datetime.utcnow()
                        )
                    ]
                    org_manager._save_org_users(org_users)
                    logger.info(f"Saved org_users for {org_id} to org_manager storage")
                    
                    logger.info(f"Successfully synced tenant {org_id} to org_manager")
                except Exception as sync_err:
                    logger.error(f"Failed to sync to org_manager: {sync_err}", exc_info=True)
                    # Don't fail the whole operation if sync fails
                
                # Get resource counts (will be 0 for new tenant)
                resource_counts = {'users': 1, 'devices': 0, 'webhooks': 0, 'api_keys': 0, 'alerts': 0}
                
                # Extract plan_tier from metadata
                metadata_parsed = json.loads(org_row['metadata_json']) if isinstance(org_row['metadata_json'], str) else org_row['metadata_json']
                plan_tier = metadata_parsed.get('plan_tier', 'trial') if metadata_parsed else 'trial'
                
                return TenantResponse(
                    organization_id=org_row['id'],
                    name=org_row['name'],
                    plan_tier=plan_tier,
                    owner_email=tenant_data.owner_email,
                    subdomain=org_row['slug'],
                    custom_domain=org_row['website'],
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
                # Note: plan_tier is stored in metadata_json, filtering by tier would require JSON query
                # For now, we'll skip this filter as it's complex with JSON column
                # Could be enhanced later with: metadata_json::jsonb @> '{"plan_tier":"value"}'::jsonb
                pass
            
            if search:
                conditions.append(f"(name ILIKE ${param_count} OR id ILIKE ${param_count})")
                params.append(f"%{search}%")
                param_count += 1
            
            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            
            # Get total count
            count_query = f"SELECT COUNT(*) FROM organizations {where_clause}"
            total = await conn.fetchval(count_query, *params)
            
            # Get paginated results
            offset = (page - 1) * page_size
            
            list_query = f"""
                SELECT 
                    o.id,
                    o.name,
                    o.slug,
                    o.is_active,
                    o.created_at,
                    o.updated_at,
                    o.metadata_json,
                    (SELECT COUNT(*) FROM organization_members om WHERE om.organization_id = o.id) as member_count,
                    (SELECT user_id FROM organization_members om WHERE om.organization_id = o.id AND om.role = 'OWNER' LIMIT 1) as owner_id
                FROM organizations o
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_count} OFFSET ${param_count + 1}
            """
            
            params.extend([page_size, offset])
            
            rows = await conn.fetch(list_query, *params)
            
            tenants = []
            owner_cache: Dict[str, str] = {}
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
                owner_id = row['owner_id']
                if owner_id:
                    if owner_id in owner_cache:
                        owner_display = owner_cache[owner_id]
                    else:
                        owner_display = await resolve_owner_display(owner_id)
                        owner_cache[owner_id] = owner_display
                else:
                    owner_display = 'unknown'
                
                # Use plan_tier from database column, fallback to metadata_json if needed
                plan_tier = row.get('plan_tier')
                if not plan_tier:
                    # Fallback: Extract plan_tier from metadata_json
                    metadata_raw = row.get('metadata_json')
                    if metadata_raw:
                        metadata = json.loads(metadata_raw) if isinstance(metadata_raw, str) else metadata_raw
                        plan_tier = metadata.get('plan_tier', 'trial') if isinstance(metadata, dict) else 'trial'
                    else:
                        plan_tier = 'trial'
                
                tenants.append(TenantResponse(
                    organization_id=str(row['id']),
                    name=row['name'],
                    plan_tier=plan_tier,
                    owner_email=owner_display,  # Showing user_id for now
                    subdomain=row['slug'],  # Use slug as subdomain
                    custom_domain=None,  # Website column doesn't exist in schema
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
                    o.id as organization_id,
                    o.name,
                    o.tier as plan_tier,
                    o.slug as subdomain,
                    o.is_active,
                    o.created_at,
                    o.updated_at,
                    (SELECT COUNT(*) FROM organization_members om WHERE om.organization_id = o.id) as member_count,
                    (SELECT user_id FROM organization_members om WHERE om.organization_id = o.id AND om.role = 'OWNER' LIMIT 1) as owner_email
                FROM organizations o
                WHERE o.id = $1
            """
            
            row = await conn.fetchrow(query, tenant_id)
            
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tenant {tenant_id} not found"
                )
            
            resource_counts = await get_resource_counts(pool, tenant_id)
            owner_display = await resolve_owner_display(row['owner_email'])
            
            response_data = TenantResponse(
                organization_id=str(row['organization_id']),
                name=row['name'],
                plan_tier=row['plan_tier'],
                owner_email=owner_display,
                subdomain=row['subdomain'],
                custom_domain=None,  # Website column doesn't exist
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
            # First, get the current metadata to merge with plan_tier if needed
            current_row = await conn.fetchrow(
                "SELECT metadata_json FROM organizations WHERE id = $1",
                tenant_id
            )
            
            if not current_row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tenant {tenant_id} not found"
                )
            
            # Parse existing metadata
            current_metadata = current_row['metadata_json']
            if isinstance(current_metadata, str):
                current_metadata = json.loads(current_metadata) if current_metadata else {}
            elif current_metadata is None:
                current_metadata = {}
            
            # Build update query
            update_fields = []
            update_values = []
            param_count = 1
            
            if tenant_update.name is not None:
                update_fields.append(f"name = ${param_count}")
                update_values.append(tenant_update.name)
                param_count += 1
            
            if tenant_update.plan_tier is not None:
                # Update plan_tier in metadata_json
                current_metadata['plan_tier'] = tenant_update.plan_tier
            
            if tenant_update.subdomain is not None:
                # Use slug column for subdomain
                update_fields.append(f"slug = ${param_count}")
                update_values.append(tenant_update.subdomain)
                param_count += 1
            
            if tenant_update.custom_domain is not None:
                # Use website column for custom_domain
                update_fields.append(f"website = ${param_count}")
                update_values.append(tenant_update.custom_domain)
                param_count += 1
            
            if tenant_update.is_active is not None:
                update_fields.append(f"is_active = ${param_count}")
                update_values.append(tenant_update.is_active)
                param_count += 1
            
            if tenant_update.metadata is not None:
                # Merge user-provided metadata with plan_tier
                current_metadata.update(tenant_update.metadata)
            
            # Always update metadata_json to include plan_tier changes
            update_fields.append(f"metadata_json = ${param_count}")
            update_values.append(json.dumps(current_metadata))
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
                WHERE id = ${param_count}
                RETURNING *
            """
            
            row = await conn.fetchrow(query, *update_values)
            
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tenant {tenant_id} not found"
                )
            
            # Get owner user_id
            owner_query = """
                SELECT user_id FROM organization_members
                WHERE organization_id = $1 AND role = 'OWNER'
                LIMIT 1
            """
            owner_id = await conn.fetchval(owner_query, tenant_id)
            
            # Get member count
            member_count_query = """
                SELECT COUNT(*) FROM organization_members
                WHERE organization_id = $1
            """
            member_count = await conn.fetchval(member_count_query, tenant_id)
            
            # Simple resource counts
            resource_counts = {
                'users': member_count or 0,
                'devices': 0,
                'webhooks': 0,
                'api_keys': 0,
                'alerts': 0
            }
            
            # Extract plan_tier from metadata_json
            metadata_raw = row.get('metadata_json')
            if metadata_raw:
                # Parse if it's a string, otherwise use as-is
                metadata = json.loads(metadata_raw) if isinstance(metadata_raw, str) else metadata_raw
            else:
                metadata = {}
            plan_tier = metadata.get('plan_tier', 'trial') if isinstance(metadata, dict) else 'trial'
            
            # Sync update to org_manager
            try:
                logger.info(f"Starting sync of update for tenant {tenant_id} to org_manager...")
                org = org_manager.get_org(tenant_id)
                if org:
                    logger.info(f"Found existing org {tenant_id} in org_manager")
                    # Update existing org in org_manager
                    if tenant_update.name is not None:
                        org.name = tenant_update.name
                    if tenant_update.plan_tier is not None:
                        org.plan_tier = tenant_update.plan_tier
                    if tenant_update.subdomain is not None:
                        org.subdomain = tenant_update.subdomain
                    if tenant_update.custom_domain is not None:
                        org.custom_domain = tenant_update.custom_domain
                    if tenant_update.is_active is not None:
                        org.status = 'active' if tenant_update.is_active else 'suspended'
                    
                    # Save the updated org (need to manually update the storage)
                    orgs = org_manager._load_organizations()
                    orgs[tenant_id] = org
                    org_manager._save_organizations(orgs)
                    logger.info(f"Successfully synced tenant update {tenant_id} to org_manager")
                else:
                    logger.warning(f"Org {tenant_id} not found in org_manager, skipping sync")
            except Exception as sync_err:
                logger.error(f"Failed to sync update to org_manager: {sync_err}", exc_info=True)
            
            owner_display = await resolve_owner_display(owner_id)
            return TenantResponse(
                organization_id=str(row['id']),
                name=row['name'],
                plan_tier=plan_tier,
                owner_email=owner_display,
                subdomain=row.get('slug'),
                custom_domain=None,  # Website column doesn't exist
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
            check_query = "SELECT name FROM organizations WHERE id = $1"
            tenant_name = await conn.fetchval(check_query, tenant_id)
            
            if not tenant_name:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tenant {tenant_id} not found"
                )
            
            if hard_delete:
                # Hard delete - remove members first (foreign key)
                members_delete_query = "DELETE FROM organization_members WHERE organization_id = $1"
                await conn.execute(members_delete_query, tenant_id)
                
                # Delete organization record
                org_delete_query = "DELETE FROM organizations WHERE id = $1"
                await conn.execute(org_delete_query, tenant_id)
                
                logger.warning(f"Hard deleted tenant {tenant_id} ({tenant_name})")
                
                return {
                    "message": f"Tenant {tenant_name} permanently deleted",
                    "tenant_id": tenant_id
                }
            else:
                # Soft delete - mark as inactive
                soft_delete_query = """
                    UPDATE organizations
                    SET is_active = FALSE, updated_at = $1
                    WHERE id = $2
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
                    SELECT created_at FROM organization_members WHERE organization_id = $1
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
