"""
Anomaly Detection Engine for Smart Alerts

This module implements ML-based anomaly detection for device metrics using:
- Isolation Forest (primary ML model)
- Statistical methods (Z-score, moving averages)
- Baseline learning and adaptive thresholds

Epic 13: Smart Alerts - AI-Powered Anomaly Detection
"""

import asyncio
import logging
import pickle
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID
import numpy as np
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import asyncpg

logger = logging.getLogger(__name__)


class Baseline:
    """Statistical baseline for a metric"""
    
    def __init__(
        self,
        mean: float,
        std: float,
        median: float,
        percentile_25: float,
        percentile_75: float,
        percentile_95: float,
        percentile_99: float,
        min_value: float,
        max_value: float,
        sample_count: int
    ):
        self.mean = mean
        self.std = std
        self.median = median
        self.percentile_25 = percentile_25
        self.percentile_75 = percentile_75
        self.percentile_95 = percentile_95
        self.percentile_99 = percentile_99
        self.min_value = min_value
        self.max_value = max_value
        self.sample_count = sample_count
    
    def to_dict(self) -> Dict:
        """Convert baseline to dictionary for JSON storage"""
        return {
            'mean': float(self.mean),
            'std': float(self.std),
            'median': float(self.median),
            'percentile_25': float(self.percentile_25),
            'percentile_75': float(self.percentile_75),
            'percentile_95': float(self.percentile_95),
            'percentile_99': float(self.percentile_99),
            'min': float(self.min_value),
            'max': float(self.max_value),
            'sample_count': int(self.sample_count)
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Baseline':
        """Create baseline from dictionary"""
        return cls(
            mean=data['mean'],
            std=data['std'],
            median=data['median'],
            percentile_25=data['percentile_25'],
            percentile_75=data['percentile_75'],
            percentile_95=data['percentile_95'],
            percentile_99=data['percentile_99'],
            min_value=data['min'],
            max_value=data['max'],
            sample_count=data['sample_count']
        )
    
    def get_expected_range(self, confidence: float = 0.95) -> Tuple[float, float]:
        """
        Get expected range based on confidence level.
        
        Args:
            confidence: Confidence level (0.95 = 95%, 0.99 = 99%)
        
        Returns:
            Tuple of (min, max) expected values
        """
        if confidence >= 0.99:
            # 99th percentile range (very strict)
            return (self.percentile_25, self.percentile_99)
        elif confidence >= 0.95:
            # 95th percentile range (normal)
            return (self.percentile_25, self.percentile_95)
        else:
            # IQR range (lenient)
            iqr = self.percentile_75 - self.percentile_25
            return (self.percentile_25 - 1.5 * iqr, self.percentile_75 + 1.5 * iqr)


class AnomalyResult:
    """Result of anomaly detection"""
    
    def __init__(
        self,
        is_anomaly: bool,
        anomaly_score: float,
        confidence: float,
        severity: str,
        expected_value: Optional[float] = None,
        expected_range_min: Optional[float] = None,
        expected_range_max: Optional[float] = None,
        model_type: str = 'unknown',
        metadata: Optional[Dict] = None
    ):
        self.is_anomaly = is_anomaly
        self.anomaly_score = anomaly_score
        self.confidence = confidence
        self.severity = severity
        self.expected_value = expected_value
        self.expected_range_min = expected_range_min
        self.expected_range_max = expected_range_max
        self.model_type = model_type
        self.metadata = metadata or {}


class AnomalyDetector:
    """
    Main anomaly detection engine using ML and statistical methods.
    
    Detection Methods:
    1. Isolation Forest - Primary ML-based detection
    2. Z-Score - Fast statistical detection
    3. Moving Average - Trend-based detection
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.model_cache: Dict[str, Tuple[Any, datetime]] = {}
        self.baseline_cache: Dict[str, Tuple[Baseline, datetime]] = {}
        self.cache_ttl = timedelta(hours=1)  # Cache models for 1 hour
    
    async def detect_anomaly(
        self,
        device_id: UUID,
        metric_name: str,
        metric_value: float,
        timestamp: Optional[datetime] = None
    ) -> Optional[AnomalyResult]:
        """
        Detect if a metric value is anomalous.
        
        Args:
            device_id: Device UUID
            metric_name: Name of metric (cpu_usage, memory_usage, etc.)
            metric_value: Current metric value
            timestamp: Timestamp of metric (default: now)
        
        Returns:
            AnomalyResult if anomaly detected, None otherwise
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Try ML-based detection first (most accurate)
        ml_result = await self._detect_with_ml(device_id, metric_name, metric_value)
        if ml_result and ml_result.is_anomaly:
            return ml_result
        
        # Fall back to statistical detection
        stat_result = await self._detect_with_statistics(device_id, metric_name, metric_value)
        if stat_result and stat_result.is_anomaly:
            return stat_result
        
        # No anomaly detected
        return None
    
    async def _detect_with_ml(
        self,
        device_id: UUID,
        metric_name: str,
        metric_value: float
    ) -> Optional[AnomalyResult]:
        """Detect anomalies using Isolation Forest ML model"""
        
        # Get or load model
        model = await self._get_model(device_id, metric_name)
        if not model:
            logger.debug(f"No ML model available for {device_id}/{metric_name}")
            return None
        
        baseline = await self._get_baseline(device_id, metric_name)
        if not baseline:
            return None
        
        try:
            # Prepare feature vector (single value for now)
            X = np.array([[metric_value]])
            
            # Normalize using baseline stats
            if baseline.std > 0:
                X_normalized = (X - baseline.mean) / baseline.std
            else:
                X_normalized = X
            
            # Predict (-1 = anomaly, 1 = normal)
            prediction = model.predict(X_normalized)[0]
            
            # Get anomaly score (lower = more anomalous)
            score = model.score_samples(X_normalized)[0]
            
            # Convert score to 0-1 range (higher = more anomalous)
            # Isolation Forest scores are typically in range [-0.5, 0.5]
            anomaly_score = max(0.0, min(1.0, (-score + 0.5)))
            
            is_anomaly = prediction == -1
            
            if not is_anomaly:
                return None
            
            # Calculate expected range
            expected_min, expected_max = baseline.get_expected_range(0.95)
            
            # Determine severity based on how far outside expected range
            severity = self._calculate_severity(
                metric_value, baseline.mean, baseline.std, anomaly_score
            )
            
            return AnomalyResult(
                is_anomaly=True,
                anomaly_score=anomaly_score,
                confidence=min(0.99, anomaly_score),
                severity=severity,
                expected_value=baseline.mean,
                expected_range_min=expected_min,
                expected_range_max=expected_max,
                model_type='isolation_forest',
                metadata={
                    'raw_score': float(score),
                    'prediction': int(prediction),
                    'baseline_mean': baseline.mean,
                    'baseline_std': baseline.std
                }
            )
        
        except Exception as e:
            logger.error(f"ML detection failed for {device_id}/{metric_name}: {e}")
            return None
    
    async def _detect_with_statistics(
        self,
        device_id: UUID,
        metric_name: str,
        metric_value: float
    ) -> Optional[AnomalyResult]:
        """Detect anomalies using statistical Z-score method"""
        
        baseline = await self._get_baseline(device_id, metric_name)
        if not baseline or baseline.std == 0:
            return None
        
        # Calculate Z-score
        z_score = abs((metric_value - baseline.mean) / baseline.std)
        
        # Anomaly if |z-score| > 3 (99.7% confidence)
        is_anomaly = z_score > 3.0
        
        if not is_anomaly:
            return None
        
        # Anomaly score based on Z-score (normalized to 0-1)
        anomaly_score = min(1.0, z_score / 6.0)  # Cap at z=6
        
        # Expected range (mean ± 3*std)
        expected_min = baseline.mean - 3 * baseline.std
        expected_max = baseline.mean + 3 * baseline.std
        
        # Determine severity
        severity = self._calculate_severity(
            metric_value, baseline.mean, baseline.std, anomaly_score
        )
        
        return AnomalyResult(
            is_anomaly=True,
            anomaly_score=anomaly_score,
            confidence=min(0.99, anomaly_score),
            severity=severity,
            expected_value=baseline.mean,
            expected_range_min=expected_min,
            expected_range_max=expected_max,
            model_type='statistical',
            metadata={
                'z_score': float(z_score),
                'baseline_mean': baseline.mean,
                'baseline_std': baseline.std
            }
        )
    
    def _calculate_severity(
        self,
        value: float,
        mean: float,
        std: float,
        anomaly_score: float
    ) -> str:
        """
        Calculate severity level based on deviation from normal.
        
        Returns:
            'info', 'warning', 'error', or 'critical'
        """
        z_score = abs((value - mean) / std) if std > 0 else 0
        
        if z_score > 5 or anomaly_score > 0.9:
            return 'critical'
        elif z_score > 4 or anomaly_score > 0.7:
            return 'error'
        elif z_score > 3 or anomaly_score > 0.5:
            return 'warning'
        else:
            return 'info'
    
    async def _get_model(self, device_id: UUID, metric_name: str) -> Optional[IsolationForest]:
        """Get or load ML model from cache/database"""
        
        cache_key = f"{device_id}:{metric_name}"
        
        # Check cache
        if cache_key in self.model_cache:
            model, cached_at = self.model_cache[cache_key]
            if datetime.utcnow() - cached_at < self.cache_ttl:
                return model
        
        # Load from database
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT model_data, last_trained_at
                FROM smart_alert_models
                WHERE device_id = $1 AND metric_name = $2
                  AND status = 'active'
                  AND model_type = 'isolation_forest'
                ORDER BY last_trained_at DESC
                LIMIT 1
            """, device_id, metric_name)
            
            if not row:
                return None
            
            try:
                # Deserialize model
                model_data = row['model_data']
                model = pickle.loads(model_data['model_pickle'])
                
                # Cache it
                self.model_cache[cache_key] = (model, datetime.utcnow())
                
                return model
            
            except Exception as e:
                logger.error(f"Failed to load model for {device_id}/{metric_name}: {e}")
                return None
    
    async def _get_baseline(self, device_id: UUID, metric_name: str) -> Optional[Baseline]:
        """Get or load baseline statistics from cache/database"""
        
        cache_key = f"{device_id}:{metric_name}"
        
        # Check cache
        if cache_key in self.baseline_cache:
            baseline, cached_at = self.baseline_cache[cache_key]
            if datetime.utcnow() - cached_at < self.cache_ttl:
                return baseline
        
        # Load from database
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT baseline_stats
                FROM smart_alert_models
                WHERE device_id = $1 AND metric_name = $2
                  AND status = 'active'
                  AND baseline_stats IS NOT NULL
                ORDER BY last_trained_at DESC
                LIMIT 1
            """, device_id, metric_name)
            
            if not row or not row['baseline_stats']:
                return None
            
            try:
                baseline = Baseline.from_dict(row['baseline_stats'])
                
                # Cache it
                self.baseline_cache[cache_key] = (baseline, datetime.utcnow())
                
                return baseline
            
            except Exception as e:
                logger.error(f"Failed to load baseline for {device_id}/{metric_name}: {e}")
                return None
    
    async def train_model(
        self,
        device_id: UUID,
        metric_name: str,
        training_days: int = 30,
        contamination: float = 0.05
    ) -> bool:
        """
        Train Isolation Forest model on historical data.
        
        Args:
            device_id: Device UUID
            metric_name: Metric to train on
            training_days: Days of historical data to use
            contamination: Expected proportion of anomalies (0-1)
        
        Returns:
            True if training succeeded, False otherwise
        """
        logger.info(f"Training model for {device_id}/{metric_name} with {training_days} days")
        
        # Fetch historical data
        historical_data = await self._fetch_historical_data(
            device_id, metric_name, training_days
        )
        
        if len(historical_data) < 100:
            logger.warning(f"Insufficient data for {device_id}/{metric_name}: {len(historical_data)} samples")
            return False
        
        try:
            # Calculate baseline statistics
            baseline = self._calculate_baseline(historical_data)
            
            # Prepare training data
            X = np.array(historical_data).reshape(-1, 1)
            
            # Normalize
            scaler = StandardScaler()
            X_normalized = scaler.fit_transform(X)
            
            # Train Isolation Forest
            model = IsolationForest(
                contamination=contamination,
                random_state=42,
                n_estimators=100,
                max_samples='auto',
                bootstrap=False
            )
            model.fit(X_normalized)
            
            # Evaluate on training data
            predictions = model.predict(X_normalized)
            anomaly_count = (predictions == -1).sum()
            false_positive_rate = anomaly_count / len(predictions)
            
            # Calculate accuracy (how close to expected contamination)
            accuracy = 1.0 - abs(false_positive_rate - contamination)
            
            # Serialize model
            model_pickle = pickle.dumps(model)
            scaler_pickle = pickle.dumps(scaler)
            
            model_data = {
                'model_pickle': model_pickle,
                'scaler_pickle': scaler_pickle,
                'contamination': contamination,
                'n_estimators': 100
            }
            
            # Save to database
            async with self.db_pool.acquire() as conn:
                training_start = datetime.utcnow() - timedelta(days=training_days)
                training_end = datetime.utcnow()
                
                await conn.execute("""
                    INSERT INTO smart_alert_models (
                        device_id, metric_name, model_type, model_data, baseline_stats,
                        training_data_start, training_data_end, accuracy_score,
                        false_positive_rate, status, version
                    ) VALUES (
                        $1, $2, 'isolation_forest', $3, $4, $5, $6, $7, $8, 'active', 1
                    )
                """, device_id, metric_name, json.dumps(model_data), 
                     json.dumps(baseline.to_dict()), training_start, training_end,
                     accuracy, false_positive_rate)
            
            logger.info(
                f"Model trained successfully for {device_id}/{metric_name}: "
                f"accuracy={accuracy:.2%}, fpr={false_positive_rate:.2%}"
            )
            
            # Clear cache to force reload
            cache_key = f"{device_id}:{metric_name}"
            self.model_cache.pop(cache_key, None)
            self.baseline_cache.pop(cache_key, None)
            
            return True
        
        except Exception as e:
            logger.error(f"Model training failed for {device_id}/{metric_name}: {e}")
            return False
    
    async def _fetch_historical_data(
        self,
        device_id: UUID,
        metric_name: str,
        days: int
    ) -> List[float]:
        """Fetch historical metric data from database"""
        
        # TODO: This depends on your metrics storage structure
        # For now, return dummy data for testing
        
        # In production, this would query your metrics database:
        # async with self.db_pool.acquire() as conn:
        #     rows = await conn.fetch("""
        #         SELECT metric_value
        #         FROM device_metrics
        #         WHERE device_id = $1 AND metric_name = $2
        #           AND timestamp > NOW() - INTERVAL '$3 days'
        #         ORDER BY timestamp
        #     """, device_id, metric_name, days)
        #     return [row['metric_value'] for row in rows]
        
        logger.warning(f"Using simulated data for {device_id}/{metric_name}")
        
        # Simulated normal data with some noise
        np.random.seed(int(str(device_id)[:8], 16) % (2**32))
        
        # Generate realistic metric data based on metric type
        if 'cpu' in metric_name.lower():
            # CPU: 20-60% with occasional spikes
            data = np.random.normal(40, 10, 2000).tolist()
        elif 'memory' in metric_name.lower():
            # Memory: 50-70% slowly increasing
            data = np.random.normal(60, 8, 2000).tolist()
        elif 'disk' in metric_name.lower():
            # Disk: 30-50% slowly increasing
            data = np.linspace(35, 45, 2000) + np.random.normal(0, 3, 2000)
            data = data.tolist()
        else:
            # Generic metric
            data = np.random.normal(50, 15, 2000).tolist()
        
        # Clip to valid range
        return [max(0, min(100, x)) for x in data]
    
    def _calculate_baseline(self, data: List[float]) -> Baseline:
        """Calculate baseline statistics from historical data"""
        
        arr = np.array(data)
        
        return Baseline(
            mean=float(np.mean(arr)),
            std=float(np.std(arr)),
            median=float(np.median(arr)),
            percentile_25=float(np.percentile(arr, 25)),
            percentile_75=float(np.percentile(arr, 75)),
            percentile_95=float(np.percentile(arr, 95)),
            percentile_99=float(np.percentile(arr, 99)),
            min_value=float(np.min(arr)),
            max_value=float(np.max(arr)),
            sample_count=len(arr)
        )
    
    async def save_anomaly(
        self,
        device_id: UUID,
        metric_name: str,
        metric_value: float,
        result: AnomalyResult,
        model_id: Optional[UUID] = None
    ) -> UUID:
        """
        Save detected anomaly to database.
        
        Returns:
            UUID of created anomaly detection record
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO anomaly_detections (
                    device_id, metric_name, metric_value, expected_value,
                    expected_range_min, expected_range_max, anomaly_score,
                    model_id, model_type, confidence, severity, metadata
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
                )
                RETURNING id
            """, device_id, metric_name, metric_value, result.expected_value,
                 result.expected_range_min, result.expected_range_max,
                 result.anomaly_score, model_id, result.model_type,
                 result.confidence, result.severity, json.dumps(result.metadata))
            
            return row['id']
    
    async def train_all_models(self, organization_id: Optional[str] = None):
        """
        Train models for all devices.
        
        This should be run periodically (e.g., weekly) to keep models updated.
        """
        logger.info("Starting batch model training...")
        
        # Get all devices
        async with self.db_pool.acquire() as conn:
            query = "SELECT id FROM devices WHERE status = 'active'"
            params = []
            
            if organization_id:
                query += " AND organization_id = $1"
                params.append(organization_id)
            
            devices = await conn.fetch(query, *params)
        
        metrics = ['cpu_usage', 'memory_usage', 'disk_usage', 'network_bytes']
        
        total = len(devices) * len(metrics)
        trained = 0
        failed = 0
        
        for device in devices:
            for metric in metrics:
                try:
                    success = await self.train_model(device['id'], metric)
                    if success:
                        trained += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"Training failed for {device['id']}/{metric}: {e}")
                    failed += 1
                
                # Small delay to avoid overwhelming the database
                await asyncio.sleep(0.1)
        
        logger.info(
            f"Batch training complete: {trained}/{total} succeeded, {failed} failed"
        )
