"""
Smart Alerts Service - Real-time Anomaly Monitoring

This service monitors incoming metrics and triggers anomaly detection.
Runs continuously to process metrics and create smart alerts.

Epic 13: Smart Alerts
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from uuid import UUID
import asyncpg

from anomaly_detector import AnomalyDetector, AnomalyResult
from prediction_engine import get_prediction_engine
from alert_correlation_engine import get_correlation_engine
from noise_reduction_engine import get_noise_reduction_engine

logger = logging.getLogger(__name__)


class SmartAlertsService:
    """
    Main service for Smart Alerts system.
    
    Responsibilities:
    - Monitor metrics for anomalies
    - Create smart alerts when anomalies detected
    - Manage model training schedule
    - Clean up old data
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.detector = AnomalyDetector(db_pool)
        self.prediction_engine = None  # Initialized in start()
        self.correlation_engine = None  # Initialized in start()
        self.noise_reduction_engine = None  # Initialized in start()
        self.running = False
        self.metrics_queue: asyncio.Queue = asyncio.Queue()
    
    async def start(self):
        """Start the Smart Alerts service"""
        logger.info("Starting Smart Alerts Service...")
        self.running = True
        self.prediction_engine = await get_prediction_engine(self.db_pool)
        self.correlation_engine = await get_correlation_engine(self.db_pool)
        self.noise_reduction_engine = await get_noise_reduction_engine(self.db_pool)
        
        # Start background tasks
        tasks = [
            asyncio.create_task(self._process_metrics_loop()),
            asyncio.create_task(self._model_training_loop()),
            asyncio.create_task(self._cleanup_loop()),
            asyncio.create_task(self._prediction_loop()),
            asyncio.create_task(self._correlation_loop())
        ]
        
        logger.info("Smart Alerts Service started successfully")
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Smart Alerts Service stopping...")
            self.running = False
    
    async def stop(self):
        """Stop the Smart Alerts service"""
        logger.info("Stopping Smart Alerts Service...")
        self.running = False
    
    async def process_metric(
        self,
        device_id: UUID,
        metric_name: str,
        metric_value: float,
        timestamp: Optional[datetime] = None
    ):
        """
        Process a single metric for anomaly detection.
        
        This is called when a new metric is collected.
        Can be called synchronously or queued for async processing.
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        try:
            # Detect anomaly
            result = await self.detector.detect_anomaly(
                device_id, metric_name, metric_value, timestamp
            )
            
            if result is None:
                # No anomaly detected
                return
            
            logger.info(
                f"Anomaly detected: {device_id}/{metric_name} = {metric_value} "
                f"(score={result.anomaly_score:.2f}, severity={result.severity})"
            )
            
            # Save anomaly detection
            anomaly_id = await self.detector.save_anomaly(
                device_id, metric_name, metric_value, result
            )
            
            # Create smart alert if severity warrants it
            if result.severity in ['error', 'critical']:
                await self._create_smart_alert(
                    device_id, metric_name, metric_value, result, anomaly_id
                )
        
        except Exception as e:
            logger.error(f"Error processing metric {device_id}/{metric_name}: {e}")
    
    async def _create_smart_alert(
        self,
        device_id: UUID,
        metric_name: str,
        metric_value: float,
        result: AnomalyResult,
        anomaly_id: UUID
    ):
        """Create a smart alert for detected anomaly"""
        
        async with self.db_pool.acquire() as conn:
            # Check if alert already exists for this anomaly
            existing = await conn.fetchval("""
                SELECT id FROM alerts
                WHERE anomaly_id = $1
            """, anomaly_id)
            
            if existing:
                logger.debug(f"Alert already exists for anomaly {anomaly_id}")
                return
            
            # Get device info
            device = await conn.fetchrow("""
                SELECT device_name, organization_id FROM devices
                WHERE id = $1
            """, device_id)
            
            if not device:
                logger.error(f"Device not found: {device_id}")
                return
            
            # Create alert title and message
            title = f"Anomaly Detected: {metric_name} on {device['device_name']}"
            
            expected_str = ""
            if result.expected_range_min and result.expected_range_max:
                expected_str = f" (expected {result.expected_range_min:.1f}-{result.expected_range_max:.1f})"
            
            message = (
                f"Unusual {metric_name} detected on {device['device_name']}.\n\n"
                f"Current value: {metric_value:.2f}{expected_str}\n"
                f"Anomaly score: {result.anomaly_score:.2%}\n"
                f"Confidence: {result.confidence:.2%}\n"
                f"Detection method: {result.model_type}\n\n"
                f"This was detected by ML-based anomaly detection."
            )
            
            # Check noise reduction - should this alert be suppressed?
            should_suppress, suppression_reason = await self.noise_reduction_engine.should_suppress_alert(
                device_id=device_id,
                alert_type='anomaly',
                alert_message=message,
                severity=result.severity
            )
            
            # Calculate priority score (0-100)
            priority_score = self._calculate_priority(result, metric_name)
            
            # Create alert (suppressed or visible)
            alert_id = await conn.fetchval("""
                INSERT INTO alerts (
                    device_id, organization_id, title, message, severity,
                    is_smart_alert, anomaly_id, priority_score, ml_confidence,
                    status, created_at, suppressed, suppression_reason, noise_score
                ) VALUES (
                    $1, $2, $3, $4, $5, true, $6, $7, $8, 'open', NOW(), $9, $10, $11
                )
                RETURNING id
            """, device_id, device['organization_id'], title, message,
                 result.severity, anomaly_id, priority_score, result.confidence,
                 should_suppress, suppression_reason, 1.0 if should_suppress else 0.0)
            
            if should_suppress:
                logger.info(
                    f"Alert {alert_id} created but suppressed (reason: {suppression_reason})"
                )
            else:
                logger.info(f"Created smart alert {alert_id} for anomaly {anomaly_id}")
                # TODO: Trigger webhook/notification only for visible alerts
    
    def _calculate_priority(self, result: AnomalyResult, metric_name: str) -> float:
        """
        Calculate priority score (0-100) for alert.
        
        Factors:
        - Severity (30%)
        - Anomaly score (30%)
        - Confidence (20%)
        - Metric criticality (20%)
        """
        score = 0.0
        
        # Severity component (30 points)
        severity_scores = {
            'critical': 30,
            'error': 25,
            'warning': 20,
            'info': 10
        }
        score += severity_scores.get(result.severity, 10)
        
        # Anomaly score component (30 points)
        score += result.anomaly_score * 30
        
        # Confidence component (20 points)
        score += result.confidence * 20
        
        # Metric criticality (20 points)
        critical_metrics = {'cpu_usage', 'memory_usage', 'disk_usage'}
        if metric_name in critical_metrics:
            score += 20
        elif 'error' in metric_name or 'latency' in metric_name:
            score += 15
        else:
            score += 10
        
        return min(100.0, score)
    
    async def _process_metrics_loop(self):
        """Background task to process queued metrics"""
        logger.info("Starting metrics processing loop...")
        
        while self.running:
            try:
                # Process queued metrics
                while not self.metrics_queue.empty():
                    metric_data = await self.metrics_queue.get()
                    await self.process_metric(**metric_data)
                
                # Sleep briefly
                await asyncio.sleep(1)
            
            except Exception as e:
                logger.error(f"Error in metrics processing loop: {e}")
                await asyncio.sleep(5)
    
    async def _model_training_loop(self):
        """Background task to retrain models periodically"""
        logger.info("Starting model training loop...")
        
        # Wait a bit before first training
        await asyncio.sleep(60)
        
        while self.running:
            try:
                # Train models once per week
                logger.info("Starting weekly model training...")
                await self.detector.train_all_models()
                logger.info("Weekly model training complete")
                
                # Sleep for 7 days
                await asyncio.sleep(7 * 24 * 3600)
            
            except Exception as e:
                logger.error(f"Error in model training loop: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour
    
    async def _cleanup_loop(self):
        """Background task to clean up old data"""
        logger.info("Starting cleanup loop...")
        
        # Wait before first cleanup
        await asyncio.sleep(3600)
        
        while self.running:
            try:
                # Clean up old anomaly detections (keep 90 days)
                async with self.db_pool.acquire() as conn:
                    deleted = await conn.fetchval("""
                        DELETE FROM anomaly_detections
                        WHERE created_at < NOW() - INTERVAL '90 days'
                        RETURNING COUNT(*)
                    """)
                    
                    if deleted:
                        logger.info(f"Cleaned up {deleted} old anomaly detections")
                    
                    # Clean up old models (keep active + last 3 versions)
                    await conn.execute("""
                        DELETE FROM smart_alert_models
                        WHERE id NOT IN (
                            SELECT id FROM (
                                SELECT id, ROW_NUMBER() OVER (
                                    PARTITION BY device_id, metric_name
                                    ORDER BY last_trained_at DESC
                                ) as rn
                                FROM smart_alert_models
                            ) t
                            WHERE rn <= 3
                        )
                    """)
                
                # Run cleanup daily
                await asyncio.sleep(24 * 3600)
            
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(3600)
    
    async def get_anomalies(
        self,
        device_id: Optional[UUID] = None,
        metric_name: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get detected anomalies with filters.
        
        Returns list of anomaly detection records.
        """
        async with self.db_pool.acquire() as conn:
            conditions = []
            params = []
            param_idx = 1
            
            if device_id:
                conditions.append(f"device_id = ${param_idx}")
                params.append(device_id)
                param_idx += 1
            
            if metric_name:
                conditions.append(f"metric_name = ${param_idx}")
                params.append(metric_name)
                param_idx += 1
            
            if severity:
                conditions.append(f"severity = ${param_idx}")
                params.append(severity)
                param_idx += 1
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            params.extend([limit, offset])
            
            rows = await conn.fetch(f"""
                SELECT 
                    id, device_id, metric_name, detected_at, metric_value,
                    expected_value, expected_range_min, expected_range_max,
                    anomaly_score, model_type, confidence, severity,
                    alert_id, false_positive, metadata
                FROM anomaly_detections
                {where_clause}
                ORDER BY detected_at DESC
                LIMIT ${param_idx} OFFSET ${param_idx + 1}
            """, *params)
            
            return [dict(row) for row in rows]
    
    async def get_model_performance(
        self,
        device_id: Optional[UUID] = None,
        metric_name: Optional[str] = None
    ) -> List[Dict]:
        """Get model performance metrics"""
        async with self.db_pool.acquire() as conn:
            conditions = ["status = 'active'"]
            params = []
            param_idx = 1
            
            if device_id:
                conditions.append(f"device_id = ${param_idx}")
                params.append(device_id)
                param_idx += 1
            
            if metric_name:
                conditions.append(f"metric_name = ${param_idx}")
                params.append(metric_name)
                param_idx += 1
            
            where_clause = "WHERE " + " AND ".join(conditions)
            
            rows = await conn.fetch(f"""
                SELECT 
                    device_id, metric_name, model_type,
                    accuracy_score, false_positive_rate,
                    last_trained_at, version,
                    (baseline_stats->>'sample_count')::int as training_samples
                FROM smart_alert_models
                {where_clause}
                ORDER BY last_trained_at DESC
            """, *params)
            
            return [dict(row) for row in rows]
    
    async def mark_false_positive(
        self,
        anomaly_id: UUID,
        user_id: UUID
    ):
        """Mark an anomaly as false positive (user feedback)"""
        async with self.db_pool.acquire() as conn:
            # Update anomaly
            await conn.execute("""
                UPDATE anomaly_detections
                SET false_positive = true
                WHERE id = $1
            """, anomaly_id)
            
            # Get associated alert
            alert_id = await conn.fetchval("""
                SELECT id FROM alerts WHERE anomaly_id = $1
            """, anomaly_id)
            
            if alert_id:
                # Add feedback
                await conn.execute("""
                    INSERT INTO alert_feedback (
                        alert_id, user_id, feedback_type, created_at
                    ) VALUES ($1, $2, 'false_positive', NOW())
                """, alert_id, user_id)
                
                # Close alert
                await conn.execute("""
                    UPDATE alerts
                    SET status = 'closed',
                        noise_score = 1.0
                    WHERE id = $1
                """, alert_id)
            
            logger.info(f"Marked anomaly {anomaly_id} as false positive")
    
    async def _prediction_loop(self):
        """
        Background task: Generate predictions and predictive alerts.
        Runs every hour to forecast metrics and detect threshold crossings.
        """
        while self.running:
            try:
                logger.info("Starting prediction cycle...")
                
                # Get active devices
                async with self.db_pool.acquire() as conn:
                    devices = await conn.fetch("""
                        SELECT DISTINCT id FROM devices WHERE status = 'active' LIMIT 100
                    """)
                
                predictions_created = 0
                alerts_created = 0
                
                critical_metrics = ['disk_usage', 'memory_usage', 'cpu_usage', 'error_rate']
                
                for device in devices:
                    device_id = device['id']
                    
                    # Check resource exhaustion
                    exhaustion_warnings = await self.prediction_engine.detect_resource_exhaustion(device_id)
                    
                    for warning in exhaustion_warnings:
                        if warning['severity'] in ['critical', 'error']:
                            await self._create_predictive_alert(device_id, warning)
                            alerts_created += 1
                    
                    # Generate forecasts
                    for metric_name in critical_metrics:
                        try:
                            predictions = await self.prediction_engine.predict_metric(
                                device_id, metric_name, [60, 180, 360]
                            )
                            predictions_created += len(predictions)
                            
                            # Check threshold crossings
                            crossing = await self.prediction_engine.predict_threshold_crossing(
                                device_id, metric_name
                            )
                            
                            if crossing:
                                time_remaining = crossing.time_until_crossing()
                                if time_remaining.total_seconds() < 21600:  # < 6 hours
                                    await self._create_threshold_crossing_alert(device_id, crossing)
                                    alerts_created += 1
                        except Exception as e:
                            logger.error(f"Error predicting {metric_name} for {device_id}: {e}")
                
                logger.info(f"Prediction cycle: {predictions_created} predictions, {alerts_created} alerts")
            except Exception as e:
                logger.error(f"Error in prediction loop: {e}")
            
            await asyncio.sleep(3600)  # 1 hour
    
    async def _create_predictive_alert(self, device_id: UUID, warning: Dict[str, Any]) -> Optional[UUID]:
        """Create predictive alert for resource exhaustion"""
        try:
            time_remaining = warning['time_until_exhaustion_seconds']
            hours = time_remaining / 3600
            time_str = f"{int(time_remaining / 60)} minutes" if hours < 1 else f"{hours:.1f} hours"
            
            alert_message = (
                f"Resource exhaustion predicted: {warning['resource']} will reach "
                f"{warning['threshold']}% in {time_str}. Current: {warning['current_usage']:.1f}%. "
                f"Growth: {warning['growth_rate_per_hour']:.2f}%/hour"
            )
            
            priority = 100 if hours < 1 else (90 if hours < 4 else (70 if hours < 12 else 50))
            
            async with self.db_pool.acquire() as conn:
                alert_id = await conn.fetchval("""
                    INSERT INTO alerts (
                        device_id, alert_type, severity, alert_message,
                        is_smart_alert, alert_category, priority_score,
                        ml_confidence, metadata, created_at, status
                    ) VALUES ($1, 'predictive', $2, $3, true, 'resource_exhaustion',
                              $4, $5, $6, NOW(), 'open')
                    RETURNING id
                """, device_id, warning['severity'], alert_message, priority,
                     warning['confidence'], json.dumps({
                         'prediction_type': 'resource_exhaustion',
                         'resource': warning['resource'],
                         'time_until_exhaustion_seconds': time_remaining
                     }))
            
            logger.info(f"Created predictive alert {alert_id} for {warning['resource']} on {device_id}")
            return alert_id
        except Exception as e:
            logger.error(f"Error creating predictive alert: {e}")
            return None
    
    async def _create_threshold_crossing_alert(self, device_id: UUID, crossing) -> Optional[UUID]:
        """Create alert for predicted threshold crossing"""
        try:
            time_remaining = crossing.time_until_crossing()
            hours = time_remaining.total_seconds() / 3600
            time_str = f"{int(time_remaining.total_seconds() / 60)} minutes" if hours < 1 else f"{hours:.1f} hours"
            
            alert_message = (
                f"Threshold crossing predicted: {crossing.metric_name} will reach "
                f"{crossing.threshold_value} in {time_str}. Current: {crossing.current_value:.1f}, "
                f"Trend: {crossing.trend} at {crossing.growth_rate:.2f}/hour"
            )
            
            if hours < 1:
                severity, priority = 'critical', 95
            elif hours < 4:
                severity, priority = 'error', 80
            else:
                severity, priority = 'warning', 60
            
            async with self.db_pool.acquire() as conn:
                alert_id = await conn.fetchval("""
                    INSERT INTO alerts (
                        device_id, alert_type, severity, alert_message,
                        is_smart_alert, alert_category, priority_score,
                        ml_confidence, metadata, created_at, status
                    ) VALUES ($1, 'predictive', $2, $3, true, 'threshold_crossing',
                              $4, $5, $6, NOW(), 'open')
                    RETURNING id
                """, device_id, severity, alert_message, priority,
                     crossing.confidence, json.dumps(crossing.to_dict()))
            
            logger.info(f"Created threshold crossing alert {alert_id} for {crossing.metric_name} on {device_id}")
            return alert_id
        except Exception as e:
            logger.error(f"Error creating threshold crossing alert: {e}")
            return None
    
    async def _correlation_loop(self):
        """
        Background task: Correlate related alerts.
        Runs every 5 minutes to find patterns and group alerts.
        """
        while self.running:
            try:
                logger.info("Starting alert correlation cycle...")
                
                # Analyze alerts from last 15 minutes
                correlations = await self.correlation_engine.correlate_alerts(
                    time_window_minutes=15
                )
                
                if correlations:
                    logger.info(
                        f"Alert correlation cycle completed: {len(correlations)} "
                        f"correlation groups found"
                    )
                    
                    # Log high-impact correlations
                    for correlation in correlations:
                        if correlation.impact_score >= 70:
                            logger.warning(
                                f"High-impact correlation detected: {correlation.correlation_type} "
                                f"with {len(correlation.alert_ids)} alerts, "
                                f"impact score: {correlation.impact_score:.1f}, "
                                f"root cause: {correlation.root_cause_alert_id}"
                            )
                else:
                    logger.info("Alert correlation cycle: No correlations found")
                
            except Exception as e:
                logger.error(f"Error in correlation loop: {e}", exc_info=True)
            
            # Sleep for 5 minutes
            await asyncio.sleep(300)


# Singleton instance
_service_instance: Optional[SmartAlertsService] = None


async def get_smart_alerts_service(db_pool: asyncpg.Pool) -> SmartAlertsService:
    """Get or create Smart Alerts service instance"""
    global _service_instance
    
    if _service_instance is None:
        _service_instance = SmartAlertsService(db_pool)
    
    return _service_instance


async def initialize_smart_alerts(db_pool: asyncpg.Pool):
    """Initialize Smart Alerts system on startup"""
    logger.info("Initializing Smart Alerts system...")
    
    service = await get_smart_alerts_service(db_pool)
    
    # Start service in background
    asyncio.create_task(service.start())
    
    logger.info("Smart Alerts system initialized")
