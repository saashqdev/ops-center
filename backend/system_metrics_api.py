"""
System Metrics API

Comprehensive system monitoring endpoints for real-time health tracking.
Provides CPU, memory, disk, network metrics with historical data support.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import psutil
import docker
import asyncio
import logging
import redis
import json
from enum import Enum

from health_score import HealthScoreCalculator
from alert_manager import AlertManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/system", tags=["system-metrics"])

# Initialize health score calculator and alert manager
health_calculator = HealthScoreCalculator()
alert_manager = AlertManager()


class TimeFrame(str, Enum):
    """Valid timeframes for metrics queries."""
    ONE_HOUR = "1h"
    SIX_HOURS = "6h"
    TWENTY_FOUR_HOURS = "24h"
    SEVEN_DAYS = "7d"
    THIRTY_DAYS = "30d"


class MetricsCache:
    """Redis-backed metrics cache for historical data."""

    def __init__(self):
        try:
            self.redis = redis.Redis(
                host='unicorn-redis',
                port=6379,
                db=1,
                decode_responses=True,
                socket_timeout=5
            )
            self.redis.ping()
            logger.info("Connected to Redis for metrics storage")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory fallback.")
            self.redis = None

    def get_historical_metrics(
        self,
        timeframe: TimeFrame
    ) -> List[Dict]:
        """Retrieve historical metrics from Redis."""
        if not self.redis:
            return []

        try:
            now = datetime.utcnow()

            # Calculate time range
            if timeframe == TimeFrame.ONE_HOUR:
                start_time = now - timedelta(hours=1)
            elif timeframe == TimeFrame.SIX_HOURS:
                start_time = now - timedelta(hours=6)
            elif timeframe == TimeFrame.TWENTY_FOUR_HOURS:
                start_time = now - timedelta(hours=24)
            elif timeframe == TimeFrame.SEVEN_DAYS:
                start_time = now - timedelta(days=7)
            else:  # 30 days
                start_time = now - timedelta(days=30)

            start_ts = int(start_time.timestamp())
            end_ts = int(now.timestamp())

            # Get all metric keys in range
            keys = []
            for ts in range(start_ts, end_ts, 5):  # 5 second intervals
                key = f"metrics:{ts}"
                if self.redis.exists(key):
                    keys.append(key)

            # Retrieve metrics
            metrics = []
            for key in keys[-200:]:  # Limit to last 200 data points
                data = self.redis.get(key)
                if data:
                    metrics.append(json.loads(data))

            return metrics
        except Exception as e:
            logger.error(f"Error retrieving historical metrics: {e}")
            return []


# Initialize cache
metrics_cache = MetricsCache()


def get_cpu_metrics() -> Dict:
    """Get current CPU metrics."""
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1, percpu=False)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()

        return {
            "current": round(cpu_percent, 2),
            "cores": cpu_count,
            "frequency": round(cpu_freq.current / 1000, 2) if cpu_freq else 0,
            "per_cpu": [round(p, 2) for p in psutil.cpu_percent(interval=0.1, percpu=True)]
        }
    except Exception as e:
        logger.error(f"Error getting CPU metrics: {e}")
        return {
            "current": 0,
            "cores": 0,
            "frequency": 0,
            "per_cpu": []
        }


def get_memory_metrics() -> Dict:
    """Get current memory metrics."""
    try:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return {
            "current": round(mem.percent, 2),
            "total": round(mem.total / (1024**3), 2),  # GB
            "used": round(mem.used / (1024**3), 2),
            "available": round(mem.available / (1024**3), 2),
            "swap_total": round(swap.total / (1024**3), 2),
            "swap_used": round(swap.used / (1024**3), 2),
            "swap_percent": round(swap.percent, 2)
        }
    except Exception as e:
        logger.error(f"Error getting memory metrics: {e}")
        return {
            "current": 0,
            "total": 0,
            "used": 0,
            "available": 0,
            "swap_total": 0,
            "swap_used": 0,
            "swap_percent": 0
        }


def get_disk_metrics() -> Dict:
    """Get current disk metrics."""
    try:
        volumes = []

        # Get all mounted partitions
        partitions = psutil.disk_partitions()
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                volumes.append({
                    "path": partition.mountpoint,
                    "device": partition.device,
                    "fstype": partition.fstype,
                    "total": round(usage.total / (1024**3), 2),  # GB
                    "used": round(usage.used / (1024**3), 2),
                    "free": round(usage.free / (1024**3), 2),
                    "percent": round(usage.percent, 2)
                })
            except (PermissionError, OSError):
                # Skip inaccessible mounts
                continue

        # Get I/O stats
        io_counters = psutil.disk_io_counters()
        io_stats = {
            "read_bytes": io_counters.read_bytes,
            "write_bytes": io_counters.write_bytes,
            "read_count": io_counters.read_count,
            "write_count": io_counters.write_count,
            "read_mb": round(io_counters.read_bytes / (1024**2), 2),
            "write_mb": round(io_counters.write_bytes / (1024**2), 2)
        }

        return {
            "volumes": volumes,
            "io": io_stats
        }
    except Exception as e:
        logger.error(f"Error getting disk metrics: {e}")
        return {
            "volumes": [],
            "io": {
                "read_bytes": 0,
                "write_bytes": 0,
                "read_count": 0,
                "write_count": 0,
                "read_mb": 0,
                "write_mb": 0
            }
        }


def get_network_metrics() -> Dict:
    """Get current network metrics."""
    try:
        net_io = psutil.net_io_counters(pernic=True)
        interfaces = []

        for interface, counters in net_io.items():
            # Skip loopback and docker interfaces
            if interface.startswith(('lo', 'docker', 'br-', 'veth')):
                continue

            interfaces.append({
                "name": interface,
                "sent": counters.bytes_sent,
                "recv": counters.bytes_recv,
                "sent_mb": round(counters.bytes_sent / (1024**2), 2),
                "recv_mb": round(counters.bytes_recv / (1024**2), 2),
                "packets_sent": counters.packets_sent,
                "packets_recv": counters.packets_recv,
                "errors_in": counters.errin,
                "errors_out": counters.errout,
                "drops_in": counters.dropin,
                "drops_out": counters.dropout
            })

        return {
            "interfaces": interfaces
        }
    except Exception as e:
        logger.error(f"Error getting network metrics: {e}")
        return {
            "interfaces": []
        }


def get_detailed_network_metrics() -> Dict:
    """Get comprehensive network metrics including interfaces, connections, DNS, and gateway."""
    import subprocess
    import time

    result = {
        "interfaces": [],
        "connections": {
            "total": 0,
            "by_state": {},
            "top_connections": []
        },
        "dns": {
            "nameservers": [],
            "search_domains": []
        },
        "gateway": {
            "default": None,
            "interface": None
        },
        "aggregate_bandwidth": {
            "total_in_per_sec": 0,
            "total_out_per_sec": 0
        }
    }

    # --- Interfaces with bandwidth ---
    try:
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        io_before = psutil.net_io_counters(pernic=True)
        time.sleep(1)
        io_after = psutil.net_io_counters(pernic=True)

        total_in_per_sec = 0
        total_out_per_sec = 0

        for iface_name, iface_addrs in addrs.items():
            # Classify interface type
            if iface_name == 'lo':
                iface_type = 'loopback'
            elif iface_name.startswith(('docker', 'br-', 'veth', 'cni', 'flannel')):
                iface_type = 'virtual'
            elif iface_name.startswith(('wl', 'wlan')):
                iface_type = 'wifi'
            else:
                iface_type = 'ethernet'

            # Get link stats
            iface_stats = stats.get(iface_name)
            is_up = iface_stats.isup if iface_stats else False
            speed_mbps = iface_stats.speed if iface_stats else 0
            mtu = iface_stats.mtu if iface_stats else 0
            duplex_val = iface_stats.duplex if iface_stats else 0
            duplex_str = {0: 'unknown', 1: 'half', 2: 'full'}.get(duplex_val, 'unknown')

            # Parse addresses
            mac = None
            ipv4_list = []
            ipv6_list = []
            for addr in iface_addrs:
                if addr.family.name == 'AF_LINK' or addr.family.name == 'AF_PACKET':
                    mac = addr.address
                elif addr.family.name == 'AF_INET':
                    ipv4_list.append({"address": addr.address, "netmask": addr.netmask or ""})
                elif addr.family.name == 'AF_INET6':
                    ipv6_list.append({"address": addr.address, "prefix_length": addr.netmask or ""})

            # I/O counters
            before = io_before.get(iface_name)
            after = io_after.get(iface_name)
            io_data = {}
            bandwidth = {"bytes_sent_per_sec": 0, "bytes_recv_per_sec": 0}
            if after:
                io_data = {
                    "bytes_sent": after.bytes_sent,
                    "bytes_recv": after.bytes_recv,
                    "packets_sent": after.packets_sent,
                    "packets_recv": after.packets_recv,
                    "errors_in": after.errin,
                    "errors_out": after.errout,
                    "drops_in": after.dropin,
                    "drops_out": after.dropout
                }
                if before:
                    bw_in = after.bytes_recv - before.bytes_recv
                    bw_out = after.bytes_sent - before.bytes_sent
                    bandwidth = {
                        "bytes_sent_per_sec": max(0, bw_out),
                        "bytes_recv_per_sec": max(0, bw_in)
                    }
                    if iface_type not in ('loopback', 'virtual'):
                        total_in_per_sec += max(0, bw_in)
                        total_out_per_sec += max(0, bw_out)

            result["interfaces"].append({
                "name": iface_name,
                "type": iface_type,
                "state": "up" if is_up else "down",
                "mac": mac,
                "mtu": mtu,
                "speed_mbps": speed_mbps,
                "duplex": duplex_str,
                "ipv4": ipv4_list,
                "ipv6": ipv6_list,
                "stats": io_data,
                "bandwidth": bandwidth
            })

        result["aggregate_bandwidth"] = {
            "total_in_per_sec": total_in_per_sec,
            "total_out_per_sec": total_out_per_sec
        }

    except Exception as e:
        logger.error(f"Error getting detailed interface metrics: {e}")

    # --- Active Connections ---
    try:
        connections = psutil.net_connections(kind='inet')
        state_counts = {}
        top_conns = []
        pid_cache = {}

        for conn in connections:
            state = conn.status
            state_counts[state] = state_counts.get(state, 0) + 1

            if len(top_conns) < 50 and state in ('ESTABLISHED', 'LISTEN'):
                proc_name = ""
                if conn.pid:
                    if conn.pid not in pid_cache:
                        try:
                            pid_cache[conn.pid] = psutil.Process(conn.pid).name()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pid_cache[conn.pid] = "unknown"
                    proc_name = pid_cache[conn.pid]

                local = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else ""
                remote = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else ""

                top_conns.append({
                    "pid": conn.pid,
                    "process": proc_name,
                    "local_address": local,
                    "remote_address": remote,
                    "status": state,
                    "type": "tcp" if conn.type == 1 else "udp"
                })

        result["connections"] = {
            "total": len(connections),
            "by_state": state_counts,
            "top_connections": top_conns
        }
    except (psutil.AccessDenied, Exception) as e:
        logger.warning(f"Cannot retrieve connections (may need root): {e}")

    # --- DNS Configuration ---
    try:
        with open('/etc/resolv.conf', 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('nameserver'):
                    result["dns"]["nameservers"].append(line.split()[1])
                elif line.startswith('search') or line.startswith('domain'):
                    result["dns"]["search_domains"].extend(line.split()[1:])
    except Exception as e:
        logger.debug(f"Could not read /etc/resolv.conf: {e}")

    # --- Default Gateway ---
    try:
        gw_result = subprocess.run(
            ['ip', '-j', 'route', 'show', 'default'],
            capture_output=True, text=True, timeout=5
        )
        if gw_result.returncode == 0 and gw_result.stdout.strip():
            routes = json.loads(gw_result.stdout)
            if routes:
                result["gateway"] = {
                    "default": routes[0].get("gateway"),
                    "interface": routes[0].get("dev")
                }
    except Exception as e:
        logger.debug(f"Could not get default gateway: {e}")

    return result


@router.get("/network/detailed")
async def get_network_detailed() -> Dict:
    """
    Get comprehensive network monitoring data.

    Returns detailed information about all network interfaces,
    live bandwidth per interface, active connections, DNS config,
    and default gateway.
    """
    try:
        return get_detailed_network_metrics()
    except Exception as e:
        logger.error(f"Error getting detailed network metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve network details: {str(e)}")


@router.get("/network/bandwidth/history")
async def get_network_bandwidth_history(
    interface: Optional[str] = Query(None, description="Interface name (e.g. eth0). Omit for aggregate."),
    points: int = Query(30, ge=5, le=200, description="Number of data points")
) -> Dict:
    """
    Get historical bandwidth data from Redis cache.

    Returns time-series bandwidth data for charting.
    """
    try:
        if not metrics_cache.redis:
            return {"history": [], "interface": interface or "all"}

        key = f"network_bw_history:{interface or 'aggregate'}"
        raw = metrics_cache.redis.lrange(key, -points, -1)
        history = [json.loads(item) for item in raw] if raw else []

        return {
            "interface": interface or "all",
            "history": history
        }
    except Exception as e:
        logger.error(f"Error getting bandwidth history: {e}")
        return {"history": [], "interface": interface or "all"}


def record_network_bandwidth_snapshot():
    """Record a bandwidth snapshot for historical tracking. Call periodically."""
    import time
    try:
        if not metrics_cache.redis:
            return

        io_before = psutil.net_io_counters(pernic=True)
        time.sleep(1)
        io_after = psutil.net_io_counters(pernic=True)

        timestamp = datetime.utcnow().isoformat()
        aggregate_in = 0
        aggregate_out = 0

        for iface, after in io_after.items():
            if iface.startswith(('lo', 'docker', 'br-', 'veth')):
                continue
            before = io_before.get(iface)
            if not before:
                continue

            bw_in = max(0, after.bytes_recv - before.bytes_recv)
            bw_out = max(0, after.bytes_sent - before.bytes_sent)
            aggregate_in += bw_in
            aggregate_out += bw_out

            # Per-interface history
            key = f"network_bw_history:{iface}"
            entry = json.dumps({"time": timestamp, "in": bw_in, "out": bw_out})
            metrics_cache.redis.rpush(key, entry)
            metrics_cache.redis.ltrim(key, -200, -1)  # Keep last 200 points
            metrics_cache.redis.expire(key, 86400)  # TTL 24h

        # Aggregate history
        key = "network_bw_history:aggregate"
        entry = json.dumps({"time": timestamp, "in": aggregate_in, "out": aggregate_out})
        metrics_cache.redis.rpush(key, entry)
        metrics_cache.redis.ltrim(key, -200, -1)
        metrics_cache.redis.expire(key, 86400)

    except Exception as e:
        logger.debug(f"Error recording bandwidth snapshot: {e}")


def get_gpu_metrics() -> Dict:
    """Get GPU metrics if available."""
    try:
        import subprocess
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=index,name,temperature.gpu,utilization.gpu,memory.used,memory.total',
             '--format=csv,noheader,nounits'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return {"available": False, "gpus": []}

        gpus = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = [p.strip() for p in line.split(',')]
                if len(parts) == 6:
                    gpus.append({
                        "index": int(parts[0]),
                        "name": parts[1],
                        "temperature": int(parts[2]),
                        "utilization": int(parts[3]),
                        "memory_used": int(parts[4]),
                        "memory_total": int(parts[5]),
                        "memory_percent": round((int(parts[4]) / int(parts[5])) * 100, 2)
                    })

        return {
            "available": True,
            "count": len(gpus),
            "gpus": gpus
        }
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception) as e:
        logger.debug(f"GPU metrics unavailable: {e}")
        return {"available": False, "gpus": []}


@router.get("/metrics")
async def get_system_metrics(
    timeframe: TimeFrame = Query(TimeFrame.TWENTY_FOUR_HOURS, description="Timeframe for historical data")
) -> Dict:
    """
    Get comprehensive system metrics with historical data.

    Returns real-time CPU, memory, disk, network, and GPU metrics
    along with historical trend data for the specified timeframe.
    """
    try:
        # Get current metrics
        cpu = get_cpu_metrics()
        memory = get_memory_metrics()
        disk = get_disk_metrics()
        network = get_network_metrics()
        gpu = get_gpu_metrics()

        # Get historical data
        historical = metrics_cache.get_historical_metrics(timeframe)

        # Process historical data for trends
        cpu_history = [m.get("cpu", 0) for m in historical]
        memory_history = [m.get("memory", 0) for m in historical]
        disk_history = [m.get("disk", 0) for m in historical]
        network_history = [m.get("network", {}) for m in historical]

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "timeframe": timeframe,
            "cpu": {
                **cpu,
                "history": cpu_history[-50:]  # Last 50 data points
            },
            "memory": {
                **memory,
                "history": memory_history[-50:]
            },
            "disk": {
                **disk,
                "history": disk_history[-50:]
            },
            "network": {
                **network,
                "history": network_history[-50:]
            },
            "gpu": gpu
        }
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve metrics: {str(e)}")


@router.get("/services/status")
async def get_services_status() -> Dict:
    """
    Get status of all Docker services.

    Returns detailed information about each Docker container including
    resource usage, health status, and uptime.
    """
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True)

        services = []
        running_count = 0
        stopped_count = 0

        for container in containers:
            try:
                # Get container stats (non-blocking)
                stats = container.stats(stream=False)

                # Calculate CPU percentage
                cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                           stats['precpu_stats']['cpu_usage']['total_usage']
                system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                              stats['precpu_stats']['system_cpu_usage']
                cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0.0

                # Calculate memory usage
                memory_usage = stats['memory_stats'].get('usage', 0)
                memory_mb = round(memory_usage / (1024**2), 2)

                # Get uptime
                started_at = container.attrs['State']['StartedAt']
                if started_at != '0001-01-01T00:00:00Z':
                    start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    uptime_seconds = (datetime.now(start_time.tzinfo) - start_time).total_seconds()
                    uptime = format_uptime(uptime_seconds)
                else:
                    uptime = "N/A"

                # Get health status
                health_status = container.attrs['State'].get('Health', {}).get('Status')

                status = container.status
                if status == 'running':
                    running_count += 1
                else:
                    stopped_count += 1

                services.append({
                    "id": container.id[:12],
                    "name": container.name,
                    "status": status,
                    "uptime": uptime,
                    "health": health_status,
                    "cpu_percent": round(cpu_percent, 2),
                    "memory_mb": memory_mb,
                    "image": container.image.tags[0] if container.image.tags else "unknown",
                    "ports": [f"{k}/{v[0]['HostPort']}" for k, v in (container.ports or {}).items() if v]
                })
            except Exception as e:
                logger.warning(f"Error getting stats for container {container.name}: {e}")
                services.append({
                    "id": container.id[:12],
                    "name": container.name,
                    "status": container.status,
                    "uptime": "N/A",
                    "health": None,
                    "cpu_percent": 0,
                    "memory_mb": 0,
                    "image": "unknown",
                    "ports": []
                })

        return {
            "total": len(containers),
            "running": running_count,
            "stopped": stopped_count,
            "services": sorted(services, key=lambda x: x['name'])
        }
    except Exception as e:
        logger.error(f"Error getting services status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve service status: {str(e)}")


def format_uptime(seconds: float) -> str:
    """Format uptime in human-readable format."""
    if seconds < 60:
        return f"{int(seconds)} seconds"
    elif seconds < 3600:
        return f"{int(seconds // 60)} minutes"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"
    else:
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        return f"{days}d {hours}h"


@router.get("/processes")
async def get_top_processes(limit: int = Query(10, ge=1, le=50)) -> Dict:
    """
    Get top processes by CPU and memory usage.

    Args:
        limit: Number of processes to return (1-50)

    Returns:
        Top processes sorted by resource usage
    """
    try:
        processes = []

        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'username']):
            try:
                pinfo = proc.info
                processes.append({
                    "pid": pinfo['pid'],
                    "name": pinfo['name'],
                    "cpu_percent": round(pinfo['cpu_percent'] or 0, 2),
                    "memory_percent": round(pinfo['memory_percent'] or 0, 2),
                    "username": pinfo['username']
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort by CPU usage
        by_cpu = sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:limit]

        # Sort by memory usage
        by_memory = sorted(processes, key=lambda x: x['memory_percent'], reverse=True)[:limit]

        return {
            "top_by_cpu": by_cpu,
            "top_by_memory": by_memory,
            "total_processes": len(processes)
        }
    except Exception as e:
        logger.error(f"Error getting top processes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve processes: {str(e)}")


@router.get("/temperature")
async def get_system_temperature() -> Dict:
    """
    Get system temperature sensors.

    Returns temperature readings from all available sensors.
    """
    try:
        temps = {}

        # Try to get CPU temperatures
        try:
            sensors = psutil.sensors_temperatures()
            for name, entries in sensors.items():
                temps[name] = [
                    {
                        "label": entry.label or f"sensor_{i}",
                        "current": round(entry.current, 1),
                        "high": round(entry.high, 1) if entry.high else None,
                        "critical": round(entry.critical, 1) if entry.critical else None
                    }
                    for i, entry in enumerate(entries)
                ]
        except AttributeError:
            # sensors_temperatures not available on this system
            pass

        # Add GPU temperatures
        gpu_metrics = get_gpu_metrics()
        if gpu_metrics.get("available"):
            temps["gpu"] = [
                {
                    "label": f"{gpu['name']} (GPU {gpu['index']})",
                    "current": float(gpu['temperature']),
                    "high": 80.0,
                    "critical": 90.0
                }
                for gpu in gpu_metrics.get("gpus", [])
            ]

        return {
            "available": len(temps) > 0,
            "sensors": temps
        }
    except Exception as e:
        logger.error(f"Error getting temperature: {e}")
        return {
            "available": False,
            "sensors": {}
        }


@router.get("/health-score")
async def get_health_score() -> Dict:
    """
    Calculate overall system health score (0-100).

    The health score is calculated using weighted components:
    - CPU health: 30%
    - Memory health: 25%
    - Disk health: 20%
    - Services health: 15%
    - Network health: 10%

    Returns:
        Overall health score with component breakdown and recommendations
    """
    try:
        health_data = health_calculator.calculate_overall_score()

        # Add recommendations
        recommendations = health_calculator.get_recommendations(health_data)
        health_data["recommendations"] = recommendations

        return health_data
    except Exception as e:
        logger.error(f"Error calculating health score: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate health score: {str(e)}")


@router.get("/alerts")
async def get_system_alerts() -> List[Dict]:
    """
    Get active system alerts and warnings.

    Alert types:
    - high_cpu: CPU usage above threshold
    - low_memory: Low available memory
    - low_disk: Low disk space
    - service_down: Docker container stopped
    - service_unhealthy: Container health check failed
    - high_temperature: Temperature above safe levels
    - network_errors: Network error rate elevated
    - swap_usage_high: High swap usage
    - disk_io_high: High disk I/O activity
    - backup_failed: Backup operation failed
    - security_warning: Security-related alert

    Returns:
        List of active alerts with severity, message, and details
    """
    try:
        alerts = await alert_manager.get_active_alerts()
        return alerts
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve alerts: {str(e)}")


@router.post("/alerts/{alert_id}/dismiss")
async def dismiss_alert(alert_id: str) -> Dict:
    """
    Dismiss a system alert.

    Args:
        alert_id: Alert ID to dismiss

    Returns:
        Success status
    """
    try:
        success = await alert_manager.dismiss_alert(alert_id)

        if success:
            return {
                "success": True,
                "message": f"Alert {alert_id} dismissed",
                "alert_id": alert_id
            }
        else:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found or not dismissible")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error dismissing alert: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to dismiss alert: {str(e)}")


@router.get("/alerts/history")
async def get_alert_history(
    limit: int = Query(100, ge=1, le=500),
    severity: Optional[str] = Query(None, description="Filter by severity: info, warning, error, critical")
) -> List[Dict]:
    """
    Get alert history.

    Args:
        limit: Maximum number of alerts to return (1-500)
        severity: Filter by severity level (optional)

    Returns:
        List of historical alerts
    """
    try:
        from alert_manager import AlertSeverity

        # Validate severity if provided
        severity_filter = None
        if severity:
            try:
                severity_filter = AlertSeverity(severity.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid severity: {severity}. Must be one of: info, warning, error, critical"
                )

        history = await alert_manager.get_alert_history(limit=limit, severity=severity_filter)
        return history
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alert history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve alert history: {str(e)}")


@router.get("/alerts/summary")
async def get_alert_summary() -> Dict:
    """
    Get summary of current alerts by severity.

    Returns:
        Alert counts broken down by severity level
    """
    try:
        summary = alert_manager.get_alert_summary()
        return summary
    except Exception as e:
        logger.error(f"Error getting alert summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve alert summary: {str(e)}")
