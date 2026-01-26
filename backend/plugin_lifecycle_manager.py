"""Plugin Lifecycle Manager

Manages plugin installation, enablement, updates, and removal
with support for multi-tenant isolation and security sandboxing.

Epic 11: Plugin/Extension Architecture
"""

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4

import aiofiles
import aiohttp
import semver
from pydantic import BaseModel, Field, validator
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import (
    Plugin, PluginVersion, PluginInstallation, PluginDependency,
    PluginPermission, PluginHook, PluginAnalytics
)


class PluginManifest(BaseModel):
    """Plugin manifest schema (plugin.yaml)"""
    id: str
    name: str
    version: str
    description: str
    author: str
    author_email: Optional[str] = None
    license: str = "MIT"
    
    type: str  # backend, frontend, hybrid, container, theme
    category: str  # ai, monitoring, integration, analytics, automation, security
    
    min_platform_version: Optional[str] = None
    max_platform_version: Optional[str] = None
    python_version: Optional[str] = None
    node_version: Optional[str] = None
    
    tags: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    
    # Entry points
    entry_points: Dict[str, str] = Field(default_factory=dict)
    
    # Dependencies
    dependencies: Dict[str, Any] = Field(default_factory=dict)
    
    # Permissions
    permissions: List[str] = Field(default_factory=list)
    
    # Hooks
    hooks: List[Dict[str, Any]] = Field(default_factory=list)
    
    # API routes
    api_routes: List[Dict[str, Any]] = Field(default_factory=list)
    
    # UI slots
    ui_slots: List[str] = Field(default_factory=list)
    
    # Configuration schema
    config_schema: Dict[str, Any] = Field(default_factory=dict)
    
    # Resource limits
    resources: Dict[str, str] = Field(default_factory=dict)
    
    # Pricing
    pricing: Optional[Dict[str, Any]] = None
    
    # Links
    homepage: Optional[str] = None
    repository: Optional[str] = None
    documentation: Optional[str] = None
    
    @validator('id')
    def validate_id(cls, v):
        """Ensure plugin ID is URL-safe"""
        if not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Plugin ID must be alphanumeric with hyphens/underscores')
        return v.lower()
    
    @validator('version')
    def validate_version(cls, v):
        """Ensure version is valid semantic version"""
        try:
            semver.VersionInfo.parse(v)
        except ValueError:
            raise ValueError('Version must be valid semantic version (e.g., 1.2.3)')
        return v


class PluginInstallRequest(BaseModel):
    """Request to install a plugin"""
    plugin_slug: str
    version: Optional[str] = None  # Latest if not specified
    tenant_id: UUID
    user_id: UUID
    config: Dict[str, Any] = Field(default_factory=dict)
    auto_update: bool = True


class PluginUpdateRequest(BaseModel):
    """Request to update a plugin"""
    version: Optional[str] = None  # Latest if not specified
    config: Optional[Dict[str, Any]] = None


class PluginConfigUpdate(BaseModel):
    """Update plugin configuration"""
    config: Dict[str, Any]


class PluginLifecycleManager:
    """Manages plugin lifecycle operations"""
    
    def __init__(self):
        self.plugins_dir = Path("/var/lib/ops-center/plugins")
        self.cache_dir = Path("/var/cache/ops-center/plugins")
        self.temp_dir = Path("/tmp/ops-center-plugins")
        
        # Ensure directories exist
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    async def list_marketplace_plugins(
        self,
        db: AsyncSession,
        category: Optional[str] = None,
        type: Optional[str] = None,
        search: Optional[str] = None,
        featured: bool = False,
        verified: bool = False,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[Plugin], int]:
        """List available plugins in marketplace"""
        query = select(Plugin).where(Plugin.is_published == True)
        
        if category:
            query = query.where(Plugin.category == category)
        
        if type:
            query = query.where(Plugin.type == type)
        
        if featured:
            query = query.where(Plugin.is_official == True)
        
        if verified:
            query = query.where(Plugin.is_verified == True)
        
        if search:
            # Full-text search
            query = query.where(
                or_(
                    Plugin.name.ilike(f"%{search}%"),
                    Plugin.description.ilike(f"%{search}%"),
                    Plugin.tags.contains([search])
                )
            )
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query)
        
        # Order by rating and popularity
        query = query.order_by(
            Plugin.is_official.desc(),
            Plugin.rating_average.desc(),
            Plugin.total_installs.desc()
        )
        
        # Paginate
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        plugins = result.scalars().all()
        
        return plugins, total
    
    async def get_plugin_details(
        self,
        db: AsyncSession,
        plugin_slug: str
    ) -> Optional[Plugin]:
        """Get detailed plugin information"""
        result = await db.execute(
            select(Plugin).where(Plugin.slug == plugin_slug)
        )
        return result.scalar_one_or_none()
    
    async def get_plugin_versions(
        self,
        db: AsyncSession,
        plugin_id: UUID
    ) -> List[PluginVersion]:
        """Get all versions of a plugin"""
        result = await db.execute(
            select(PluginVersion)
            .where(PluginVersion.plugin_id == plugin_id)
            .order_by(PluginVersion.created_at.desc())
        )
        return result.scalars().all()
    
    async def install_plugin(
        self,
        db: AsyncSession,
        request: PluginInstallRequest
    ) -> Dict[str, Any]:
        """Install a plugin for a tenant"""
        try:
            # 1. Get plugin from registry
            plugin = await self.get_plugin_details(db, request.plugin_slug)
            if not plugin:
                return {"success": False, "error": "Plugin not found"}
            
            # 2. Check if already installed
            existing = await db.execute(
                select(PluginInstallation).where(
                    and_(
                        PluginInstallation.tenant_id == request.tenant_id,
                        PluginInstallation.plugin_id == plugin.id
                    )
                )
            )
            if existing.scalar_one_or_none():
                return {"success": False, "error": "Plugin already installed"}
            
            # 3. Get version to install
            if request.version:
                version_result = await db.execute(
                    select(PluginVersion).where(
                        and_(
                            PluginVersion.plugin_id == plugin.id,
                            PluginVersion.version == request.version
                        )
                    )
                )
                version = version_result.scalar_one_or_none()
            else:
                # Get latest stable version
                version_result = await db.execute(
                    select(PluginVersion)
                    .where(
                        and_(
                            PluginVersion.plugin_id == plugin.id,
                            PluginVersion.is_stable == True
                        )
                    )
                    .order_by(PluginVersion.created_at.desc())
                    .limit(1)
                )
                version = version_result.scalar_one_or_none()
            
            if not version:
                return {"success": False, "error": "No suitable version found"}
            
            # 4. Check platform compatibility
            if not await self._check_compatibility(version):
                return {
                    "success": False,
                    "error": f"Plugin requires platform version {version.min_platform_version}"
                }
            
            # 5. Download and validate plugin package
            plugin_path = await self._download_plugin(version)
            if not plugin_path:
                return {"success": False, "error": "Failed to download plugin"}
            
            # 6. Validate checksum
            if not await self._validate_checksum(plugin_path, version.checksum):
                return {"success": False, "error": "Checksum validation failed"}
            
            # 7. Extract and validate manifest
            manifest = await self._extract_and_validate(plugin_path, plugin.slug)
            if not manifest:
                return {"success": False, "error": "Invalid plugin package"}
            
            # 8. Check dependencies
            deps_ok, missing_deps = await self._check_dependencies(db, manifest, request.tenant_id)
            if not deps_ok:
                return {
                    "success": False,
                    "error": f"Missing dependencies: {', '.join(missing_deps)}"
                }
            
            # 9. Install dependencies (Python, npm)
            if not await self._install_dependencies(plugin.slug, manifest):
                return {"success": False, "error": "Failed to install dependencies"}
            
            # 10. Run database migrations
            if not await self._run_migrations(plugin.slug, manifest):
                return {"success": False, "error": "Failed to run migrations"}
            
            # 11. Create installation record
            installation = PluginInstallation(
                id=uuid4(),
                tenant_id=request.tenant_id,
                plugin_id=plugin.id,
                version_id=version.id,
                status='installed',
                enabled=True,
                auto_update=request.auto_update,
                config=request.config,
                permissions=manifest.permissions,
                installed_by=request.user_id,
                installed_at=datetime.utcnow()
            )
            db.add(installation)
            
            # 12. Register hooks
            await self._register_hooks(db, plugin.id, manifest)
            
            # 13. Update plugin stats
            plugin.total_installs += 1
            
            # 14. Track analytics
            analytics = PluginAnalytics(
                id=uuid4(),
                plugin_id=plugin.id,
                tenant_id=request.tenant_id,
                event_type='install',
                event_data={'version': version.version},
                user_id=request.user_id,
                timestamp=datetime.utcnow()
            )
            db.add(analytics)
            
            await db.commit()
            
            # 15. Enable plugin (start services)
            await self._enable_plugin(installation.id, plugin.slug, manifest)
            
            return {
                "success": True,
                "message": f"Plugin {plugin.name} installed successfully",
                "installation_id": str(installation.id),
                "version": version.version
            }
            
        except Exception as e:
            await db.rollback()
            return {"success": False, "error": str(e)}
    
    async def uninstall_plugin(
        self,
        db: AsyncSession,
        installation_id: UUID,
        user_id: UUID,
        permanent: bool = False
    ) -> Dict[str, Any]:
        """Uninstall a plugin"""
        try:
            # Get installation
            result = await db.execute(
                select(PluginInstallation)
                .where(PluginInstallation.id == installation_id)
            )
            installation = result.scalar_one_or_none()
            
            if not installation:
                return {"success": False, "error": "Installation not found"}
            
            # Get plugin info
            plugin = await db.get(Plugin, installation.plugin_id)
            
            # 1. Disable plugin first
            await self._disable_plugin(installation_id, plugin.slug)
            
            # 2. Run uninstall hooks
            await self._run_lifecycle_hook(plugin.slug, 'on_uninstall')
            
            # 3. Remove plugin files
            plugin_dir = self.plugins_dir / plugin.slug
            if plugin_dir.exists():
                shutil.rmtree(plugin_dir)
            
            if permanent:
                # 4. Delete database data (CASCADE will handle related records)
                await db.delete(installation)
                
                # 5. Decrement install count
                plugin.total_installs = max(0, plugin.total_installs - 1)
            else:
                # Soft delete: just disable
                installation.status = 'uninstalled'
                installation.enabled = False
            
            # 6. Track analytics
            analytics = PluginAnalytics(
                id=uuid4(),
                plugin_id=plugin.id,
                tenant_id=installation.tenant_id,
                event_type='uninstall',
                event_data={'permanent': permanent},
                user_id=user_id,
                timestamp=datetime.utcnow()
            )
            db.add(analytics)
            
            await db.commit()
            
            return {
                "success": True,
                "message": f"Plugin {plugin.name} uninstalled successfully"
            }
            
        except Exception as e:
            await db.rollback()
            return {"success": False, "error": str(e)}
    
    async def enable_plugin(
        self,
        db: AsyncSession,
        installation_id: UUID
    ) -> Dict[str, Any]:
        """Enable an installed plugin"""
        try:
            installation = await db.get(PluginInstallation, installation_id)
            if not installation:
                return {"success": False, "error": "Installation not found"}
            
            plugin = await db.get(Plugin, installation.plugin_id)
            
            # Load manifest
            manifest_path = self.plugins_dir / plugin.slug / "plugin.yaml"
            if not manifest_path.exists():
                return {"success": False, "error": "Plugin manifest not found"}
            
            import yaml
            with open(manifest_path, 'r') as f:
                manifest_data = yaml.safe_load(f)
            manifest = PluginManifest(**manifest_data)
            
            # Start plugin services
            await self._enable_plugin(installation_id, plugin.slug, manifest)
            
            # Run on_enable hook
            await self._run_lifecycle_hook(plugin.slug, 'on_enable')
            
            # Update status
            installation.enabled = True
            installation.status = 'enabled'
            installation.last_enabled_at = datetime.utcnow()
            
            await db.commit()
            
            return {"success": True, "message": f"Plugin {plugin.name} enabled"}
            
        except Exception as e:
            await db.rollback()
            return {"success": False, "error": str(e)}
    
    async def disable_plugin(
        self,
        db: AsyncSession,
        installation_id: UUID
    ) -> Dict[str, Any]:
        """Disable an enabled plugin"""
        try:
            installation = await db.get(PluginInstallation, installation_id)
            if not installation:
                return {"success": False, "error": "Installation not found"}
            
            plugin = await db.get(Plugin, installation.plugin_id)
            
            # Stop plugin services
            await self._disable_plugin(installation_id, plugin.slug)
            
            # Run on_disable hook
            await self._run_lifecycle_hook(plugin.slug, 'on_disable')
            
            # Update status
            installation.enabled = False
            installation.status = 'disabled'
            installation.last_disabled_at = datetime.utcnow()
            
            await db.commit()
            
            return {"success": True, "message": f"Plugin {plugin.name} disabled"}
            
        except Exception as e:
            await db.rollback()
            return {"success": False, "error": str(e)}
    
    async def update_plugin_config(
        self,
        db: AsyncSession,
        installation_id: UUID,
        config_update: PluginConfigUpdate
    ) -> Dict[str, Any]:
        """Update plugin configuration"""
        try:
            installation = await db.get(PluginInstallation, installation_id)
            if not installation:
                return {"success": False, "error": "Installation not found"}
            
            plugin = await db.get(Plugin, installation.plugin_id)
            
            # Merge configs
            old_config = installation.config or {}
            new_config = {**old_config, **config_update.config}
            
            # Run on_config_change hook
            await self._run_lifecycle_hook(
                plugin.slug,
                'on_config_change',
                old_config=old_config,
                new_config=new_config
            )
            
            # Update config
            installation.config = new_config
            installation.updated_at = datetime.utcnow()
            
            await db.commit()
            
            return {
                "success": True,
                "message": "Configuration updated",
                "config": new_config
            }
            
        except Exception as e:
            await db.rollback()
            return {"success": False, "error": str(e)}
    
    # Private helper methods
    
    async def _check_compatibility(self, version: PluginVersion) -> bool:
        """Check if plugin version is compatible with platform"""
        # TODO: Implement actual version checking against PLATFORM_VERSION
        return True
    
    async def _download_plugin(self, version: PluginVersion) -> Optional[Path]:
        """Download plugin package from URL"""
        try:
            download_path = self.cache_dir / f"{version.id}.zip"
            
            if download_path.exists():
                return download_path
            
            async with aiohttp.ClientSession() as session:
                async with session.get(version.download_url) as response:
                    if response.status == 200:
                        async with aiofiles.open(download_path, 'wb') as f:
                            await f.write(await response.read())
                        return download_path
            
            return None
            
        except Exception as e:
            print(f"Download error: {e}")
            return None
    
    async def _validate_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """Validate file checksum"""
        if not expected_checksum:
            return True  # No checksum to validate
        
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest() == expected_checksum
    
    async def _extract_and_validate(
        self,
        zip_path: Path,
        plugin_slug: str
    ) -> Optional[PluginManifest]:
        """Extract plugin and validate manifest"""
        try:
            plugin_dir = self.plugins_dir / plugin_slug
            
            # Remove existing if present
            if plugin_dir.exists():
                shutil.rmtree(plugin_dir)
            
            # Extract zip
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(plugin_dir)
            
            # Load and validate manifest
            manifest_path = plugin_dir / "plugin.yaml"
            if not manifest_path.exists():
                return None
            
            import yaml
            with open(manifest_path, 'r') as f:
                manifest_data = yaml.safe_load(f)
            
            manifest = PluginManifest(**manifest_data)
            return manifest
            
        except Exception as e:
            print(f"Extract/validate error: {e}")
            return None
    
    async def _check_dependencies(
        self,
        db: AsyncSession,
        manifest: PluginManifest,
        tenant_id: UUID
    ) -> Tuple[bool, List[str]]:
        """Check if all plugin dependencies are satisfied"""
        if 'plugins' not in manifest.dependencies:
            return True, []
        
        missing = []
        for dep in manifest.dependencies['plugins']:
            dep_slug = dep.get('slug')
            
            # Check if dependency is installed for this tenant
            result = await db.execute(
                select(PluginInstallation)
                .join(Plugin)
                .where(
                    and_(
                        Plugin.slug == dep_slug,
                        PluginInstallation.tenant_id == tenant_id,
                        PluginInstallation.enabled == True
                    )
                )
            )
            
            if not result.scalar_one_or_none():
                missing.append(dep_slug)
        
        return len(missing) == 0, missing
    
    async def _install_dependencies(
        self,
        plugin_slug: str,
        manifest: PluginManifest
    ) -> bool:
        """Install Python and npm dependencies"""
        try:
            plugin_dir = self.plugins_dir / plugin_slug
            
            # Install Python dependencies
            if manifest.dependencies.get('python'):
                requirements = "\n".join(manifest.dependencies['python'])
                req_file = plugin_dir / "requirements.txt"
                
                with open(req_file, 'w') as f:
                    f.write(requirements)
                
                result = subprocess.run(
                    ['pip', 'install', '-r', str(req_file)],
                    capture_output=True,
                    cwd=str(plugin_dir)
                )
                
                if result.returncode != 0:
                    print(f"Python deps install failed: {result.stderr}")
                    return False
            
            # Install npm dependencies
            if manifest.dependencies.get('npm') and (plugin_dir / 'frontend').exists():
                frontend_dir = plugin_dir / 'frontend'
                
                result = subprocess.run(
                    ['npm', 'install'],
                    capture_output=True,
                    cwd=str(frontend_dir)
                )
                
                if result.returncode != 0:
                    print(f"npm deps install failed: {result.stderr}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"Dependency installation error: {e}")
            return False
    
    async def _run_migrations(
        self,
        plugin_slug: str,
        manifest: PluginManifest
    ) -> bool:
        """Run plugin database migrations"""
        # TODO: Implement migration runner
        return True
    
    async def _register_hooks(
        self,
        db: AsyncSession,
        plugin_id: UUID,
        manifest: PluginManifest
    ):
        """Register plugin hooks in database"""
        for hook_def in manifest.hooks:
            hook = PluginHook(
                id=uuid4(),
                plugin_id=plugin_id,
                hook_name=hook_def['name'],
                handler_function=hook_def['handler'],
                priority=hook_def.get('priority', 10),
                is_active=True
            )
            db.add(hook)
    
    async def _enable_plugin(
        self,
        installation_id: UUID,
        plugin_slug: str,
        manifest: PluginManifest
    ):
        """Start plugin services"""
        plugin_dir = self.plugins_dir / plugin_slug
        
        # If container-based plugin, start docker-compose
        if manifest.type == 'container':
            compose_file = plugin_dir / 'docker' / 'docker-compose.yml'
            if compose_file.exists():
                subprocess.run(
                    ['docker-compose', '-f', str(compose_file), 'up', '-d'],
                    cwd=str(plugin_dir / 'docker')
                )
    
    async def _disable_plugin(
        self,
        installation_id: UUID,
        plugin_slug: str
    ):
        """Stop plugin services"""
        plugin_dir = self.plugins_dir / plugin_slug
        
        # Stop docker-compose if exists
        compose_file = plugin_dir / 'docker' / 'docker-compose.yml'
        if compose_file.exists():
            subprocess.run(
                ['docker-compose', '-f', str(compose_file), 'down'],
                cwd=str(plugin_dir / 'docker')
            )
    
    async def _run_lifecycle_hook(
        self,
        plugin_slug: str,
        hook_name: str,
        **kwargs
    ):
        """Run a plugin lifecycle hook"""
        # TODO: Implement dynamic Python module loading and hook execution
        pass


# Singleton instance
plugin_manager = PluginLifecycleManager()
