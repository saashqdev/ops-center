"""
Ops-Center Edge Device Agent
Epic 7.1: Edge Device Management

Lightweight Python agent that runs on edge devices to:
- Send heartbeats to Ops-Center
- Apply configuration updates
- Report metrics and logs
- Handle OTA updates
"""

import asyncio
import aiohttp
import platform
import psutil
import logging
import json
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EdgeAgent:
    """Main Edge Device Agent"""
    
    def __init__(
        self,
        device_id: str,
        auth_token: str,
        cloud_url: str,
        config_file: str = "/etc/edge-agent/config.json"
    ):
        self.device_id = device_id
        self.auth_token = auth_token
        self.cloud_url = cloud_url.rstrip('/')
        self.config_file = config_file
        self.heartbeat_interval = 30  # seconds
        self.config_version = 0
        self.running = False
        
    async def start(self):
        """Start the agent and all background tasks"""
        logger.info(f"Starting Edge Agent for device: {self.device_id}")
        self.running = True
        
        try:
            await asyncio.gather(
                self.heartbeat_loop(),
                self.config_watcher(),
                self.metrics_collector(),
                self.ota_update_checker(),
                return_exceptions=True
            )
        except Exception as e:
            logger.error(f"Agent crashed: {e}")
            self.running = False
    
    async def heartbeat_loop(self):
        """Send periodic heartbeats to cloud"""
        while self.running:
            try:
                status = await self.collect_status()
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.cloud_url}/api/v1/edge/devices/{self.device_id}/heartbeat",
                        json=status,
                        headers={"Authorization": f"Bearer {self.auth_token}"}
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            
                            # Check for pending configuration updates
                            if "pending_config" in data:
                                logger.info(f"Pending config update detected: v{data['pending_config']['version']}")
                                await self.apply_config(data['pending_config'])
                        else:
                            logger.warning(f"Heartbeat failed: HTTP {resp.status}")
                            
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
            
            await asyncio.sleep(self.heartbeat_interval)
    
    async def collect_status(self) -> Dict[str, Any]:
        """Collect current device status"""
        # Get system uptime
        boot_time = psutil.boot_time()
        uptime = int(datetime.now().timestamp() - boot_time)
        
        # Get service status (check Docker containers)
        services = await self.check_services()
        
        # Get current metrics
        metrics = await self.collect_metrics()
        
        # Get IP address
        import socket
        try:
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)
        except:
            ip_address = None
        
        return {
            "status": "online",
            "uptime": uptime,
            "services": services,
            "metrics": metrics,
            "ip_address": ip_address
        }
    
    async def check_services(self) -> list:
        """Check status of local services (Docker containers)"""
        services = []
        
        try:
            # Check if Docker is available
            proc = await asyncio.create_subprocess_exec(
                'docker', 'ps', '--format', '{{.Names}}:{{.Status}}',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                lines = stdout.decode().strip().split('\n')
                for line in lines:
                    if ':' in line:
                        name, status = line.split(':', 1)
                        services.append({
                            "name": name,
                            "status": "running" if "Up" in status else "stopped"
                        })
        except Exception as e:
            logger.warning(f"Failed to check Docker services: {e}")
        
        return services
    
    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect system metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # Network stats (total bytes sent/received)
            net_io = psutil.net_io_counters()
            
            metrics = {
                "cpu": {
                    "percent": cpu_percent,
                    "cores": psutil.cpu_count()
                },
                "memory": {
                    "percent": memory_percent,
                    "total_mb": memory.total // (1024 * 1024),
                    "available_mb": memory.available // (1024 * 1024)
                },
                "disk": {
                    "percent": disk_percent,
                    "total_gb": disk.total // (1024 * 1024 * 1024),
                    "free_gb": disk.free // (1024 * 1024 * 1024)
                },
                "network": {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv
                }
            }
            
            # Try to get GPU metrics if nvidia-smi is available
            try:
                proc = await asyncio.create_subprocess_exec(
                    'nvidia-smi',
                    '--query-gpu=utilization.gpu,memory.used,temperature.gpu',
                    '--format=csv,noheader,nounits',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await proc.communicate()
                
                if proc.returncode == 0:
                    values = stdout.decode().strip().split(',')
                    if len(values) >= 3:
                        metrics["gpu"] = {
                            "utilization": float(values[0].strip()),
                            "memory_used_mb": float(values[1].strip()),
                            "temperature": float(values[2].strip())
                        }
            except:
                pass  # GPU not available
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            return {}
    
    async def config_watcher(self):
        """Watch for configuration changes"""
        while self.running:
            try:
                # Check if there's a new config on server
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.cloud_url}/api/v1/edge/devices/{self.device_id}/config",
                        headers={"Authorization": f"Bearer {self.auth_token}"}
                    ) as resp:
                        if resp.status == 200:
                            config_data = await resp.json()
                            
                            if config_data['version'] > self.config_version:
                                logger.info(f"New config version {config_data['version']} available")
                                await self.apply_config(config_data)
                
            except Exception as e:
                logger.error(f"Config watcher error: {e}")
            
            await asyncio.sleep(60)  # Check every minute
    
    async def apply_config(self, config_data: Dict[str, Any]):
        """Apply new configuration"""
        try:
            logger.info(f"Applying configuration version {config_data['version']}")
            
            # Save config to file
            config_path = Path(self.config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w') as f:
                json.dump(config_data['data'], f, indent=2)
            
            # Update docker-compose if needed
            if 'services' in config_data['data']:
                await self.update_services(config_data['data']['services'])
            
            # Update vLLM configuration if needed
            if 'vllm' in config_data['data']:
                await self.update_vllm_config(config_data['data']['vllm'])
            
            self.config_version = config_data['version']
            
            # Notify cloud that config was applied
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.cloud_url}/api/v1/edge/devices/{self.device_id}/config/applied",
                    json={
                        "config_id": config_data.get('config_id'),
                        "success": True
                    },
                    headers={"Authorization": f"Bearer {self.auth_token}"}
                ) as resp:
                    if resp.status == 200:
                        logger.info("Configuration applied successfully")
            
        except Exception as e:
            logger.error(f"Failed to apply config: {e}")
            
            # Notify cloud of failure
            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(
                        f"{self.cloud_url}/api/v1/edge/devices/{self.device_id}/config/applied",
                        json={
                            "config_id": config_data.get('config_id'),
                            "success": False,
                            "error_message": str(e)
                        },
                        headers={"Authorization": f"Bearer {self.auth_token}"}
                    )
            except:
                pass
    
    async def update_services(self, services_config: Dict[str, bool]):
        """Update which services are running"""
        logger.info(f"Updating services: {services_config}")
        
        # This would typically update docker-compose.yml and restart services
        # For now, just log what would happen
        for service, enabled in services_config.items():
            action = "start" if enabled else "stop"
            logger.info(f"Would {action} service: {service}")
            
            # In production:
            # if enabled:
            #     await asyncio.create_subprocess_exec('docker-compose', 'up', '-d', service)
            # else:
            #     await asyncio.create_subprocess_exec('docker-compose', 'stop', service)
    
    async def update_vllm_config(self, vllm_config: Dict[str, Any]):
        """Update vLLM configuration"""
        logger.info(f"Updating vLLM config: {vllm_config}")
        
        # This would update vLLM environment variables and restart
        # For now, just log
        if 'model' in vllm_config:
            logger.info(f"Would update vLLM model to: {vllm_config['model']}")
        
        if 'gpu_memory_util' in vllm_config:
            logger.info(f"Would set GPU memory util to: {vllm_config['gpu_memory_util']}")
    
    async def metrics_collector(self):
        """Collect and send detailed metrics periodically"""
        while self.running:
            try:
                metrics = await self.collect_metrics()
                
                # Send to cloud
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.cloud_url}/api/v1/edge/devices/{self.device_id}/metrics",
                        json={
                            "metrics": [
                                {
                                    "timestamp": datetime.utcnow().isoformat(),
                                    "metric_type": metric_type,
                                    "value": value
                                }
                                for metric_type, value in metrics.items()
                            ]
                        },
                        headers={"Authorization": f"Bearer {self.auth_token}"}
                    ) as resp:
                        if resp.status != 200:
                            logger.warning(f"Failed to send metrics: HTTP {resp.status}")
                
            except Exception as e:
                logger.error(f"Metrics collector error: {e}")
            
            await asyncio.sleep(300)  # Every 5 minutes
    
    async def send_log(self, level: str, message: str, service_name: Optional[str] = None):
        """Send log entry to cloud"""
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"{self.cloud_url}/api/v1/edge/devices/{self.device_id}/logs",
                    json={
                        "log_level": level,
                        "message": message,
                        "service_name": service_name
                    },
                    headers={"Authorization": f"Bearer {self.auth_token}"}
                )
        except Exception as e:
            logger.error(f"Failed to send log: {e}")
    
    # ==================== OTA Update Handling ====================
    
    async def ota_update_checker(self):
        """Check for OTA updates periodically"""
        while self.running:
            try:
                # Check for available updates
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.cloud_url}/api/v1/ota/check-update",
                        params={"device_id": self.device_id},
                        headers={"Authorization": f"Bearer {self.auth_token}"}
                    ) as resp:
                        if resp.status == 200:
                            update_info = await resp.json()
                            
                            if update_info.get('update_available'):
                                logger.info(
                                    f"OTA update available: {update_info['target_version']} "
                                    f"(current: {platform.platform()})"
                                )
                                
                                # Start update process
                                await self.perform_ota_update(update_info)
                        elif resp.status != 200:
                            logger.warning(f"OTA check failed: HTTP {resp.status}")
                
            except Exception as e:
                logger.error(f"OTA update checker error: {e}")
            
            await asyncio.sleep(300)  # Check every 5 minutes
    
    async def perform_ota_update(self, update_info: Dict[str, Any]):
        """Perform OTA update"""
        deployment_id = update_info['deployment_id']
        target_version = update_info['target_version']
        update_package_url = update_info.get('update_package_url')
        checksum = update_info.get('checksum')
        
        logger.info(f"Starting OTA update to version {target_version}")
        
        try:
            # Report downloading status
            await self.report_ota_status(deployment_id, "downloading")
            
            # Download update package
            if not update_package_url:
                raise Exception("No update package URL provided")
            
            update_file = await self.download_update_package(
                update_package_url, 
                checksum
            )
            
            # Report installing status
            await self.report_ota_status(deployment_id, "installing")
            
            # Install update
            await self.install_update(update_file)
            
            # Report verifying status
            await self.report_ota_status(deployment_id, "verifying")
            
            # Verify installation
            verification_passed = await self.verify_update(target_version)
            
            if verification_passed:
                # Report completed
                await self.report_ota_status(deployment_id, "completed")
                logger.info(f"OTA update to {target_version} completed successfully")
                
                # Schedule reboot if needed
                logger.info("Update may require reboot to take full effect")
            else:
                # Verification failed - rollback
                raise Exception("Update verification failed")
                
        except Exception as e:
            logger.error(f"OTA update failed: {e}")
            
            # Report failed status
            await self.report_ota_status(
                deployment_id, 
                "failed",
                error_message=str(e)
            )
            
            # Attempt rollback
            await self.rollback_update(deployment_id)
    
    async def download_update_package(
        self, 
        url: str, 
        expected_checksum: Optional[str] = None
    ) -> Path:
        """Download and verify update package"""
        import hashlib
        
        logger.info(f"Downloading update package from {url}")
        
        download_dir = Path("/tmp/ota-updates")
        download_dir.mkdir(parents=True, exist_ok=True)
        
        update_file = download_dir / "update.tar.gz"
        
        # Download file
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise Exception(f"Download failed: HTTP {resp.status}")
                
                # Save to file
                with open(update_file, 'wb') as f:
                    async for chunk in resp.content.iter_chunked(8192):
                        f.write(chunk)
        
        logger.info(f"Downloaded {update_file.stat().st_size} bytes")
        
        # Verify checksum if provided
        if expected_checksum:
            logger.info("Verifying checksum...")
            sha256_hash = hashlib.sha256()
            
            with open(update_file, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256_hash.update(chunk)
            
            actual_checksum = sha256_hash.hexdigest()
            
            if actual_checksum != expected_checksum:
                raise Exception(
                    f"Checksum mismatch! Expected: {expected_checksum}, "
                    f"Got: {actual_checksum}"
                )
            
            logger.info("Checksum verified successfully")
        
        return update_file
    
    async def install_update(self, update_file: Path):
        """Install the update package"""
        logger.info(f"Installing update from {update_file}")
        
        # Extract update package
        extract_dir = Path("/tmp/ota-updates/extracted")
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        proc = await asyncio.create_subprocess_exec(
            'tar', '-xzf', str(update_file), '-C', str(extract_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise Exception(f"Failed to extract update: {stderr.decode()}")
        
        # Run installation script if present
        install_script = extract_dir / "install.sh"
        if install_script.exists():
            logger.info("Running installation script...")
            
            proc = await asyncio.create_subprocess_exec(
                'bash', str(install_script),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                raise Exception(f"Installation script failed: {stderr.decode()}")
            
            logger.info(f"Installation output: {stdout.decode()}")
        else:
            # Default installation: copy files to system
            logger.info("No install script found, using default installation")
            
            # Copy edge-agent binary if present
            agent_binary = extract_dir / "edge_agent.py"
            if agent_binary.exists():
                import shutil
                shutil.copy(agent_binary, __file__)
                logger.info("Updated edge agent binary")
    
    async def verify_update(self, target_version: str) -> bool:
        """Verify that update was installed correctly"""
        logger.info(f"Verifying update installation for version {target_version}")
        
        # Basic verification - check if services are still running
        try:
            services = await self.check_services()
            
            # Check if critical services are running
            critical_services_running = True
            for service in services:
                if service['status'] != 'running':
                    logger.warning(f"Service {service['name']} not running after update")
                    critical_services_running = False
            
            if not critical_services_running:
                return False
            
            # Check system health
            metrics = await self.collect_metrics()
            if not metrics:
                logger.warning("Failed to collect metrics after update")
                return False
            
            logger.info("Update verification passed")
            return True
            
        except Exception as e:
            logger.error(f"Update verification failed: {e}")
            return False
    
    async def rollback_update(self, deployment_id: str):
        """Rollback to previous version"""
        logger.warning("Attempting rollback to previous version")
        
        try:
            # Get current version (before update attempt)
            previous_version = platform.platform()
            
            # Notify cloud of rollback
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.cloud_url}/api/v1/admin/ota/deployments/{deployment_id}/devices/{self.device_id}/rollback",
                    json={"previous_version": previous_version},
                    headers={"Authorization": f"Bearer {self.auth_token}"}
                ) as resp:
                    if resp.status == 200:
                        logger.info("Rollback reported to cloud")
            
            # Restore from backup if available
            backup_agent = Path("/etc/edge-agent/edge_agent.py.backup")
            if backup_agent.exists():
                import shutil
                shutil.copy(backup_agent, __file__)
                logger.info("Restored agent from backup")
                
                # Restart agent
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                logger.warning("No backup available for rollback")
                
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
    
    async def report_ota_status(
        self, 
        deployment_id: str, 
        status: str,
        error_message: Optional[str] = None
    ):
        """Report OTA update status to cloud"""
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    f"{self.cloud_url}/api/v1/ota/deployments/{deployment_id}/status",
                    params={"device_id": self.device_id},
                    json={
                        "status": status,
                        "error_message": error_message
                    },
                    headers={"Authorization": f"Bearer {self.auth_token}"}
                )
                
            logger.info(f"Reported OTA status: {status}")
            
        except Exception as e:
            logger.error(f"Failed to report OTA status: {e}")
    
    def stop(self):
        """Stop the agent"""
        logger.info("Stopping Edge Agent")
        self.running = False


async def register_device(cloud_url: str, registration_token: str) -> Dict[str, Any]:
    """Register this device with the cloud"""
    logger.info("Registering device with Ops-Center...")
    
    # Get hardware ID (MAC address or similar)
    import uuid
    hardware_id = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0, 48, 8)])
    
    # Get system info
    firmware_version = platform.platform()
    
    metadata = {
        "hostname": platform.node(),
        "architecture": platform.machine(),
        "os": platform.system(),
        "os_release": platform.release()
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{cloud_url}/api/v1/edge/devices/register",
            json={
                "hardware_id": hardware_id,
                "registration_token": registration_token,
                "firmware_version": firmware_version,
                "metadata": metadata
            }
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                logger.info(f"Device registered successfully: {data['device_name']}")
                return data
            else:
                error_text = await resp.text()
                raise Exception(f"Registration failed: HTTP {resp.status} - {error_text}")


def save_credentials(device_id: str, auth_token: str, cloud_url: str):
    """Save device credentials to file"""
    creds_dir = Path("/etc/edge-agent")
    creds_dir.mkdir(parents=True, exist_ok=True)
    
    creds_file = creds_dir / "credentials.json"
    
    with open(creds_file, 'w') as f:
        json.dump({
            "device_id": device_id,
            "auth_token": auth_token,
            "cloud_url": cloud_url
        }, f)
    
    # Set restrictive permissions
    os.chmod(creds_file, 0o600)
    
    logger.info(f"Credentials saved to {creds_file}")


def load_credentials() -> Optional[Dict[str, str]]:
    """Load device credentials from file"""
    creds_file = Path("/etc/edge-agent/credentials.json")
    
    if not creds_file.exists():
        return None
    
    with open(creds_file, 'r') as f:
        return json.load(f)


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Ops-Center Edge Device Agent')
    parser.add_argument('--register', action='store_true', help='Register this device')
    parser.add_argument('--token', type=str, help='Registration token')
    parser.add_argument('--cloud-url', type=str, default='https://your-domain.com', help='Ops-Center URL')
    
    args = parser.parse_args()
    
    if args.register:
        if not args.token:
            logger.error("Registration token required (--token)")
            sys.exit(1)
        
        # Register device
        try:
            result = await register_device(args.cloud_url, args.token)
            save_credentials(result['device_id'], result['auth_token'], args.cloud_url)
            logger.info("Registration complete! Starting agent...")
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            sys.exit(1)
    
    # Load credentials
    creds = load_credentials()
    if not creds:
        logger.error("No credentials found. Please register first with --register --token <TOKEN>")
        sys.exit(1)
    
    # Start agent
    agent = EdgeAgent(
        device_id=creds['device_id'],
        auth_token=creds['auth_token'],
        cloud_url=creds['cloud_url']
    )
    
    try:
        await agent.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
