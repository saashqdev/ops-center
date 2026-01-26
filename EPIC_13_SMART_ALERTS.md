# Epic 13: Smart Alerts - AI-Powered Anomaly Detection

> **Status**: 🚧 In Progress  
> **Priority**: P0 (Phase 2 - Intelligence)  
> **Phase**: Phase 2 - Intelligence  
> **Estimated Effort**: 2-3 weeks

## 📋 Executive Summary

**Smart Alerts** transforms Ops-Center's alerting system from reactive to proactive by leveraging AI and machine learning for anomaly detection, predictive alerting, and intelligent alert management. The system learns normal behavior patterns and predicts issues before they become critical.

### Vision Statement

"Detect problems before they impact users, reduce alert noise by 80%, and surface only actionable insights."

### Key Capabilities

- **Anomaly Detection**: ML-based detection of unusual patterns in metrics
- **Predictive Alerting**: Forecast issues before they occur (disk will fill in 4 hours)
- **Alert Correlation**: Group related alerts to identify root causes
- **Fatigue Reduction**: Smart deduplication and priority scoring
- **Adaptive Learning**: Continuously improves from feedback
- **Integration**: Works seamlessly with The Colonel and existing alerts

---

## 🎯 Goals & Objectives

### Primary Goals

1. **Reduce False Positives**: Cut noise by 80% through intelligent filtering
2. **Enable Prediction**: Alert 30+ minutes before critical issues
3. **Improve MTTR**: Reduce mean time to resolution by 50%
4. **Automate Triage**: Automatically prioritize and categorize alerts

### Success Metrics

- 80% reduction in alert volume
- 90% accuracy in anomaly detection
- 50% reduction in MTTR
- 95% of critical issues predicted before impact
- <5% false positive rate

### Non-Goals (v1)

- ❌ Auto-remediation (Epic 12 v2)
- ❌ Multi-server correlation (Epic 15)
- ❌ Custom ML model training UI
- ❌ Real-time streaming at millisecond latency

---

## 🏗️ Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Ingestion Layer                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Metrics Collector                                   │  │
│  │  - Device metrics (CPU, memory, disk, network)       │  │
│  │  - Application metrics                               │  │
│  │  - Custom metrics                                    │  │
│  │  - 1-minute resolution                               │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Time Series Database                        │
│  - Historical metrics (90 days retention)                    │
│  - Aggregations (1m, 5m, 1h, 1d)                            │
│  - Fast range queries                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Anomaly Detection Engine                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Statistical Models                                  │  │
│  │  - Z-score analysis                                  │  │
│  │  - Moving averages                                   │  │
│  │  - Seasonal decomposition                            │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Machine Learning Models                             │  │
│  │  - Isolation Forest (unsupervised)                   │  │
│  │  - LSTM for time series                              │  │
│  │  - AutoEncoder for patterns                          │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Pattern Recognition                                 │  │
│  │  - Baseline learning (7-day, 30-day)                 │  │
│  │  - Seasonal patterns                                 │  │
│  │  - Trend detection                                   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Prediction Engine                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Forecasting Models                                  │  │
│  │  - Linear regression                                 │  │
│  │  - Exponential smoothing                             │  │
│  │  - ARIMA for trend prediction                        │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Threshold Prediction                                │  │
│  │  - Time to threshold crossing                        │  │
│  │  - Confidence intervals                              │  │
│  │  - Resource exhaustion forecasts                     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                Alert Correlation Engine                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Grouping Logic                                      │  │
│  │  - Time-based windows (5 minutes)                    │  │
│  │  - Device-based grouping                             │  │
│  │  - Metric-based correlation                          │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Root Cause Analysis                                 │  │
│  │  - Dependency graphs                                 │  │
│  │  - Impact analysis                                   │  │
│  │  - Probable cause ranking                            │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Deduplication                                       │  │
│  │  - Signature matching                                │  │
│  │  - Similarity scoring                                │  │
│  │  - Update vs new alert logic                         │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Priority Scoring Engine                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Severity Calculation                                │  │
│  │  - Impact score (users affected)                     │  │
│  │  - Urgency score (time to critical)                  │  │
│  │  - Business impact                                   │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Noise Reduction                                     │  │
│  │  - Known issues suppression                          │  │
│  │  - Maintenance window filtering                      │  │
│  │  - Flapping detection                                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Alert Manager                             │
│  - Create/update smart alerts                                │
│  - Notification routing                                      │
│  - Feedback collection (was this useful?)                    │
│  - Integration with webhooks                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Learning & Feedback Loop                    │
│  - User feedback (thumbs up/down)                            │
│  - Model retraining (weekly)                                 │
│  - Baseline updates                                          │
│  - Performance metrics                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 💾 Database Schema

### New Tables

#### 1. `smart_alert_models`
Stores trained ML models and baselines.

```sql
CREATE TABLE smart_alert_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,  -- cpu_usage, memory_usage, etc.
    model_type VARCHAR(50) NOT NULL,  -- isolation_forest, statistical, lstm
    model_data JSONB NOT NULL,  -- Serialized model parameters
    baseline_stats JSONB,  -- Mean, std, percentiles
    training_data_start TIMESTAMP WITH TIME ZONE,
    training_data_end TIMESTAMP WITH TIME ZONE,
    accuracy_score FLOAT,
    false_positive_rate FLOAT,
    last_trained_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    version INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'active',  -- active, deprecated, training
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_smart_alert_models_device ON smart_alert_models(device_id);
CREATE INDEX idx_smart_alert_models_metric ON smart_alert_models(metric_name);
CREATE INDEX idx_smart_alert_models_status ON smart_alert_models(status);
```

#### 2. `anomaly_detections`
Records of detected anomalies.

```sql
CREATE TABLE anomaly_detections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metric_value FLOAT NOT NULL,
    expected_value FLOAT,
    expected_range_min FLOAT,
    expected_range_max FLOAT,
    anomaly_score FLOAT NOT NULL,  -- 0-1, higher = more anomalous
    model_id UUID REFERENCES smart_alert_models(id),
    model_type VARCHAR(50),
    confidence FLOAT,  -- 0-1
    severity VARCHAR(20),  -- info, warning, critical
    alert_id UUID REFERENCES alerts(id),  -- Created alert (if any)
    false_positive BOOLEAN,  -- User feedback
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_anomaly_detections_device ON anomaly_detections(device_id);
CREATE INDEX idx_anomaly_detections_metric ON anomaly_detections(metric_name);
CREATE INDEX idx_anomaly_detections_detected_at ON anomaly_detections(detected_at DESC);
CREATE INDEX idx_anomaly_detections_score ON anomaly_detections(anomaly_score DESC);
CREATE INDEX idx_anomaly_detections_alert ON anomaly_detections(alert_id);
```

#### 3. `alert_predictions`
Predictive alerts for future issues.

```sql
CREATE TABLE alert_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    prediction_type VARCHAR(50) NOT NULL,  -- threshold_crossing, resource_exhaustion
    predicted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    will_occur_at TIMESTAMP WITH TIME ZONE NOT NULL,  -- When issue will happen
    confidence FLOAT NOT NULL,  -- 0-1
    current_value FLOAT,
    predicted_value FLOAT,
    threshold_value FLOAT,
    time_to_critical_minutes INTEGER,  -- Minutes until critical
    recommendation TEXT,  -- What to do
    alert_id UUID REFERENCES alerts(id),  -- Created alert (if any)
    actually_occurred BOOLEAN,  -- Validation after prediction time
    accuracy_score FLOAT,  -- How accurate was the prediction
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_alert_predictions_device ON alert_predictions(device_id);
CREATE INDEX idx_alert_predictions_will_occur ON alert_predictions(will_occur_at);
CREATE INDEX idx_alert_predictions_confidence ON alert_predictions(confidence DESC);
CREATE INDEX idx_alert_predictions_created ON alert_predictions(created_at DESC);
```

#### 4. `alert_correlations`
Groups related alerts together.

```sql
CREATE TABLE alert_correlations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    correlation_group_id UUID NOT NULL,  -- Shared ID for correlated alerts
    alert_id UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    is_root_cause BOOLEAN DEFAULT false,
    correlation_score FLOAT,  -- 0-1, how related
    correlation_type VARCHAR(50),  -- time_based, device_based, metric_based, causal
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    UNIQUE(correlation_group_id, alert_id)
);

CREATE INDEX idx_alert_correlations_group ON alert_correlations(correlation_group_id);
CREATE INDEX idx_alert_correlations_alert ON alert_correlations(alert_id);
CREATE INDEX idx_alert_correlations_root_cause ON alert_correlations(is_root_cause);
CREATE INDEX idx_alert_correlations_detected ON alert_correlations(detected_at DESC);
```

#### 5. `alert_suppression_rules`
Rules to reduce alert noise.

```sql
CREATE TABLE alert_suppression_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    rule_type VARCHAR(50) NOT NULL,  -- maintenance_window, known_issue, flapping, duplicate
    conditions JSONB NOT NULL,  -- Match criteria
    action VARCHAR(50) DEFAULT 'suppress',  -- suppress, downgrade, group
    priority INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT true,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    created_by UUID REFERENCES users(id),
    alerts_suppressed INTEGER DEFAULT 0,
    last_matched_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_alert_suppression_rules_active ON alert_suppression_rules(active);
CREATE INDEX idx_alert_suppression_rules_org ON alert_suppression_rules(organization_id);
CREATE INDEX idx_alert_suppression_rules_expires ON alert_suppression_rules(expires_at);
```

#### 6. `alert_feedback`
User feedback on alert quality.

```sql
CREATE TABLE alert_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES alerts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    feedback_type VARCHAR(50) NOT NULL,  -- useful, false_positive, duplicate, noise
    rating INTEGER,  -- 1-5 stars
    comment TEXT,
    action_taken VARCHAR(100),  -- acknowledged, resolved, ignored
    time_to_acknowledge_seconds INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_alert_feedback_alert ON alert_feedback(alert_id);
CREATE INDEX idx_alert_feedback_user ON alert_feedback(user_id);
CREATE INDEX idx_alert_feedback_type ON alert_feedback(feedback_type);
CREATE INDEX idx_alert_feedback_created ON alert_feedback(created_at DESC);
```

### Enhanced Existing Tables

Add columns to existing `alerts` table:

```sql
ALTER TABLE alerts 
    ADD COLUMN IF NOT EXISTS is_smart_alert BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS anomaly_id UUID REFERENCES anomaly_detections(id),
    ADD COLUMN IF NOT EXISTS prediction_id UUID REFERENCES alert_predictions(id),
    ADD COLUMN IF NOT EXISTS priority_score FLOAT,
    ADD COLUMN IF NOT EXISTS correlation_group_id UUID,
    ADD COLUMN IF NOT EXISTS noise_score FLOAT,  -- 0-1, higher = likely noise
    ADD COLUMN IF NOT EXISTS ml_confidence FLOAT;  -- 0-1

CREATE INDEX idx_alerts_smart ON alerts(is_smart_alert);
CREATE INDEX idx_alerts_priority ON alerts(priority_score DESC);
CREATE INDEX idx_alerts_correlation_group ON alerts(correlation_group_id);
```

---

## 🧠 Machine Learning Models

### 1. Anomaly Detection Models

#### Isolation Forest (Primary)
- **Type**: Unsupervised learning
- **Purpose**: Detect outliers in multi-dimensional metric space
- **Training**: Weekly on 30 days of data
- **Features**: CPU, memory, disk, network metrics
- **Output**: Anomaly score (0-1)

```python
from sklearn.ensemble import IsolationForest

model = IsolationForest(
    contamination=0.05,  # Expected 5% anomalies
    random_state=42,
    n_estimators=100
)
```

#### Z-Score Statistical Model
- **Type**: Statistical
- **Purpose**: Fast detection of values beyond normal range
- **Training**: Rolling 7-day window
- **Threshold**: |z-score| > 3 = anomaly
- **Output**: Boolean + z-score

#### LSTM Time Series Model
- **Type**: Deep learning (future enhancement)
- **Purpose**: Learn temporal patterns
- **Training**: Monthly on 90 days
- **Features**: Sequential metric history
- **Output**: Expected value + confidence interval

### 2. Prediction Models

#### Linear Regression (Resource Exhaustion)
- **Purpose**: Predict disk/memory exhaustion time
- **Features**: Last 24 hours of growth rate
- **Output**: Time to 100% utilization

#### ARIMA (Trend Forecasting)
- **Purpose**: Forecast metric values 1-6 hours ahead
- **Training**: Daily on 30 days
- **Output**: Predicted value + confidence interval

### 3. Correlation Models

#### Graph-Based Causality
- **Purpose**: Identify root cause alerts
- **Method**: Dependency graph + temporal correlation
- **Output**: Root cause probability scores

---

## 🔧 Core Components

### 1. Anomaly Detection Engine

```python
class AnomalyDetector:
    """
    Detects anomalies in device metrics using multiple algorithms.
    """
    
    def detect_anomalies(
        self,
        device_id: UUID,
        metric_name: str,
        metric_value: float,
        timestamp: datetime
    ) -> Optional[Anomaly]:
        """
        Check if metric value is anomalous.
        
        Returns:
            Anomaly object if detected, None otherwise
        """
        
    def train_model(
        self,
        device_id: UUID,
        metric_name: str,
        historical_data: pd.DataFrame
    ) -> Model:
        """
        Train anomaly detection model on historical data.
        """
        
    def get_baseline(
        self,
        device_id: UUID,
        metric_name: str
    ) -> Baseline:
        """
        Get learned baseline for metric.
        """
```

### 2. Prediction Engine

```python
class PredictionEngine:
    """
    Predicts future metric values and threshold crossings.
    """
    
    def predict_threshold_crossing(
        self,
        device_id: UUID,
        metric_name: str,
        threshold: float
    ) -> Optional[Prediction]:
        """
        Predict when metric will cross threshold.
        
        Returns:
            Prediction with time estimate, or None if no crossing expected
        """
        
    def forecast_metric(
        self,
        device_id: UUID,
        metric_name: str,
        hours_ahead: int = 6
    ) -> List[ForecastPoint]:
        """
        Forecast metric values for next N hours.
        """
```

### 3. Alert Correlation Engine

```python
class AlertCorrelationEngine:
    """
    Groups related alerts and identifies root causes.
    """
    
    def correlate_alerts(
        self,
        time_window_minutes: int = 5
    ) -> List[CorrelationGroup]:
        """
        Find alerts that should be grouped together.
        """
        
    def find_root_cause(
        self,
        correlation_group: CorrelationGroup
    ) -> Optional[Alert]:
        """
        Identify most likely root cause alert in group.
        """
        
    def calculate_impact(
        self,
        alert: Alert
    ) -> ImpactScore:
        """
        Calculate downstream impact of alert.
        """
```

### 4. Noise Reduction Engine

```python
class NoiseReductionEngine:
    """
    Reduces alert fatigue through intelligent filtering.
    """
    
    def evaluate_alert(
        self,
        alert: Alert
    ) -> AlertEvaluation:
        """
        Determine if alert should be shown, suppressed, or downgraded.
        
        Returns:
            Evaluation with action and reasoning
        """
        
    def check_suppression_rules(
        self,
        alert: Alert
    ) -> Optional[SuppressionRule]:
        """
        Check if alert matches any suppression rules.
        """
        
    def detect_flapping(
        self,
        device_id: UUID,
        metric_name: str
    ) -> bool:
        """
        Detect if metric is flapping (rapidly changing states).
        """
```

---

## 📊 Alert Types

### 1. Anomaly Alerts
Triggered when ML detects unusual behavior.

**Example**:
```
⚠️ Anomaly Detected: CPU Usage Spike
Device: web-server-01
Current: 92% (normally 35-45%)
Anomaly Score: 0.89
Confidence: 94%
Model: Isolation Forest

Recommendation: Investigate processes consuming CPU
```

### 2. Predictive Alerts
Forecasts issues before they occur.

**Example**:
```
🔮 Prediction: Disk Space Will Be Full
Device: db-server-02
Current: 78% used
Predicted: 100% in 4 hours
Confidence: 87%

Recommendation: Free up space or add storage
Time to act: 4 hours
```

### 3. Correlated Alerts
Groups related issues with root cause.

**Example**:
```
🔗 Alert Group: Database Performance Issue
Root Cause: High CPU on db-server-02
Related Alerts (5):
  - Slow API responses (api-gateway)
  - Connection timeouts (app-server-01, 02, 03)
  - Queue backup (message-broker)

Impact: 15 devices affected
Recommendation: Address root cause first
```

---

## 🎯 Priority Scoring Algorithm

```python
def calculate_priority_score(alert: Alert) -> float:
    """
    Calculate priority score (0-100).
    
    Factors:
    - Severity (30%): critical=30, warning=20, info=10
    - Impact (25%): Number of affected devices/users
    - Urgency (25%): Time until critical (predictions)
    - Confidence (10%): ML model confidence
    - History (10%): Past similar alerts
    
    Returns:
        Score from 0-100 (100 = highest priority)
    """
    score = 0
    
    # Severity
    severity_scores = {"critical": 30, "error": 25, "warning": 20, "info": 10}
    score += severity_scores.get(alert.severity, 10)
    
    # Impact
    impact = alert.metadata.get("devices_affected", 1)
    score += min(25, impact * 2.5)
    
    # Urgency
    if alert.prediction_id:
        minutes_to_critical = alert.prediction.time_to_critical_minutes
        if minutes_to_critical < 30:
            score += 25
        elif minutes_to_critical < 120:
            score += 20
        else:
            score += 10
    
    # Confidence
    if alert.ml_confidence:
        score += alert.ml_confidence * 10
    
    # History
    similar_alerts = get_similar_alerts(alert)
    if similar_alerts:
        avg_resolution_time = calculate_avg_resolution(similar_alerts)
        if avg_resolution_time > 3600:  # Over 1 hour
            score += 10
    
    return min(100, score)
```

---

## 🔔 Alert Lifecycle with Smart Features

```
1. Metric Collection
   ↓
2. Anomaly Detection (runs every minute)
   ↓
3. [If anomalous] Create Smart Alert
   ↓
4. Prediction Check
   - Will this get worse?
   - Time to critical?
   ↓
5. Correlation Analysis
   - Group with related alerts
   - Identify root cause
   ↓
6. Noise Reduction
   - Check suppression rules
   - Detect duplicates
   - Evaluate if actionable
   ↓
7. Priority Scoring
   - Calculate priority (0-100)
   - Assign to severity tier
   ↓
8. Notification Routing
   - Send to appropriate channels
   - Apply escalation rules
   ↓
9. Feedback Collection
   - Was this useful?
   - False positive?
   ↓
10. Model Learning
    - Update baselines
    - Retrain models
```

---

## 📈 Training Pipeline

### Initial Training (First Run)

```python
def initial_training():
    """
    Train models for all devices on historical data.
    """
    devices = get_all_devices()
    metrics = ["cpu_usage", "memory_usage", "disk_usage", "network_bytes"]
    
    for device in devices:
        for metric in metrics:
            # Get 30 days of historical data
            data = get_historical_metrics(
                device_id=device.id,
                metric_name=metric,
                days=30
            )
            
            if len(data) < 1000:  # Need minimum data
                continue
            
            # Train Isolation Forest
            model = train_isolation_forest(data)
            
            # Calculate baseline statistics
            baseline = calculate_baseline(data)
            
            # Save model
            save_model(
                device_id=device.id,
                metric_name=metric,
                model=model,
                baseline=baseline
            )
```

### Continuous Learning

```python
def retrain_models():
    """
    Retrain models weekly with new data.
    Runs as scheduled job.
    """
    models = get_active_models()
    
    for model in models:
        # Get fresh 30-day window
        data = get_historical_metrics(
            device_id=model.device_id,
            metric_name=model.metric_name,
            days=30
        )
        
        # Retrain
        new_model = train_isolation_forest(data)
        
        # Evaluate performance
        accuracy = evaluate_model(new_model, validation_data)
        
        if accuracy > model.accuracy_score:
            # Better model, deploy it
            deploy_model(new_model)
        else:
            # Keep existing model
            logger.info(f"Model {model.id} performance degraded, keeping old version")
```

---

## 🎨 Dashboard Components

### 1. Smart Alerts Dashboard

**Sections**:
- Active Smart Alerts (sorted by priority)
- Predictive Warnings (issues forecasted)
- Alert Groups (correlated alerts)
- Noise Suppressed (filtered alerts)

**Features**:
- Filterable by priority, device, type
- Visual timeline of alert correlations
- Confidence meters for predictions
- Quick feedback buttons (useful/not useful)

### 2. Anomaly Detection View

**Visualizations**:
- Metric charts with anomaly markers
- Expected range bands (confidence intervals)
- Anomaly score trends
- Model accuracy metrics

### 3. Alert Analytics

**Metrics**:
- False positive rate (%)
- Average time to resolution
- Noise reduction savings (%)
- Prediction accuracy (%)
- Model performance scores

---

## 🔌 API Endpoints

### Anomaly Detection

```
GET  /api/smart-alerts/anomalies
GET  /api/smart-alerts/anomalies/{id}
POST /api/smart-alerts/anomalies/feedback

GET  /api/smart-alerts/models
GET  /api/smart-alerts/models/{device_id}/{metric}
POST /api/smart-alerts/models/{device_id}/retrain
```

### Predictions

```
GET  /api/smart-alerts/predictions
GET  /api/smart-alerts/predictions/{id}
POST /api/smart-alerts/predictions/validate

GET  /api/smart-alerts/forecasts/{device_id}/{metric}
```

### Alert Correlation

```
GET  /api/smart-alerts/correlations
GET  /api/smart-alerts/correlations/groups
GET  /api/smart-alerts/correlations/{group_id}

POST /api/smart-alerts/correlations/merge
POST /api/smart-alerts/correlations/split
```

### Suppression Rules

```
GET    /api/smart-alerts/suppression-rules
POST   /api/smart-alerts/suppression-rules
GET    /api/smart-alerts/suppression-rules/{id}
PATCH  /api/smart-alerts/suppression-rules/{id}
DELETE /api/smart-alerts/suppression-rules/{id}
```

### Analytics

```
GET /api/smart-alerts/analytics/overview
GET /api/smart-alerts/analytics/model-performance
GET /api/smart-alerts/analytics/feedback-summary
GET /api/smart-alerts/analytics/noise-reduction
```

---

## 🔮 Example Scenarios

### Scenario 1: Disk Space Prediction

```python
# System detects disk growing at 5% per hour
current_usage = 78%
growth_rate = 5% per hour
threshold = 95%

# Prediction
hours_to_full = (95 - 78) / 5 = 3.4 hours
confidence = 0.92

# Alert created
Alert(
    title="Disk Space Will Be Full in 3.4 Hours",
    severity="warning",
    type="predictive",
    device="db-server-02",
    time_to_critical=204,  # minutes
    recommendation="Free up space or add storage",
    confidence=0.92
)
```

### Scenario 2: CPU Anomaly Detection

```python
# Normal CPU: 30-45%
# Current CPU: 92%
# Z-score: 4.2 (highly anomalous)

# Isolation Forest score: 0.89 (anomaly)

# Alert created
Alert(
    title="CPU Usage Anomaly Detected",
    severity="warning",
    type="anomaly",
    device="web-server-01",
    anomaly_score=0.89,
    expected_range="30-45%",
    actual_value="92%",
    confidence=0.94
)
```

### Scenario 3: Alert Correlation

```python
# Multiple alerts in 5-minute window:
# 1. DB CPU high (10:30)
# 2. API slow responses (10:31)
# 3. Connection timeouts (10:32)
# 4. Queue backup (10:33)

# Correlation engine identifies:
# Root cause: Alert #1 (DB CPU high)
# Impacted: Alerts #2, #3, #4

# Creates correlation group
CorrelationGroup(
    id="group-123",
    root_cause_alert=alert_1,
    related_alerts=[alert_2, alert_3, alert_4],
    correlation_score=0.95,
    type="causal",
    recommendation="Address DB performance first"
)
```

---

## 💰 Cost Analysis

### Computational Costs

**Training**:
- Initial training: 1-2 hours CPU time
- Weekly retraining: 10-30 minutes
- Cost: Negligible (uses existing infrastructure)

**Inference**:
- Per metric evaluation: <1ms
- Models run in-memory
- Cost: Negligible

### Storage Costs

**Per Device**:
- Model data: ~100KB
- Anomaly records: ~1KB each
- 90 days metrics: ~10MB

**1000 Devices**:
- Models: 100MB
- Metrics: 10GB
- Total: ~10GB additional storage

**Very cost-effective!**

---

## 📊 Success Metrics

### Quantitative

- ✅ 80% reduction in alert volume
- ✅ 90% anomaly detection accuracy
- ✅ 95% prediction accuracy (6-hour window)
- ✅ <5% false positive rate
- ✅ 50% reduction in MTTR

### Qualitative

- ✅ Users report less alert fatigue
- ✅ More actionable insights
- ✅ Faster incident resolution
- ✅ Proactive issue prevention

---

## 🚀 Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Database schema migration
- [ ] Data collection pipeline
- [ ] Baseline statistical models

### Phase 2: ML Models (Week 2)
- [ ] Isolation Forest implementation
- [ ] Model training pipeline
- [ ] Anomaly detection engine

### Phase 3: Predictions (Week 2)
- [ ] Forecasting models
- [ ] Threshold prediction
- [ ] Resource exhaustion detection

### Phase 4: Correlation (Week 3)
- [ ] Alert grouping logic
- [ ] Root cause analysis
- [ ] Dependency graphs

### Phase 5: Noise Reduction (Week 3)
- [ ] Suppression rules engine
- [ ] Flapping detection
- [ ] Priority scoring

### Phase 6: UI & API (Week 3-4)
- [ ] Smart Alerts dashboard
- [ ] API endpoints
- [ ] Feedback mechanisms

---

## 🎯 Integration Points

### With The Colonel
The Colonel can query smart alerts:
- "Show me predictive alerts"
- "What anomalies were detected today?"
- "Which alerts are correlated?"

### With Existing Alerts
Smart alerts augment, don't replace:
- Traditional alerts still work
- Smart features add metadata
- Gradual migration path

### With Webhooks
Smart alerts trigger webhooks:
- Same notification channels
- Enhanced metadata
- Priority-based routing

---

## 🔒 Privacy & Security

- ✅ All ML models trained per-organization (no cross-org learning)
- ✅ Historical data stays in database (not sent to external services)
- ✅ Models run on-premise (no cloud ML services)
- ✅ User feedback anonymized for aggregate analysis

---

## ✅ Success Criteria

### Launch Criteria
- ✅ Models trained for all active devices
- ✅ <100ms latency for anomaly detection
- ✅ >85% accuracy on validation data
- ✅ UI showing all smart alert types
- ✅ Feedback mechanism working

### Post-Launch (30 days)
- 70% reduction in alert noise
- 80% user satisfaction
- >90% prediction accuracy
- <10% false positive rate

---

## 🎓 Conclusion

Smart Alerts transforms Ops-Center from reactive monitoring to proactive intelligence. By leveraging ML for anomaly detection, predictive analytics for early warning, and correlation for root cause analysis, we dramatically reduce alert fatigue while catching issues before they impact users.

Combined with The Colonel AI assistant, users get both intelligent alerts AND an AI agent to help investigate and resolve them.

**Let's build the smartest alerting system in the industry! 🎯**
