"""
Prediction Engine for Smart Alerts

Forecasts metric values and predicts threshold crossings to enable
proactive alerting before problems occur.

Epic 13: Smart Alerts - Prediction Engine
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
import json

import numpy as np
from scipy import stats
from sklearn.linear_model import LinearRegression
import pickle

logger = logging.getLogger(__name__)


@dataclass
class Prediction:
    """Prediction result for a metric"""
    metric_name: str
    device_id: UUID
    forecast_horizon_minutes: int
    predicted_value: float
    confidence_lower: float
    confidence_upper: float
    confidence_level: float
    model_type: str  # 'linear', 'arima', 'exponential'
    predicted_at: datetime
    
    def to_dict(self) -> dict:
        return {
            'metric_name': self.metric_name,
            'device_id': str(self.device_id),
            'forecast_horizon_minutes': self.forecast_horizon_minutes,
            'predicted_value': self.predicted_value,
            'confidence_lower': self.confidence_lower,
            'confidence_upper': self.confidence_upper,
            'confidence_level': self.confidence_level,
            'model_type': self.model_type,
            'predicted_at': self.predicted_at.isoformat()
        }


@dataclass
class ThresholdCrossing:
    """Prediction of when a threshold will be crossed"""
    metric_name: str
    device_id: UUID
    threshold_value: float
    threshold_type: str  # 'upper', 'lower'
    estimated_crossing_time: datetime
    confidence: float
    current_value: float
    trend: str  # 'increasing', 'decreasing', 'stable'
    growth_rate: float  # per hour
    
    def time_until_crossing(self) -> timedelta:
        """Calculate time remaining until threshold crossing"""
        return self.estimated_crossing_time - datetime.utcnow()
    
    def to_dict(self) -> dict:
        return {
            'metric_name': self.metric_name,
            'device_id': str(self.device_id),
            'threshold_value': self.threshold_value,
            'threshold_type': self.threshold_type,
            'estimated_crossing_time': self.estimated_crossing_time.isoformat(),
            'confidence': self.confidence,
            'current_value': self.current_value,
            'trend': self.trend,
            'growth_rate': self.growth_rate,
            'time_until_crossing_seconds': self.time_until_crossing().total_seconds()
        }


class PredictionEngine:
    """
    Prediction engine for forecasting metric values and threshold crossings.
    
    Uses multiple forecasting models:
    - Linear regression for trending metrics
    - Exponential smoothing for volatile metrics
    - ARIMA for complex time series patterns
    """
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self.prediction_cache: Dict[str, Tuple[Prediction, datetime]] = {}
        self.cache_ttl = timedelta(minutes=5)
        
        # Default thresholds for common metrics (percentage-based)
        self.default_thresholds = {
            'cpu_usage': {'warning': 70, 'critical': 90},
            'memory_usage': {'warning': 75, 'critical': 90},
            'disk_usage': {'warning': 80, 'critical': 95},
            'network_latency': {'warning': 100, 'critical': 200},  # ms
            'error_rate': {'warning': 5, 'critical': 10},  # percentage
        }
    
    async def predict_metric(
        self,
        device_id: UUID,
        metric_name: str,
        forecast_horizons: List[int] = [60, 180, 360]  # minutes
    ) -> List[Prediction]:
        """
        Predict metric values at multiple time horizons.
        
        Args:
            device_id: Device to predict for
            metric_name: Metric to forecast
            forecast_horizons: List of minutes into the future to predict
            
        Returns:
            List of predictions for each horizon
        """
        try:
            # Fetch historical data
            historical_data = await self._fetch_historical_data(
                device_id, metric_name, days=7
            )
            
            if len(historical_data) < 20:
                logger.warning(
                    f"Insufficient data for prediction: {device_id}/{metric_name} "
                    f"({len(historical_data)} points)"
                )
                return []
            
            # Select best forecasting model
            model_type = self._select_model_type(historical_data)
            
            predictions = []
            for horizon in forecast_horizons:
                pred = await self._forecast(
                    historical_data, horizon, model_type, device_id, metric_name
                )
                if pred:
                    predictions.append(pred)
                    
                    # Save to database
                    await self._save_prediction(pred, device_id)
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error predicting metric {device_id}/{metric_name}: {e}")
            return []
    
    async def predict_threshold_crossing(
        self,
        device_id: UUID,
        metric_name: str,
        custom_thresholds: Optional[Dict[str, float]] = None
    ) -> Optional[ThresholdCrossing]:
        """
        Predict when a metric will cross its threshold.
        
        Args:
            device_id: Device to check
            metric_name: Metric to monitor
            custom_thresholds: Optional custom thresholds (warning, critical)
            
        Returns:
            ThresholdCrossing if crossing predicted, None otherwise
        """
        try:
            # Get thresholds
            thresholds = custom_thresholds or self.default_thresholds.get(
                metric_name, {'warning': 80, 'critical': 90}
            )
            
            # Fetch recent data
            historical_data = await self._fetch_historical_data(
                device_id, metric_name, days=3
            )
            
            if len(historical_data) < 10:
                return None
            
            # Calculate trend
            current_value = historical_data[-1][1]
            trend_info = self._calculate_trend(historical_data)
            
            if trend_info['trend'] == 'stable':
                return None
            
            # Determine which threshold to check
            if trend_info['trend'] == 'increasing':
                threshold_value = thresholds.get('critical', 90)
                threshold_type = 'upper'
            else:  # decreasing
                threshold_value = thresholds.get('lower', 10)
                threshold_type = 'lower'
            
            # Check if already crossed
            if trend_info['trend'] == 'increasing' and current_value >= threshold_value:
                return None
            if trend_info['trend'] == 'decreasing' and current_value <= threshold_value:
                return None
            
            # Predict crossing time
            crossing_time = self._predict_crossing_time(
                historical_data, threshold_value, threshold_type
            )
            
            if not crossing_time:
                return None
            
            # Only alert if crossing within 6 hours
            if crossing_time > datetime.utcnow() + timedelta(hours=6):
                return None
            
            crossing = ThresholdCrossing(
                metric_name=metric_name,
                device_id=device_id,
                threshold_value=threshold_value,
                threshold_type=threshold_type,
                estimated_crossing_time=crossing_time,
                confidence=trend_info['confidence'],
                current_value=current_value,
                trend=trend_info['trend'],
                growth_rate=trend_info['rate_per_hour']
            )
            
            return crossing
            
        except Exception as e:
            logger.error(
                f"Error predicting threshold crossing {device_id}/{metric_name}: {e}"
            )
            return None
    
    async def detect_resource_exhaustion(
        self,
        device_id: UUID
    ) -> List[Dict[str, Any]]:
        """
        Detect potential resource exhaustion scenarios.
        
        Checks disk space, memory, and other critical resources.
        
        Returns:
            List of exhaustion predictions with time estimates
        """
        exhaustion_warnings = []
        
        # Check critical metrics
        critical_metrics = [
            ('disk_usage', 95),  # Critical at 95%
            ('memory_usage', 90),  # Critical at 90%
            ('connection_pool_usage', 90),
        ]
        
        for metric_name, critical_threshold in critical_metrics:
            crossing = await self.predict_threshold_crossing(
                device_id,
                metric_name,
                custom_thresholds={'critical': critical_threshold}
            )
            
            if crossing:
                time_remaining = crossing.time_until_crossing()
                
                exhaustion_warnings.append({
                    'resource': metric_name,
                    'current_usage': crossing.current_value,
                    'threshold': crossing.threshold_value,
                    'time_until_exhaustion': str(time_remaining),
                    'time_until_exhaustion_seconds': time_remaining.total_seconds(),
                    'estimated_exhaustion_time': crossing.estimated_crossing_time,
                    'growth_rate_per_hour': crossing.growth_rate,
                    'confidence': crossing.confidence,
                    'severity': self._calculate_exhaustion_severity(time_remaining)
                })
        
        return exhaustion_warnings
    
    def _select_model_type(self, data: List[Tuple[datetime, float]]) -> str:
        """
        Select best forecasting model based on data characteristics.
        
        Args:
            data: Historical time series data
            
        Returns:
            Model type ('linear', 'exponential', 'arima')
        """
        values = [v for _, v in data]
        
        # Calculate coefficient of variation
        cv = np.std(values) / (np.mean(values) + 1e-10)
        
        # Calculate autocorrelation at lag 1
        if len(values) > 10:
            autocorr = np.corrcoef(values[:-1], values[1:])[0, 1]
        else:
            autocorr = 0
        
        # Check for trend
        x = np.arange(len(values))
        slope, _, r_value, _, _ = stats.linregress(x, values)
        
        # Decision logic
        if abs(r_value) > 0.7:  # Strong linear trend
            return 'linear'
        elif cv > 0.3:  # High volatility
            return 'exponential'
        else:
            return 'linear'  # Default to linear (ARIMA too complex for now)
    
    async def _forecast(
        self,
        historical_data: List[Tuple[datetime, float]],
        horizon_minutes: int,
        model_type: str,
        device_id: UUID,
        metric_name: str
    ) -> Optional[Prediction]:
        """
        Generate forecast using specified model.
        
        Args:
            historical_data: Historical time series
            horizon_minutes: Minutes into future to predict
            model_type: Type of model to use
            device_id: Device ID
            metric_name: Metric name
            
        Returns:
            Prediction object
        """
        try:
            if model_type == 'linear':
                return self._forecast_linear(
                    historical_data, horizon_minutes, device_id, metric_name
                )
            elif model_type == 'exponential':
                return self._forecast_exponential(
                    historical_data, horizon_minutes, device_id, metric_name
                )
            else:
                return self._forecast_linear(
                    historical_data, horizon_minutes, device_id, metric_name
                )
        except Exception as e:
            logger.error(f"Error in forecast: {e}")
            return None
    
    def _forecast_linear(
        self,
        historical_data: List[Tuple[datetime, float]],
        horizon_minutes: int,
        device_id: UUID,
        metric_name: str
    ) -> Prediction:
        """Linear regression forecast"""
        times = np.array([(t - historical_data[0][0]).total_seconds() 
                         for t, _ in historical_data]).reshape(-1, 1)
        values = np.array([v for _, v in historical_data])
        
        # Train linear model
        model = LinearRegression()
        model.fit(times, values)
        
        # Predict
        future_time = times[-1][0] + (horizon_minutes * 60)
        predicted_value = model.predict([[future_time]])[0]
        
        # Calculate prediction interval (95% confidence)
        residuals = values - model.predict(times)
        mse = np.mean(residuals ** 2)
        std_error = np.sqrt(mse * (1 + 1/len(times)))
        margin = 1.96 * std_error  # 95% CI
        
        return Prediction(
            metric_name=metric_name,
            device_id=device_id,
            forecast_horizon_minutes=horizon_minutes,
            predicted_value=float(predicted_value),
            confidence_lower=float(predicted_value - margin),
            confidence_upper=float(predicted_value + margin),
            confidence_level=0.95,
            model_type='linear',
            predicted_at=datetime.utcnow()
        )
    
    def _forecast_exponential(
        self,
        historical_data: List[Tuple[datetime, float]],
        horizon_minutes: int,
        device_id: UUID,
        metric_name: str
    ) -> Prediction:
        """Exponential smoothing forecast"""
        values = np.array([v for _, v in historical_data])
        
        # Simple exponential smoothing
        alpha = 0.3  # Smoothing parameter
        smoothed = [values[0]]
        
        for i in range(1, len(values)):
            smoothed.append(alpha * values[i] + (1 - alpha) * smoothed[-1])
        
        # Forecast: use last smoothed value
        predicted_value = smoothed[-1]
        
        # Calculate prediction interval
        residuals = values[1:] - np.array(smoothed[1:])
        std = np.std(residuals)
        margin = 1.96 * std
        
        return Prediction(
            metric_name=metric_name,
            device_id=device_id,
            forecast_horizon_minutes=horizon_minutes,
            predicted_value=float(predicted_value),
            confidence_lower=float(predicted_value - margin),
            confidence_upper=float(predicted_value + margin),
            confidence_level=0.95,
            model_type='exponential',
            predicted_at=datetime.utcnow()
        )
    
    def _calculate_trend(
        self,
        historical_data: List[Tuple[datetime, float]]
    ) -> Dict[str, Any]:
        """
        Calculate trend information from historical data.
        
        Returns:
            Dict with trend, rate_per_hour, confidence
        """
        times = np.array([(t - historical_data[0][0]).total_seconds() / 3600 
                         for t, _ in historical_data])
        values = np.array([v for _, v in historical_data])
        
        # Linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(times, values)
        
        # Determine trend
        if abs(slope) < 0.1:
            trend = 'stable'
        elif slope > 0:
            trend = 'increasing'
        else:
            trend = 'decreasing'
        
        return {
            'trend': trend,
            'rate_per_hour': float(slope),
            'confidence': abs(float(r_value)),
            'p_value': float(p_value)
        }
    
    def _predict_crossing_time(
        self,
        historical_data: List[Tuple[datetime, float]],
        threshold: float,
        threshold_type: str
    ) -> Optional[datetime]:
        """
        Predict when metric will cross threshold based on trend.
        
        Args:
            historical_data: Time series data
            threshold: Threshold value
            threshold_type: 'upper' or 'lower'
            
        Returns:
            Estimated crossing time or None
        """
        times = np.array([(t - historical_data[0][0]).total_seconds() / 3600 
                         for t, _ in historical_data])
        values = np.array([v for _, v in historical_data])
        
        # Linear regression
        slope, intercept, r_value, _, _ = stats.linregress(times, values)
        
        # Check if trend is in right direction
        if threshold_type == 'upper' and slope <= 0:
            return None
        if threshold_type == 'lower' and slope >= 0:
            return None
        
        # Low confidence in trend
        if abs(r_value) < 0.5:
            return None
        
        # Calculate crossing time
        current_value = values[-1]
        current_time = times[-1]
        
        # Solve: threshold = slope * t + intercept
        hours_until_crossing = (threshold - intercept) / slope - current_time
        
        if hours_until_crossing <= 0:
            return None
        
        crossing_time = datetime.utcnow() + timedelta(hours=hours_until_crossing)
        
        return crossing_time
    
    def _calculate_exhaustion_severity(self, time_remaining: timedelta) -> str:
        """Calculate severity based on time until exhaustion"""
        hours = time_remaining.total_seconds() / 3600
        
        if hours < 1:
            return 'critical'
        elif hours < 4:
            return 'error'
        elif hours < 12:
            return 'warning'
        else:
            return 'info'
    
    async def _fetch_historical_data(
        self,
        device_id: UUID,
        metric_name: str,
        days: int = 7
    ) -> List[Tuple[datetime, float]]:
        """
        Fetch historical metric data.
        
        TODO: Replace with actual metrics database query
        
        Returns:
            List of (timestamp, value) tuples
        """
        # Simulated data for now
        # In production, query from metrics database
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=days)
        
        # Generate realistic time series with trend
        num_points = days * 24  # Hourly data
        times = [start_time + timedelta(hours=i) for i in range(num_points)]
        
        # Simulate trending data with noise
        trend = np.linspace(50, 75, num_points)  # Increasing trend
        noise = np.random.normal(0, 5, num_points)
        values = np.maximum(0, np.minimum(100, trend + noise))
        
        return list(zip(times, values.tolist()))
    
    async def _save_prediction(
        self,
        prediction: Prediction,
        device_id: UUID
    ) -> None:
        """Save prediction to database"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO alert_predictions (
                        device_id, metric_name, forecast_horizon_minutes,
                        predicted_value, confidence_lower, confidence_upper,
                        confidence_level, model_type, predicted_at, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                    device_id,
                    prediction.metric_name,
                    prediction.forecast_horizon_minutes,
                    prediction.predicted_value,
                    prediction.confidence_lower,
                    prediction.confidence_upper,
                    prediction.confidence_level,
                    prediction.model_type,
                    prediction.predicted_at,
                    json.dumps(prediction.to_dict())
                )
        except Exception as e:
            logger.error(f"Error saving prediction: {e}")
    
    async def get_predictions(
        self,
        device_id: Optional[UUID] = None,
        metric_name: Optional[str] = None,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Retrieve stored predictions.
        
        Args:
            device_id: Optional device filter
            metric_name: Optional metric filter
            hours: How many hours back to retrieve
            
        Returns:
            List of prediction records
        """
        conditions = ["predicted_at > NOW() - INTERVAL '%s hours'" % hours]
        params = []
        
        if device_id:
            conditions.append(f"device_id = ${len(params) + 1}")
            params.append(device_id)
        
        if metric_name:
            conditions.append(f"metric_name = ${len(params) + 1}")
            params.append(metric_name)
        
        where_clause = " AND ".join(conditions)
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT 
                    id, device_id, metric_name, forecast_horizon_minutes,
                    predicted_value, confidence_lower, confidence_upper,
                    confidence_level, model_type, predicted_at, metadata
                FROM alert_predictions
                WHERE {where_clause}
                ORDER BY predicted_at DESC
                LIMIT 100
            """, *params)
            
            return [dict(row) for row in rows]


# Singleton instance
_prediction_engine: Optional[PredictionEngine] = None


async def get_prediction_engine(db_pool) -> PredictionEngine:
    """Get singleton prediction engine instance"""
    global _prediction_engine
    
    if _prediction_engine is None:
        _prediction_engine = PredictionEngine(db_pool)
    
    return _prediction_engine
