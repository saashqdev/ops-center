"""
Alert Correlation Engine for Smart Alerts

Groups related alerts, identifies root causes, and builds dependency graphs
to reduce alert noise and improve incident response.

Epic 13: Smart Alerts - Alert Correlation Engine
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Set, Tuple, Any
from uuid import UUID, uuid4
import json
from collections import defaultdict

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class AlertCorrelation:
    """Represents a group of correlated alerts"""
    id: UUID
    correlation_group_id: str
    alert_ids: List[UUID]
    root_cause_alert_id: Optional[UUID]
    correlation_type: str  # 'temporal', 'device_cascade', 'metric_pattern'
    confidence: float
    detected_at: datetime
    time_window_start: datetime
    time_window_end: datetime
    impact_score: float
    metadata: Dict[str, Any]
    
    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'correlation_group_id': self.correlation_group_id,
            'alert_ids': [str(aid) for aid in self.alert_ids],
            'root_cause_alert_id': str(self.root_cause_alert_id) if self.root_cause_alert_id else None,
            'correlation_type': self.correlation_type,
            'confidence': self.confidence,
            'detected_at': self.detected_at.isoformat(),
            'time_window_start': self.time_window_start.isoformat(),
            'time_window_end': self.time_window_end.isoformat(),
            'impact_score': self.impact_score,
            'metadata': self.metadata
        }


class AlertCorrelationEngine:
    """
    Alert Correlation Engine - Groups related alerts and finds root causes.
    
    Correlation Strategies:
    1. Temporal - Alerts occurring within same time window
    2. Device Cascade - Related devices (same rack, same network)
    3. Metric Pattern - Similar metric patterns across devices
    4. Dependency Chain - Service dependencies causing cascading failures
    """
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.correlation_window = timedelta(minutes=5)  # Alerts within 5min are candidates
        self.device_topology_cache: Dict[UUID, Dict] = {}
        self.cache_ttl = timedelta(hours=1)
        self.last_cache_update = datetime.min
    
    async def correlate_alerts(
        self,
        time_window_minutes: int = 15
    ) -> List[AlertCorrelation]:
        """
        Find and group correlated alerts within time window.
        
        Args:
            time_window_minutes: Time window to analyze for correlations
            
        Returns:
            List of alert correlations found
        """
        try:
            # Get recent open alerts
            alerts = await self._fetch_recent_alerts(time_window_minutes)
            
            if len(alerts) < 2:
                return []
            
            correlations = []
            
            # Strategy 1: Temporal correlation
            temporal_groups = await self._correlate_temporal(alerts)
            correlations.extend(temporal_groups)
            
            # Strategy 2: Device cascade correlation
            cascade_groups = await self._correlate_device_cascade(alerts)
            correlations.extend(cascade_groups)
            
            # Strategy 3: Metric pattern correlation
            pattern_groups = await self._correlate_metric_patterns(alerts)
            correlations.extend(pattern_groups)
            
            # Save correlations to database
            for correlation in correlations:
                await self._save_correlation(correlation)
            
            logger.info(f"Found {len(correlations)} alert correlations")
            
            return correlations
            
        except Exception as e:
            logger.error(f"Error correlating alerts: {e}", exc_info=True)
            return []
    
    async def find_root_cause(
        self,
        alert_group: List[Dict[str, Any]]
    ) -> Optional[UUID]:
        """
        Identify root cause alert in a correlated group.
        
        Root cause criteria:
        1. Earliest alert in time sequence
        2. Highest severity
        3. Infrastructure/network alerts over application
        4. Upstream dependencies over downstream
        
        Args:
            alert_group: List of alert dictionaries
            
        Returns:
            UUID of root cause alert or None
        """
        if not alert_group:
            return None
        
        # Sort by timestamp (earliest first)
        sorted_alerts = sorted(alert_group, key=lambda a: a['created_at'])
        
        # Score each alert for root cause likelihood
        scores = []
        for alert in sorted_alerts:
            score = 0.0
            
            # Earlier alerts more likely to be root cause (max 40 points)
            time_diff = (sorted_alerts[-1]['created_at'] - alert['created_at']).total_seconds()
            max_time_diff = (sorted_alerts[-1]['created_at'] - sorted_alerts[0]['created_at']).total_seconds()
            if max_time_diff > 0:
                score += 40 * (1 - time_diff / max_time_diff)
            else:
                score += 40
            
            # Severity (max 30 points)
            severity_scores = {'critical': 30, 'error': 20, 'warning': 10, 'info': 5}
            score += severity_scores.get(alert.get('severity', 'info'), 5)
            
            # Infrastructure alerts (max 20 points)
            category = alert.get('alert_category', '')
            if category in ['network', 'infrastructure', 'hardware']:
                score += 20
            elif category in ['database', 'storage']:
                score += 15
            elif category in ['application', 'service']:
                score += 10
            
            # Higher priority score (max 10 points)
            priority = alert.get('priority_score', 50)
            score += (priority / 100) * 10
            
            scores.append((alert['id'], score))
        
        # Return alert with highest root cause score
        root_cause = max(scores, key=lambda x: x[1])
        
        logger.info(f"Identified root cause: {root_cause[0]} (score: {root_cause[1]:.1f})")
        
        return root_cause[0]
    
    async def calculate_impact_score(
        self,
        alert_group: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate impact score for correlated alert group.
        
        Impact factors:
        - Number of affected devices
        - Severity distribution
        - Alert categories
        - Affected services
        
        Returns:
            Impact score 0-100
        """
        if not alert_group:
            return 0.0
        
        impact = 0.0
        
        # Factor 1: Number of affected devices (max 30 points)
        unique_devices = len(set(a['device_id'] for a in alert_group if a.get('device_id')))
        impact += min(30, unique_devices * 3)
        
        # Factor 2: Number of alerts (max 20 points)
        impact += min(20, len(alert_group) * 2)
        
        # Factor 3: Severity distribution (max 30 points)
        severity_weights = {'critical': 10, 'error': 7, 'warning': 4, 'info': 1}
        severity_score = sum(severity_weights.get(a.get('severity', 'info'), 1) for a in alert_group)
        impact += min(30, severity_score)
        
        # Factor 4: Category diversity (max 20 points)
        unique_categories = len(set(a.get('alert_category', 'unknown') for a in alert_group))
        impact += min(20, unique_categories * 5)
        
        return min(100.0, impact)
    
    async def _correlate_temporal(
        self,
        alerts: List[Dict[str, Any]]
    ) -> List[AlertCorrelation]:
        """
        Group alerts occurring within same time window.
        
        Creates groups of alerts that fired within 5 minutes of each other,
        likely indicating a related incident.
        """
        correlations = []
        processed_alerts = set()
        
        # Sort by timestamp
        sorted_alerts = sorted(alerts, key=lambda a: a['created_at'])
        
        for i, alert in enumerate(sorted_alerts):
            if alert['id'] in processed_alerts:
                continue
            
            # Find alerts within correlation window
            window_start = alert['created_at']
            window_end = window_start + self.correlation_window
            
            group = [alert]
            group_ids = {alert['id']}
            
            for other in sorted_alerts[i+1:]:
                if other['created_at'] > window_end:
                    break
                if other['id'] not in processed_alerts:
                    group.append(other)
                    group_ids.add(other['id'])
            
            # Only create correlation if multiple alerts in group
            if len(group) >= 2:
                processed_alerts.update(group_ids)
                
                root_cause = await self.find_root_cause(group)
                impact = await self.calculate_impact_score(group)
                
                correlation = AlertCorrelation(
                    id=uuid4(),
                    correlation_group_id=f"temporal_{window_start.isoformat()}",
                    alert_ids=list(group_ids),
                    root_cause_alert_id=root_cause,
                    correlation_type='temporal',
                    confidence=0.7,  # Temporal correlation has moderate confidence
                    detected_at=datetime.utcnow(),
                    time_window_start=window_start,
                    time_window_end=window_end,
                    impact_score=impact,
                    metadata={
                        'alert_count': len(group),
                        'time_span_seconds': (group[-1]['created_at'] - group[0]['created_at']).total_seconds(),
                        'unique_devices': len(set(a['device_id'] for a in group if a.get('device_id')))
                    }
                )
                
                correlations.append(correlation)
        
        return correlations
    
    async def _correlate_device_cascade(
        self,
        alerts: List[Dict[str, Any]]
    ) -> List[AlertCorrelation]:
        """
        Group alerts from related devices (same rack, network, service).
        
        Detects cascading failures where one device failure causes
        failures in dependent devices.
        """
        correlations = []
        
        # Update device topology cache if needed
        if datetime.utcnow() - self.last_cache_update > self.cache_ttl:
            await self._refresh_device_topology()
        
        # Group alerts by device relationships
        device_groups = defaultdict(list)
        
        for alert in alerts:
            device_id = alert.get('device_id')
            if not device_id:
                continue
            
            topology = self.device_topology_cache.get(device_id, {})
            
            # Group by rack
            rack_id = topology.get('rack_id', 'unknown')
            device_groups[f"rack_{rack_id}"].append(alert)
            
            # Group by network segment
            network_segment = topology.get('network_segment', 'unknown')
            device_groups[f"network_{network_segment}"].append(alert)
            
            # Group by service
            service = topology.get('service', 'unknown')
            device_groups[f"service_{service}"].append(alert)
        
        # Create correlations for groups with multiple alerts
        for group_key, group in device_groups.items():
            if len(group) < 2:
                continue
            
            # Calculate time span
            timestamps = [a['created_at'] for a in group]
            time_span = max(timestamps) - min(timestamps)
            
            # Only correlate if alerts occurred within reasonable window (30 minutes)
            if time_span > timedelta(minutes=30):
                continue
            
            root_cause = await self.find_root_cause(group)
            impact = await self.calculate_impact_score(group)
            
            correlation = AlertCorrelation(
                id=uuid4(),
                correlation_group_id=group_key,
                alert_ids=[a['id'] for a in group],
                root_cause_alert_id=root_cause,
                correlation_type='device_cascade',
                confidence=0.85,  # Device topology has high confidence
                detected_at=datetime.utcnow(),
                time_window_start=min(timestamps),
                time_window_end=max(timestamps),
                impact_score=impact,
                metadata={
                    'group_type': group_key.split('_')[0],
                    'group_id': '_'.join(group_key.split('_')[1:]),
                    'alert_count': len(group),
                    'unique_devices': len(set(a['device_id'] for a in group if a.get('device_id')))
                }
            )
            
            correlations.append(correlation)
        
        return correlations
    
    async def _correlate_metric_patterns(
        self,
        alerts: List[Dict[str, Any]]
    ) -> List[AlertCorrelation]:
        """
        Group alerts with similar metric patterns across devices.
        
        Detects coordinated issues like widespread CPU spike, network
        saturation, or DDoS affecting multiple servers.
        """
        correlations = []
        
        # Group alerts by metric name
        metric_groups = defaultdict(list)
        for alert in alerts:
            # Extract metric from alert message or metadata
            metric = self._extract_metric_name(alert)
            if metric:
                metric_groups[metric].append(alert)
        
        # Analyze each metric group
        for metric, group in metric_groups.items():
            if len(group) < 3:  # Need at least 3 devices for pattern
                continue
            
            # Check if alerts occurred in similar timeframe
            timestamps = [a['created_at'] for a in group]
            time_span = max(timestamps) - min(timestamps)
            
            # Pattern should show alerts within 15 minutes
            if time_span > timedelta(minutes=15):
                continue
            
            # Check severity pattern (all similar severity = likely coordinated)
            severities = [a.get('severity', 'info') for a in group]
            severity_similarity = len(set(severities)) / len(severities)
            
            # High similarity = high confidence
            confidence = 0.6 + (0.3 * (1 - severity_similarity))
            
            root_cause = await self.find_root_cause(group)
            impact = await self.calculate_impact_score(group)
            
            correlation = AlertCorrelation(
                id=uuid4(),
                correlation_group_id=f"metric_pattern_{metric}",
                alert_ids=[a['id'] for a in group],
                root_cause_alert_id=root_cause,
                correlation_type='metric_pattern',
                confidence=confidence,
                detected_at=datetime.utcnow(),
                time_window_start=min(timestamps),
                time_window_end=max(timestamps),
                impact_score=impact,
                metadata={
                    'metric_name': metric,
                    'alert_count': len(group),
                    'unique_devices': len(set(a['device_id'] for a in group if a.get('device_id'))),
                    'severity_pattern': list(set(severities)),
                    'time_span_seconds': time_span.total_seconds()
                }
            )
            
            correlations.append(correlation)
        
        return correlations
    
    def _extract_metric_name(self, alert: Dict[str, Any]) -> Optional[str]:
        """Extract metric name from alert"""
        # Try metadata first
        metadata = alert.get('metadata', {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        if 'metric_name' in metadata:
            return metadata['metric_name']
        
        # Try to extract from alert message
        message = alert.get('alert_message', '').lower()
        
        # Common metric patterns
        metric_keywords = {
            'cpu': 'cpu_usage',
            'memory': 'memory_usage',
            'disk': 'disk_usage',
            'network': 'network_latency',
            'error': 'error_rate',
            'latency': 'latency',
            'bandwidth': 'bandwidth'
        }
        
        for keyword, metric in metric_keywords.items():
            if keyword in message:
                return metric
        
        return None
    
    async def _fetch_recent_alerts(
        self,
        time_window_minutes: int
    ) -> List[Dict[str, Any]]:
        """Fetch recent open alerts for correlation analysis"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    id, device_id, alert_type, severity, alert_message,
                    alert_category, priority_score, created_at, metadata,
                    is_smart_alert, anomaly_id
                FROM alerts
                WHERE created_at > NOW() - INTERVAL '%s minutes'
                  AND status = 'open'
                  AND suppressed = false
                ORDER BY created_at DESC
            """ % time_window_minutes)
            
            return [dict(row) for row in rows]
    
    async def _refresh_device_topology(self):
        """Refresh device topology cache from database"""
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT 
                        id, rack_id, network_segment, service_name,
                        device_metadata
                    FROM devices
                    WHERE status = 'active'
                """)
                
                self.device_topology_cache = {}
                for row in rows:
                    metadata = row['device_metadata'] or {}
                    if isinstance(metadata, str):
                        try:
                            metadata = json.loads(metadata)
                        except:
                            metadata = {}
                    
                    self.device_topology_cache[row['id']] = {
                        'rack_id': row.get('rack_id', 'unknown'),
                        'network_segment': row.get('network_segment', 'unknown'),
                        'service': row.get('service_name', 'unknown'),
                        'metadata': metadata
                    }
                
                self.last_cache_update = datetime.utcnow()
                logger.info(f"Refreshed device topology cache: {len(self.device_topology_cache)} devices")
                
        except Exception as e:
            logger.error(f"Error refreshing device topology: {e}")
    
    async def _save_correlation(self, correlation: AlertCorrelation) -> None:
        """Save correlation to database"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO alert_correlations (
                        id, correlation_group_id, alert_ids, root_cause_alert_id,
                        correlation_type, confidence_score, detected_at,
                        time_window_start, time_window_end, impact_score, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                    correlation.id,
                    correlation.correlation_group_id,
                    correlation.alert_ids,
                    correlation.root_cause_alert_id,
                    correlation.correlation_type,
                    correlation.confidence,
                    correlation.detected_at,
                    correlation.time_window_start,
                    correlation.time_window_end,
                    correlation.impact_score,
                    json.dumps(correlation.metadata)
                )
                
                # Link alerts to correlation
                for alert_id in correlation.alert_ids:
                    await conn.execute("""
                        UPDATE alerts
                        SET correlation_group_id = $1
                        WHERE id = $2
                    """, correlation.correlation_group_id, alert_id)
                
        except Exception as e:
            logger.error(f"Error saving correlation: {e}")
    
    async def get_correlations(
        self,
        hours: int = 24,
        correlation_type: Optional[str] = None,
        min_impact: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve alert correlations with filters.
        
        Args:
            hours: Lookback period
            correlation_type: Filter by type (temporal, device_cascade, metric_pattern)
            min_impact: Minimum impact score
            
        Returns:
            List of correlation records
        """
        conditions = ["detected_at > NOW() - INTERVAL '%s hours'" % hours]
        params = []
        
        if correlation_type:
            conditions.append(f"correlation_type = ${len(params) + 1}")
            params.append(correlation_type)
        
        if min_impact:
            conditions.append(f"impact_score >= ${len(params) + 1}")
            params.append(min_impact)
        
        where_clause = " AND ".join(conditions)
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT 
                    id, correlation_group_id, alert_ids, root_cause_alert_id,
                    correlation_type, confidence_score, detected_at,
                    time_window_start, time_window_end, impact_score, metadata
                FROM alert_correlations
                WHERE {where_clause}
                ORDER BY detected_at DESC, impact_score DESC
                LIMIT 100
            """, *params)
            
            return [dict(row) for row in rows]
    
    async def get_correlation_details(
        self,
        correlation_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get detailed information about a correlation"""
        async with self.db_pool.acquire() as conn:
            # Get correlation record
            correlation = await conn.fetchrow("""
                SELECT * FROM alert_correlations WHERE id = $1
            """, correlation_id)
            
            if not correlation:
                return None
            
            # Get all alerts in correlation
            alert_ids = correlation['alert_ids']
            alerts = await conn.fetch("""
                SELECT 
                    id, device_id, alert_type, severity, alert_message,
                    alert_category, priority_score, created_at, status
                FROM alerts
                WHERE id = ANY($1)
                ORDER BY created_at
            """, alert_ids)
            
            # Get root cause alert details
            root_cause = None
            if correlation['root_cause_alert_id']:
                root_cause = await conn.fetchrow("""
                    SELECT 
                        id, device_id, alert_type, severity, alert_message,
                        alert_category, created_at
                    FROM alerts
                    WHERE id = $1
                """, correlation['root_cause_alert_id'])
            
            return {
                'correlation': dict(correlation),
                'alerts': [dict(a) for a in alerts],
                'root_cause': dict(root_cause) if root_cause else None,
                'alert_count': len(alerts),
                'affected_devices': len(set(a['device_id'] for a in alerts if a['device_id']))
            }


# Singleton instance
_correlation_engine: Optional[AlertCorrelationEngine] = None


async def get_correlation_engine(db_pool) -> AlertCorrelationEngine:
    """Get singleton correlation engine instance"""
    global _correlation_engine
    
    if _correlation_engine is None:
        _correlation_engine = AlertCorrelationEngine(db_pool)
    
    return _correlation_engine
