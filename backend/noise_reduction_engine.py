"""
Noise Reduction Engine for Smart Alerts

Reduces alert noise through suppression rules, flapping detection,
duplicate prevention, and intelligent rate limiting.

Epic 13: Smart Alerts - Noise Reduction Engine
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Set, Tuple, Any
from uuid import UUID, uuid4
import json
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class SuppressionRule:
    """Alert suppression rule"""
    id: UUID
    rule_name: str
    rule_type: str  # 'maintenance', 'known_issue', 'schedule', 'regex'
    device_id: Optional[UUID]
    alert_pattern: Optional[str]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    days_of_week: Optional[List[int]]  # 0=Monday, 6=Sunday
    is_active: bool
    created_by: UUID
    metadata: Dict[str, Any]
    
    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'rule_name': self.rule_name,
            'rule_type': self.rule_type,
            'device_id': str(self.device_id) if self.device_id else None,
            'alert_pattern': self.alert_pattern,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'days_of_week': self.days_of_week,
            'is_active': self.is_active,
            'created_by': str(self.created_by),
            'metadata': self.metadata
        }


@dataclass
class FlappingDetection:
    """Flapping alert detection result"""
    device_id: UUID
    alert_pattern: str
    flap_count: int
    time_window_minutes: int
    first_occurrence: datetime
    last_occurrence: datetime
    is_flapping: bool
    suppression_recommended: bool


class NoiseReductionEngine:
    """
    Noise Reduction Engine - Reduces alert fatigue and noise.
    
    Features:
    1. Suppression Rules - Silence alerts during maintenance, known issues
    2. Flapping Detection - Detect alerts oscillating open/closed
    3. Duplicate Detection - Prevent duplicate alerts
    4. Rate Limiting - Throttle high-frequency alerts
    5. Smart Grouping - Group similar alerts to reduce volume
    """
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        
        # Flapping detection parameters
        self.flapping_threshold = 5  # Alert must flip 5+ times
        self.flapping_window = timedelta(minutes=30)  # Within 30 minutes
        
        # Duplicate detection cache
        self.recent_alerts_cache: Dict[str, datetime] = {}
        self.duplicate_window = timedelta(minutes=5)
        
        # Rate limiting
        self.rate_limit_window = timedelta(minutes=60)
        self.rate_limit_threshold = 10  # Max 10 similar alerts per hour
        self.rate_limit_counters: Dict[str, List[datetime]] = defaultdict(list)
        
        # Suppression rules cache
        self.suppression_rules_cache: List[SuppressionRule] = []
        self.cache_ttl = timedelta(minutes=5)
        self.last_cache_update = datetime.min
    
    async def should_suppress_alert(
        self,
        device_id: UUID,
        alert_type: str,
        alert_message: str,
        severity: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Determine if alert should be suppressed.
        
        Args:
            device_id: Device generating alert
            alert_type: Type of alert
            alert_message: Alert message
            severity: Alert severity
            
        Returns:
            (should_suppress, reason) tuple
        """
        # Check suppression rules
        suppressed, reason = await self._check_suppression_rules(
            device_id, alert_type, alert_message
        )
        if suppressed:
            return True, reason
        
        # Check for duplicates
        if self._is_duplicate(device_id, alert_type, alert_message):
            return True, "duplicate_alert"
        
        # Check rate limiting
        if self._is_rate_limited(device_id, alert_type):
            return True, "rate_limited"
        
        # Check flapping
        is_flapping = await self._is_flapping(device_id, alert_type)
        if is_flapping:
            return True, "flapping_detected"
        
        return False, None
    
    async def _check_suppression_rules(
        self,
        device_id: UUID,
        alert_type: str,
        alert_message: str
    ) -> Tuple[bool, Optional[str]]:
        """Check if alert matches any active suppression rule"""
        # Refresh cache if stale
        if datetime.utcnow() - self.last_cache_update > self.cache_ttl:
            await self._refresh_suppression_rules()
        
        now = datetime.utcnow()
        current_day = now.weekday()  # 0=Monday
        
        for rule in self.suppression_rules_cache:
            if not rule.is_active:
                continue
            
            # Check device match
            if rule.device_id and rule.device_id != device_id:
                continue
            
            # Check time window
            if rule.start_time and rule.end_time:
                if not (rule.start_time <= now <= rule.end_time):
                    continue
            
            # Check day of week
            if rule.days_of_week:
                if current_day not in rule.days_of_week:
                    continue
            
            # Check alert pattern (regex or substring)
            if rule.alert_pattern:
                import re
                if rule.rule_type == 'regex':
                    if not re.search(rule.alert_pattern, alert_message, re.IGNORECASE):
                        continue
                else:
                    if rule.alert_pattern.lower() not in alert_message.lower():
                        continue
            
            # Rule matched - suppress alert
            logger.info(f"Alert suppressed by rule: {rule.rule_name}")
            return True, rule.rule_name
        
        return False, None
    
    def _is_duplicate(
        self,
        device_id: UUID,
        alert_type: str,
        alert_message: str
    ) -> bool:
        """
        Check if alert is a duplicate of recent alert.
        
        Uses cache of recent alerts within duplicate_window.
        """
        # Create cache key
        cache_key = f"{device_id}:{alert_type}:{alert_message}"
        
        # Check cache
        if cache_key in self.recent_alerts_cache:
            last_occurrence = self.recent_alerts_cache[cache_key]
            time_since_last = datetime.utcnow() - last_occurrence
            
            if time_since_last < self.duplicate_window:
                logger.info(f"Duplicate alert detected: {cache_key}")
                return True
        
        # Not a duplicate - update cache
        self.recent_alerts_cache[cache_key] = datetime.utcnow()
        
        # Clean old cache entries
        self._clean_duplicate_cache()
        
        return False
    
    def _clean_duplicate_cache(self):
        """Remove old entries from duplicate cache"""
        now = datetime.utcnow()
        keys_to_remove = []
        
        for key, timestamp in self.recent_alerts_cache.items():
            if now - timestamp > self.duplicate_window:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.recent_alerts_cache[key]
    
    def _is_rate_limited(
        self,
        device_id: UUID,
        alert_type: str
    ) -> bool:
        """
        Check if alert should be rate limited.
        
        Prevents alert storms by limiting alerts per device/type.
        """
        rate_key = f"{device_id}:{alert_type}"
        now = datetime.utcnow()
        
        # Get recent alerts for this key
        recent_alerts = self.rate_limit_counters[rate_key]
        
        # Remove old timestamps
        recent_alerts = [ts for ts in recent_alerts 
                        if now - ts < self.rate_limit_window]
        self.rate_limit_counters[rate_key] = recent_alerts
        
        # Check if rate limit exceeded
        if len(recent_alerts) >= self.rate_limit_threshold:
            logger.warning(
                f"Rate limit exceeded for {rate_key}: "
                f"{len(recent_alerts)} alerts in {self.rate_limit_window.total_seconds()/60:.0f}min"
            )
            return True
        
        # Add current timestamp
        recent_alerts.append(now)
        
        return False
    
    async def _is_flapping(
        self,
        device_id: UUID,
        alert_type: str
    ) -> bool:
        """
        Check if alert is flapping (rapidly opening/closing).
        
        Queries recent alert history to detect oscillation.
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Get recent status changes for this device/alert
                rows = await conn.fetch("""
                    SELECT status, created_at, resolved_at
                    FROM alerts
                    WHERE device_id = $1
                      AND alert_type = $2
                      AND created_at > NOW() - INTERVAL '%s minutes'
                    ORDER BY created_at DESC
                """ % int(self.flapping_window.total_seconds() / 60),
                    device_id, alert_type
                )
                
                if len(rows) < self.flapping_threshold:
                    return False
                
                # Count transitions
                transitions = 0
                prev_status = None
                
                for row in rows:
                    current_status = row['status']
                    if prev_status and prev_status != current_status:
                        transitions += 1
                    prev_status = current_status
                
                if transitions >= self.flapping_threshold:
                    logger.warning(
                        f"Flapping detected: {device_id}/{alert_type} - "
                        f"{transitions} transitions in {self.flapping_window}"
                    )
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error checking flapping: {e}")
            return False
    
    async def detect_flapping_alerts(
        self,
        hours: int = 1
    ) -> List[FlappingDetection]:
        """
        Scan for flapping alerts across all devices.
        
        Returns list of detected flapping patterns.
        """
        flapping_alerts = []
        
        try:
            async with self.db_pool.acquire() as conn:
                # Find devices with multiple status changes
                rows = await conn.fetch("""
                    WITH alert_changes AS (
                        SELECT 
                            device_id,
                            alert_type,
                            COUNT(*) as alert_count,
                            MIN(created_at) as first_occurrence,
                            MAX(created_at) as last_occurrence
                        FROM alerts
                        WHERE created_at > NOW() - INTERVAL '%s hours'
                        GROUP BY device_id, alert_type
                        HAVING COUNT(*) >= $1
                    )
                    SELECT * FROM alert_changes
                    ORDER BY alert_count DESC
                """ % hours, self.flapping_threshold)
                
                for row in rows:
                    time_window = (row['last_occurrence'] - row['first_occurrence']).total_seconds() / 60
                    
                    detection = FlappingDetection(
                        device_id=row['device_id'],
                        alert_pattern=row['alert_type'],
                        flap_count=row['alert_count'],
                        time_window_minutes=int(time_window),
                        first_occurrence=row['first_occurrence'],
                        last_occurrence=row['last_occurrence'],
                        is_flapping=row['alert_count'] >= self.flapping_threshold,
                        suppression_recommended=row['alert_count'] >= self.flapping_threshold * 2
                    )
                    
                    flapping_alerts.append(detection)
            
            logger.info(f"Found {len(flapping_alerts)} flapping alert patterns")
            
            return flapping_alerts
            
        except Exception as e:
            logger.error(f"Error detecting flapping: {e}")
            return []
    
    async def create_suppression_rule(
        self,
        rule_name: str,
        rule_type: str,
        created_by: UUID,
        device_id: Optional[UUID] = None,
        alert_pattern: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        days_of_week: Optional[List[int]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """
        Create a new alert suppression rule.
        
        Args:
            rule_name: Human-readable rule name
            rule_type: Type of rule (maintenance, known_issue, schedule, regex)
            created_by: User creating the rule
            device_id: Optional specific device
            alert_pattern: Pattern to match (substring or regex)
            start_time: Optional start time
            end_time: Optional end time
            days_of_week: Optional days (0=Mon, 6=Sun)
            metadata: Additional rule metadata
            
        Returns:
            UUID of created rule
        """
        rule_id = uuid4()
        
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO alert_suppression_rules (
                    id, rule_name, rule_type, device_id, alert_pattern,
                    start_time, end_time, days_of_week, is_active,
                    created_by, created_at, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, true, $9, NOW(), $10)
            """,
                rule_id, rule_name, rule_type, device_id, alert_pattern,
                start_time, end_time, days_of_week, created_by,
                json.dumps(metadata or {})
            )
        
        # Refresh cache
        await self._refresh_suppression_rules()
        
        logger.info(f"Created suppression rule: {rule_name} ({rule_id})")
        
        return rule_id
    
    async def update_suppression_rule(
        self,
        rule_id: UUID,
        is_active: Optional[bool] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> bool:
        """Update an existing suppression rule"""
        updates = []
        params = []
        param_idx = 1
        
        if is_active is not None:
            updates.append(f"is_active = ${param_idx}")
            params.append(is_active)
            param_idx += 1
        
        if start_time is not None:
            updates.append(f"start_time = ${param_idx}")
            params.append(start_time)
            param_idx += 1
        
        if end_time is not None:
            updates.append(f"end_time = ${param_idx}")
            params.append(end_time)
            param_idx += 1
        
        if not updates:
            return False
        
        params.append(rule_id)
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(f"""
                UPDATE alert_suppression_rules
                SET {', '.join(updates)}
                WHERE id = ${param_idx}
            """, *params)
        
        # Refresh cache
        await self._refresh_suppression_rules()
        
        logger.info(f"Updated suppression rule: {rule_id}")
        
        return True
    
    async def delete_suppression_rule(self, rule_id: UUID) -> bool:
        """Delete a suppression rule"""
        async with self.db_pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM alert_suppression_rules WHERE id = $1
            """, rule_id)
        
        # Refresh cache
        await self._refresh_suppression_rules()
        
        logger.info(f"Deleted suppression rule: {rule_id}")
        
        return True
    
    async def _refresh_suppression_rules(self):
        """Refresh suppression rules cache from database"""
        try:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT 
                        id, rule_name, rule_type, device_id, alert_pattern,
                        start_time, end_time, days_of_week, is_active,
                        created_by, metadata
                    FROM alert_suppression_rules
                    ORDER BY created_at DESC
                """)
                
                self.suppression_rules_cache = []
                for row in rows:
                    metadata = row['metadata']
                    if isinstance(metadata, str):
                        try:
                            metadata = json.loads(metadata)
                        except:
                            metadata = {}
                    
                    rule = SuppressionRule(
                        id=row['id'],
                        rule_name=row['rule_name'],
                        rule_type=row['rule_type'],
                        device_id=row['device_id'],
                        alert_pattern=row['alert_pattern'],
                        start_time=row['start_time'],
                        end_time=row['end_time'],
                        days_of_week=row['days_of_week'],
                        is_active=row['is_active'],
                        created_by=row['created_by'],
                        metadata=metadata
                    )
                    
                    self.suppression_rules_cache.append(rule)
                
                self.last_cache_update = datetime.utcnow()
                logger.info(f"Refreshed suppression rules cache: {len(self.suppression_rules_cache)} rules")
                
        except Exception as e:
            logger.error(f"Error refreshing suppression rules: {e}")
    
    async def get_suppression_rules(
        self,
        is_active: Optional[bool] = None,
        rule_type: Optional[str] = None
    ) -> List[SuppressionRule]:
        """Get suppression rules with optional filters"""
        # Refresh cache if stale
        if datetime.utcnow() - self.last_cache_update > self.cache_ttl:
            await self._refresh_suppression_rules()
        
        rules = self.suppression_rules_cache
        
        if is_active is not None:
            rules = [r for r in rules if r.is_active == is_active]
        
        if rule_type:
            rules = [r for r in rules if r.rule_type == rule_type]
        
        return rules
    
    async def get_noise_reduction_stats(
        self,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get noise reduction statistics"""
        async with self.db_pool.acquire() as conn:
            # Get suppressed alerts
            suppressed = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_suppressed,
                    COUNT(*) FILTER (WHERE suppression_reason = 'duplicate_alert') as duplicates,
                    COUNT(*) FILTER (WHERE suppression_reason = 'rate_limited') as rate_limited,
                    COUNT(*) FILTER (WHERE suppression_reason = 'flapping_detected') as flapping,
                    COUNT(*) FILTER (WHERE suppression_reason NOT IN 
                        ('duplicate_alert', 'rate_limited', 'flapping_detected')) as rule_based
                FROM alerts
                WHERE created_at > NOW() - INTERVAL '%s hours'
                  AND suppressed = true
            """ % hours)
            
            # Get total alerts (including suppressed)
            total = await conn.fetchval("""
                SELECT COUNT(*) FROM alerts
                WHERE created_at > NOW() - INTERVAL '%s hours'
            """ % hours)
            
            # Get active suppression rules
            active_rules = await conn.fetchval("""
                SELECT COUNT(*) FROM alert_suppression_rules
                WHERE is_active = true
            """)
            
            suppressed_dict = dict(suppressed) if suppressed else {}
            total_suppressed = suppressed_dict.get('total_suppressed', 0)
            
            return {
                'total_alerts': total or 0,
                'suppressed_alerts': total_suppressed,
                'visible_alerts': (total or 0) - total_suppressed,
                'suppression_rate': (total_suppressed / total * 100) if total else 0,
                'breakdown': {
                    'duplicates': suppressed_dict.get('duplicates', 0),
                    'rate_limited': suppressed_dict.get('rate_limited', 0),
                    'flapping': suppressed_dict.get('flapping', 0),
                    'rule_based': suppressed_dict.get('rule_based', 0)
                },
                'active_suppression_rules': active_rules,
                'time_period_hours': hours
            }
    
    async def apply_suppression(
        self,
        alert_id: UUID,
        suppression_reason: str
    ) -> None:
        """Mark an alert as suppressed"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE alerts
                SET suppressed = true,
                    suppression_reason = $2,
                    noise_score = 1.0
                WHERE id = $1
            """, alert_id, suppression_reason)
        
        logger.info(f"Alert {alert_id} suppressed: {suppression_reason}")


# Singleton instance
_noise_reduction_engine: Optional[NoiseReductionEngine] = None


async def get_noise_reduction_engine(db_pool) -> NoiseReductionEngine:
    """Get singleton noise reduction engine instance"""
    global _noise_reduction_engine
    
    if _noise_reduction_engine is None:
        _noise_reduction_engine = NoiseReductionEngine(db_pool)
    
    return _noise_reduction_engine
