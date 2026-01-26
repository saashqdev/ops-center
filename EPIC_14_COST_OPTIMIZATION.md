# Epic 14: Cost Optimization Dashboard

**Status**: 🚧 In Progress  
**Priority**: P1 (High Value)  
**Phase**: Phase 2 - Intelligence  
**Epic Number**: 14

---

## 📋 Overview

Build a comprehensive cost optimization system that analyzes LLM usage, identifies savings opportunities, provides intelligent model routing recommendations, and enables budget management with forecasting capabilities.

### Vision Statement

"Enable organizations to reduce LLM costs by 30-50% through intelligent analysis, automated recommendations, and predictive budget management—while maintaining or improving service quality."

---

## 🎯 Goals

### Primary Goals
1. **Cost Visibility**: Complete transparency into LLM spending across models, users, and organizations
2. **Savings Identification**: Automated detection of cost optimization opportunities
3. **Budget Management**: Proactive budget tracking with forecasting and alerts
4. **Smart Recommendations**: AI-powered suggestions for model routing and optimization
5. **Cost Attribution**: Accurate per-organization and per-user cost allocation

### Success Metrics
- 30-50% cost reduction for organizations using recommendations
- 95% accuracy in cost forecasting (7-day horizon)
- <2 second dashboard load time
- 90% user adoption of recommendations
- Zero billing surprises (proactive budget alerts)

### Non-Goals for v1
- ❌ Multi-cloud cost optimization (AWS, GCP, Azure)
- ❌ Infrastructure cost optimization (compute, storage)
- ❌ Automated model switching (requires user approval)
- ❌ Contract negotiation with LLM providers
- ❌ Real-time budget enforcement (daily checks only)

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Cost Optimization Dashboard               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────┐ │
│  │  Cost Analysis   │  │    Budget        │  │  Savings  │ │
│  │     Engine       │  │   Management     │  │  Detector │ │
│  │                  │  │                  │  │           │ │
│  │ - Usage tracking │  │ - Budget limits  │  │ - Pattern │ │
│  │ - Cost calc      │  │ - Forecasting    │  │   analysis│ │
│  │ - Aggregation    │  │ - Alert thres.   │  │ - Opport. │ │
│  │ - Trends         │  │ - Burn rate      │  │   scoring │ │
│  └──────────────────┘  └──────────────────┘  └───────────┘ │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────┐ │
│  │ Recommendation   │  │   Forecasting    │  │   Cost    │ │
│  │     Engine       │  │     Engine       │  │  Anomaly  │ │
│  │                  │  │                  │  │  Detector │ │
│  │ - Model routing  │  │ - Time series    │  │           │ │
│  │ - Tier analysis  │  │ - Trend proj.    │  │ - Unusual │ │
│  │ - Quality score  │  │ - Seasonal adj.  │  │   spending│ │
│  │ - ROI calc       │  │ - Confidence     │  │ - Spike   │ │
│  └──────────────────┘  └──────────────────┘  └───────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐      ┌─────────────┐
│   Database   │    │  Smart Alerts│      │  Analytics  │
│              │    │              │      │   Engine    │
│ - Cost data  │    │ - Budget     │      │             │
│ - Budgets    │    │   alerts     │      │ - Usage API │
│ - Forecasts  │    │ - Cost       │      │ - Metrics   │
│ - Recommend. │    │   anomalies  │      │             │
└──────────────┘    └──────────────┘      └─────────────┘
```

### Data Flow

1. **Collection**: Usage data aggregated from analytics tables
2. **Analysis**: Cost calculation with provider pricing
3. **Detection**: Identify anomalies and opportunities
4. **Forecasting**: Predict future spend and budget exhaustion
5. **Recommendation**: Generate optimization suggestions
6. **Action**: Present insights via API/dashboard
7. **Feedback**: Track recommendation adoption and results

---

## 🗄️ Database Schema

### New Tables

#### 1. `cost_analysis`
Stores aggregated cost data for analysis.

```sql
CREATE TABLE cost_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Time period
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    period_type VARCHAR(20) NOT NULL, -- hourly, daily, weekly, monthly
    
    -- Model information
    model_name VARCHAR(255) NOT NULL,
    provider VARCHAR(100) NOT NULL, -- openai, anthropic, google, etc.
    
    -- Usage metrics
    total_requests INTEGER NOT NULL DEFAULT 0,
    total_tokens BIGINT NOT NULL DEFAULT 0,
    input_tokens BIGINT NOT NULL DEFAULT 0,
    output_tokens BIGINT NOT NULL DEFAULT 0,
    
    -- Cost breakdown (in USD)
    total_cost DECIMAL(12, 6) NOT NULL DEFAULT 0,
    input_cost DECIMAL(12, 6) NOT NULL DEFAULT 0,
    output_cost DECIMAL(12, 6) NOT NULL DEFAULT 0,
    
    -- Performance metrics
    avg_latency_ms INTEGER,
    error_count INTEGER DEFAULT 0,
    error_rate DECIMAL(5, 4), -- 0.0000 to 1.0000
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(organization_id, user_id, period_start, period_type, model_name)
);

CREATE INDEX idx_cost_analysis_org_period ON cost_analysis(organization_id, period_start DESC);
CREATE INDEX idx_cost_analysis_user_period ON cost_analysis(user_id, period_start DESC);
CREATE INDEX idx_cost_analysis_model ON cost_analysis(model_name, period_start DESC);
CREATE INDEX idx_cost_analysis_period_type ON cost_analysis(period_type, period_start DESC);
```

#### 2. `budgets`
Budget limits and tracking.

```sql
CREATE TABLE budgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Budget configuration
    name VARCHAR(255) NOT NULL,
    description TEXT,
    budget_type VARCHAR(50) NOT NULL, -- monthly, quarterly, annual, custom
    
    -- Amount limits (in USD)
    total_limit DECIMAL(12, 2) NOT NULL,
    warning_threshold DECIMAL(5, 4) NOT NULL DEFAULT 0.8, -- 80%
    critical_threshold DECIMAL(5, 4) NOT NULL DEFAULT 0.95, -- 95%
    
    -- Period
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    
    -- Current tracking
    current_spend DECIMAL(12, 6) NOT NULL DEFAULT 0,
    last_calculated_at TIMESTAMP,
    
    -- Alerts
    alert_enabled BOOLEAN DEFAULT true,
    alert_contacts JSONB, -- {emails: [], slack_channels: []}
    last_alert_sent TIMESTAMP,
    alert_level VARCHAR(20), -- none, warning, critical, exceeded
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT budgets_threshold_check CHECK (
        warning_threshold < critical_threshold 
        AND critical_threshold <= 1.0
    )
);

CREATE INDEX idx_budgets_org_active ON budgets(organization_id, is_active);
CREATE INDEX idx_budgets_dates ON budgets(start_date, end_date);
CREATE INDEX idx_budgets_alert_level ON budgets(alert_level) WHERE alert_enabled = true;
```

#### 3. `cost_forecasts`
Predictive cost forecasting.

```sql
CREATE TABLE cost_forecasts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    budget_id UUID REFERENCES budgets(id) ON DELETE CASCADE,
    
    -- Forecast period
    forecast_date DATE NOT NULL,
    forecast_horizon_days INTEGER NOT NULL, -- 7, 14, 30, 90
    
    -- Predictions
    predicted_cost DECIMAL(12, 6) NOT NULL,
    confidence_lower DECIMAL(12, 6) NOT NULL,
    confidence_upper DECIMAL(12, 6) NOT NULL,
    confidence_level DECIMAL(3, 2) DEFAULT 0.95, -- 95%
    
    -- Model information
    forecast_model VARCHAR(100) NOT NULL, -- linear, arima, prophet, ml
    model_accuracy DECIMAL(5, 4), -- R² score or MAPE
    
    -- Context
    historical_days_used INTEGER,
    seasonality_detected BOOLEAN DEFAULT false,
    trend_direction VARCHAR(20), -- increasing, decreasing, stable
    trend_strength DECIMAL(5, 4), -- 0.0 to 1.0
    
    -- Budget exhaustion prediction
    budget_exhaustion_date DATE,
    days_until_exhaustion INTEGER,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(organization_id, budget_id, forecast_date, forecast_horizon_days)
);

CREATE INDEX idx_forecasts_org_date ON cost_forecasts(organization_id, forecast_date DESC);
CREATE INDEX idx_forecasts_budget ON cost_forecasts(budget_id, forecast_date DESC);
CREATE INDEX idx_forecasts_exhaustion ON cost_forecasts(budget_exhaustion_date) 
    WHERE budget_exhaustion_date IS NOT NULL;
```

#### 4. `cost_recommendations`
Optimization recommendations.

```sql
CREATE TABLE cost_recommendations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Recommendation details
    recommendation_type VARCHAR(100) NOT NULL, 
    -- model_downgrade, caching, batch_processing, prompt_optimization, 
    -- tier_migration, rate_limiting, unused_features
    
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    
    -- Impact analysis
    current_monthly_cost DECIMAL(12, 6) NOT NULL,
    projected_monthly_cost DECIMAL(12, 6) NOT NULL,
    estimated_savings DECIMAL(12, 6) NOT NULL,
    savings_percentage DECIMAL(5, 2) NOT NULL,
    
    -- Priority scoring
    priority_score INTEGER NOT NULL, -- 0-100
    confidence_score DECIMAL(5, 4) NOT NULL, -- 0.0 to 1.0
    implementation_difficulty VARCHAR(20), -- easy, medium, hard
    
    -- Quality impact
    quality_impact VARCHAR(20), -- none, low, medium, high
    quality_score_change DECIMAL(5, 4), -- -1.0 to 1.0
    
    -- Recommendation details
    recommended_action JSONB NOT NULL,
    -- {
    --   "action": "switch_model",
    --   "from_model": "gpt-4",
    --   "to_model": "gpt-3.5-turbo",
    --   "use_cases": ["simple_queries", "summarization"],
    --   "keep_for": ["complex_reasoning", "code_generation"]
    -- }
    
    -- Supporting data
    analysis_data JSONB,
    -- {
    --   "usage_pattern": {...},
    --   "cost_breakdown": {...},
    --   "quality_metrics": {...}
    -- }
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'pending', 
    -- pending, accepted, rejected, implemented, archived
    
    implemented_at TIMESTAMP,
    implemented_by UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Results tracking
    actual_savings DECIMAL(12, 6),
    results_verified_at TIMESTAMP,
    
    -- Metadata
    valid_until TIMESTAMP, -- Recommendation expiry
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_recommendations_org_status ON cost_recommendations(organization_id, status);
CREATE INDEX idx_recommendations_priority ON cost_recommendations(priority_score DESC);
CREATE INDEX idx_recommendations_savings ON cost_recommendations(estimated_savings DESC);
CREATE INDEX idx_recommendations_type ON cost_recommendations(recommendation_type);
CREATE INDEX idx_recommendations_valid ON cost_recommendations(valid_until) 
    WHERE status = 'pending';
```

#### 5. `model_pricing`
Current LLM provider pricing data.

```sql
CREATE TABLE model_pricing (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Model identification
    provider VARCHAR(100) NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    model_tier VARCHAR(50), -- base, advanced, premium
    
    -- Pricing (per 1M tokens, in USD)
    input_price_per_million DECIMAL(10, 6) NOT NULL,
    output_price_per_million DECIMAL(10, 6) NOT NULL,
    
    -- Context and capabilities
    context_window INTEGER,
    max_output_tokens INTEGER,
    supports_streaming BOOLEAN DEFAULT true,
    supports_function_calling BOOLEAN DEFAULT false,
    
    -- Performance benchmarks
    avg_latency_ms INTEGER,
    quality_score DECIMAL(5, 4), -- 0.0 to 1.0 (from benchmarks)
    
    -- Availability
    is_active BOOLEAN DEFAULT true,
    deprecated_at TIMESTAMP,
    replacement_model VARCHAR(255),
    
    -- Metadata
    effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(provider, model_name, effective_date)
);

CREATE INDEX idx_pricing_provider_model ON model_pricing(provider, model_name);
CREATE INDEX idx_pricing_active ON model_pricing(is_active, effective_date DESC);
CREATE INDEX idx_pricing_tier ON model_pricing(model_tier);
```

#### 6. `savings_opportunities`
Detected cost optimization opportunities.

```sql
CREATE TABLE savings_opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Opportunity details
    opportunity_type VARCHAR(100) NOT NULL,
    -- expensive_model_overuse, low_cache_hit_rate, high_error_rate,
    -- unused_features, off_peak_usage_potential, duplicate_requests
    
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    
    -- Affected resources
    affected_models JSONB, -- ["gpt-4", "claude-3-opus"]
    affected_users JSONB, -- [user_ids]
    affected_period JSONB, -- {"start": "2026-01-01", "end": "2026-01-31"}
    
    -- Cost impact
    current_monthly_cost DECIMAL(12, 6) NOT NULL,
    potential_savings DECIMAL(12, 6) NOT NULL,
    savings_percentage DECIMAL(5, 2) NOT NULL,
    
    -- Detection metadata
    detection_confidence DECIMAL(5, 4) NOT NULL,
    detection_method VARCHAR(100), -- pattern_analysis, ml_detection, rule_based
    supporting_data JSONB,
    
    -- Recommendations
    recommended_actions TEXT[],
    estimated_implementation_hours DECIMAL(5, 2),
    
    -- Status
    status VARCHAR(50) DEFAULT 'open',
    -- open, investigating, planned, implemented, dismissed, expired
    
    assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
    resolved_at TIMESTAMP,
    resolution_notes TEXT,
    
    -- Verification
    verified BOOLEAN DEFAULT false,
    actual_savings DECIMAL(12, 6),
    verified_at TIMESTAMP,
    verified_by UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Metadata
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_opportunities_org_status ON savings_opportunities(organization_id, status);
CREATE INDEX idx_opportunities_savings ON savings_opportunities(potential_savings DESC);
CREATE INDEX idx_opportunities_type ON savings_opportunities(opportunity_type);
CREATE INDEX idx_opportunities_assigned ON savings_opportunities(assigned_to) 
    WHERE status IN ('open', 'investigating', 'planned');
```

### Enhanced Tables

Extend existing `api_usage_logs` table with cost tracking:

```sql
-- Add cost columns to api_usage_logs (if not exists)
ALTER TABLE api_usage_logs 
ADD COLUMN IF NOT EXISTS input_cost DECIMAL(12, 8),
ADD COLUMN IF NOT EXISTS output_cost DECIMAL(12, 8),
ADD COLUMN IF NOT EXISTS total_cost DECIMAL(12, 8);

CREATE INDEX IF NOT EXISTS idx_api_usage_cost ON api_usage_logs(organization_id, total_cost);
CREATE INDEX IF NOT EXISTS idx_api_usage_model_cost ON api_usage_logs(model, total_cost);
```

---

## 🔧 Core Components

### 1. Cost Analysis Engine

**File**: `backend/cost_analysis_engine.py`

```python
class CostAnalysisEngine:
    """
    Analyzes LLM usage and calculates costs across different dimensions.
    """
    
    async def calculate_costs(
        self,
        organization_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> CostAnalysis
    
    async def aggregate_by_model(
        self,
        organization_id: UUID,
        period: str = "daily"
    ) -> List[ModelCostBreakdown]
    
    async def aggregate_by_user(
        self,
        organization_id: UUID,
        period: str = "daily"
    ) -> List[UserCostBreakdown]
    
    async def get_cost_trends(
        self,
        organization_id: UUID,
        metric: str = "total_cost",
        days: int = 30
    ) -> TrendAnalysis
    
    async def detect_cost_anomalies(
        self,
        organization_id: UUID
    ) -> List[CostAnomaly]
```

**Key Features**:
- Real-time cost calculation using current pricing
- Multi-dimensional aggregation (time, model, user, org)
- Trend analysis with statistical methods
- Cost anomaly detection using Epic 13's anomaly detector
- Caching for performance (15-minute TTL)

### 2. Budget Management Service

**File**: `backend/budget_manager.py`

```python
class BudgetManager:
    """
    Manages budgets, tracking, and alerts.
    """
    
    async def create_budget(
        self,
        organization_id: UUID,
        budget_config: BudgetConfig
    ) -> Budget
    
    async def update_budget_spend(
        self,
        budget_id: UUID,
        additional_cost: Decimal
    ) -> Budget
    
    async def check_budget_status(
        self,
        budget_id: UUID
    ) -> BudgetStatus
    
    async def get_budget_utilization(
        self,
        organization_id: UUID
    ) -> List[BudgetUtilization]
    
    async def trigger_budget_alerts(
        self,
        budget_id: UUID
    ) -> Optional[Alert]
```

**Key Features**:
- Flexible budget periods (monthly, quarterly, annual, custom)
- Multi-tier alerting (warning, critical, exceeded)
- Automatic spend tracking
- Integration with Smart Alerts for notifications
- Budget rollover and renewal

### 3. Forecasting Engine

**File**: `backend/cost_forecasting_engine.py`

```python
class CostForecastingEngine:
    """
    Predicts future costs using time series analysis.
    """
    
    async def forecast_cost(
        self,
        organization_id: UUID,
        horizon_days: int = 30
    ) -> CostForecast
    
    async def predict_budget_exhaustion(
        self,
        budget_id: UUID
    ) -> BudgetExhaustionPrediction
    
    async def analyze_seasonality(
        self,
        organization_id: UUID
    ) -> SeasonalityAnalysis
    
    async def calculate_burn_rate(
        self,
        organization_id: UUID
    ) -> BurnRate
```

**Algorithms**:
- Linear regression for stable trends
- Exponential smoothing for volatile data
- Seasonal decomposition (STL)
- ARIMA for complex patterns (optional)
- Confidence intervals (95%)

### 4. Recommendation Engine

**File**: `backend/cost_recommendation_engine.py`

```python
class CostRecommendationEngine:
    """
    Generates cost optimization recommendations.
    """
    
    async def generate_recommendations(
        self,
        organization_id: UUID
    ) -> List[CostRecommendation]
    
    async def analyze_model_usage(
        self,
        organization_id: UUID
    ) -> ModelUsageAnalysis
    
    async def suggest_model_alternatives(
        self,
        current_model: str,
        use_case: str
    ) -> List[ModelAlternative]
    
    async def calculate_roi(
        self,
        recommendation_id: UUID
    ) -> ROIAnalysis
    
    async def track_recommendation_results(
        self,
        recommendation_id: UUID,
        actual_savings: Decimal
    ) -> None
```

**Recommendation Types**:
1. **Model Downgrade**: Use cheaper models for simple tasks
2. **Caching**: Implement response caching for common queries
3. **Batch Processing**: Batch similar requests
4. **Prompt Optimization**: Reduce token usage
5. **Tier Migration**: Switch to more cost-effective tier
6. **Rate Limiting**: Prevent runaway costs
7. **Unused Features**: Disable unused expensive features

### 5. Savings Detector

**File**: `backend/savings_detector.py`

```python
class SavingsDetector:
    """
    Identifies cost savings opportunities.
    """
    
    async def detect_opportunities(
        self,
        organization_id: UUID
    ) -> List[SavingsOpportunity]
    
    async def analyze_model_overuse(
        self,
        organization_id: UUID
    ) -> List[ModelOveruseOpportunity]
    
    async def detect_inefficient_patterns(
        self,
        organization_id: UUID
    ) -> List[PatternOpportunity]
    
    async def calculate_potential_savings(
        self,
        opportunity_id: UUID
    ) -> SavingsCalculation
```

**Detection Strategies**:
- Expensive model overuse (GPT-4 for simple tasks)
- Low cache hit rates
- High error rates (wasted API calls)
- Duplicate requests
- Off-peak usage potential
- Over-provisioned features

---

## 🔌 API Endpoints

### Cost Analysis Endpoints

```
GET    /api/v1/costs/analysis
       - Get cost analysis for period
       Query params: start_date, end_date, group_by
       
GET    /api/v1/costs/breakdown
       - Cost breakdown by dimension
       Query params: dimension (model, user, org), period
       
GET    /api/v1/costs/trends
       - Cost trends over time
       Query params: metric, days, granularity
       
GET    /api/v1/costs/anomalies
       - Detected cost anomalies
       Query params: severity, start_date
```

### Budget Management Endpoints

```
POST   /api/v1/budgets
       - Create new budget
       Body: {name, total_limit, budget_type, start_date, end_date}
       
GET    /api/v1/budgets
       - List budgets
       Query params: is_active, budget_type
       
GET    /api/v1/budgets/{budget_id}
       - Get budget details
       
PATCH  /api/v1/budgets/{budget_id}
       - Update budget
       
DELETE /api/v1/budgets/{budget_id}
       - Delete budget
       
GET    /api/v1/budgets/{budget_id}/status
       - Get budget utilization status
       
GET    /api/v1/budgets/{budget_id}/history
       - Get budget spend history
```

### Forecasting Endpoints

```
POST   /api/v1/costs/forecast
       - Generate cost forecast
       Body: {horizon_days, include_confidence}
       
GET    /api/v1/costs/forecast/{forecast_id}
       - Get forecast details
       
GET    /api/v1/budgets/{budget_id}/exhaustion
       - Predict budget exhaustion
       
GET    /api/v1/costs/burn-rate
       - Get current burn rate
```

### Recommendation Endpoints

```
GET    /api/v1/recommendations
       - List recommendations
       Query params: status, type, min_savings
       
GET    /api/v1/recommendations/{recommendation_id}
       - Get recommendation details
       
POST   /api/v1/recommendations/{recommendation_id}/accept
       - Accept recommendation
       
POST   /api/v1/recommendations/{recommendation_id}/reject
       - Reject recommendation
       Body: {reason}
       
POST   /api/v1/recommendations/{recommendation_id}/implement
       - Mark as implemented
       
POST   /api/v1/recommendations/{recommendation_id}/verify
       - Verify actual savings
       Body: {actual_savings}
       
GET    /api/v1/recommendations/model-alternatives
       - Get alternative models
       Query params: current_model, use_case
```

### Savings Opportunities Endpoints

```
GET    /api/v1/opportunities
       - List savings opportunities
       Query params: status, type, min_savings
       
GET    /api/v1/opportunities/{opportunity_id}
       - Get opportunity details
       
PATCH  /api/v1/opportunities/{opportunity_id}
       - Update opportunity status
       Body: {status, assigned_to, resolution_notes}
       
POST   /api/v1/opportunities/{opportunity_id}/verify
       - Verify actual savings
       Body: {actual_savings}
       
GET    /api/v1/opportunities/summary
       - Get opportunities summary
```

### Model Pricing Endpoints

```
GET    /api/v1/pricing/models
       - List model pricing
       Query params: provider, is_active
       
POST   /api/v1/pricing/models
       - Add/update model pricing (admin only)
       Body: {provider, model_name, input_price, output_price}
       
GET    /api/v1/pricing/compare
       - Compare model costs
       Query params: models[], usage_profile
```

---

## 📊 Dashboard Features

### 1. Cost Overview Dashboard

**Components**:
- Total spend (MTD, QTD, YTD)
- Spend by model (pie chart)
- Spend by user/team (bar chart)
- Cost trend graph (30-day)
- Budget utilization meters
- Top cost drivers

### 2. Budget Management Dashboard

**Components**:
- Active budgets list
- Budget health indicators
- Forecast vs. actual comparison
- Days remaining in budget
- Alert history
- Budget exhaustion predictions

### 3. Recommendations Dashboard

**Components**:
- Active recommendations (sorted by savings)
- Recommendation priority scores
- Implementation status
- Verified savings tracker
- ROI calculator
- Quick-action buttons

### 4. Savings Opportunities Dashboard

**Components**:
- Open opportunities list
- Opportunity type breakdown
- Total potential savings
- Implementation pipeline
- Success metrics
- Opportunity trends

### 5. Model Cost Comparison

**Components**:
- Side-by-side model comparison
- Cost per 1M tokens
- Quality vs. cost scatter plot
- Use case recommendations
- Migration calculator
- Provider comparison

---

## 🔄 Background Tasks

### 1. Cost Aggregation Task
- **Frequency**: Hourly
- **Function**: Aggregate usage into cost_analysis table
- **Process**:
  1. Query api_usage_logs for last hour
  2. Calculate costs using model_pricing
  3. Group by org, user, model
  4. Insert into cost_analysis
  5. Update budget current_spend

### 2. Budget Monitoring Task
- **Frequency**: Every 15 minutes
- **Function**: Check budget thresholds and trigger alerts
- **Process**:
  1. Calculate current spend for active budgets
  2. Check against warning/critical thresholds
  3. Trigger Smart Alerts if thresholds crossed
  4. Update budget alert_level
  5. Log alert history

### 3. Forecasting Task
- **Frequency**: Daily (2am)
- **Function**: Generate cost forecasts
- **Process**:
  1. Collect historical data (30-90 days)
  2. Run forecasting models
  3. Generate 7-day, 30-day, 90-day forecasts
  4. Calculate budget exhaustion dates
  5. Store in cost_forecasts table

### 4. Recommendation Generation Task
- **Frequency**: Weekly (Sunday 3am)
- **Function**: Generate new recommendations
- **Process**:
  1. Analyze usage patterns
  2. Identify optimization opportunities
  3. Calculate potential savings
  4. Score and prioritize recommendations
  5. Expire old recommendations
  6. Store in cost_recommendations table

### 5. Savings Detection Task
- **Frequency**: Daily (3am)
- **Function**: Detect savings opportunities
- **Process**:
  1. Run pattern analysis
  2. Detect anomalies and inefficiencies
  3. Calculate potential savings
  4. Create opportunity records
  5. Assign priorities

### 6. Cleanup Task
- **Frequency**: Daily (4am)
- **Function**: Archive old data
- **Process**:
  1. Archive forecasts older than 90 days
  2. Archive implemented recommendations older than 180 days
  3. Archive resolved opportunities older than 180 days
  4. Keep cost_analysis data for 2 years
  5. Update aggregation statistics

---

## 🧮 Cost Calculation Logic

### Model Pricing (as of Jan 2026)

```python
DEFAULT_PRICING = {
    "openai": {
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},  # per 1M tokens
        "gpt-4": {"input": 30.00, "output": 60.00},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        "gpt-3.5-turbo-16k": {"input": 3.00, "output": 4.00},
    },
    "anthropic": {
        "claude-3-opus": {"input": 15.00, "output": 75.00},
        "claude-3-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
    },
    "google": {
        "gemini-pro": {"input": 0.50, "output": 1.50},
        "gemini-ultra": {"input": 10.00, "output": 30.00},
    }
}
```

### Cost Formula

```python
def calculate_cost(input_tokens: int, output_tokens: int, pricing: dict) -> Decimal:
    """
    Calculate cost for a single API call.
    """
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return Decimal(input_cost + output_cost).quantize(Decimal('0.000001'))
```

### Savings Calculation

```python
def calculate_savings(
    current_usage: UsageMetrics,
    alternative_model: str
) -> SavingsEstimate:
    """
    Calculate potential savings from switching models.
    """
    current_cost = calculate_cost(
        current_usage.input_tokens,
        current_usage.output_tokens,
        PRICING[current_usage.model]
    )
    
    alternative_cost = calculate_cost(
        current_usage.input_tokens,
        current_usage.output_tokens,
        PRICING[alternative_model]
    )
    
    monthly_savings = (current_cost - alternative_cost) * current_usage.requests_per_month
    savings_percentage = ((current_cost - alternative_cost) / current_cost) * 100
    
    return SavingsEstimate(
        monthly_savings=monthly_savings,
        savings_percentage=savings_percentage,
        payback_period_days=0  # No upfront cost for model switch
    )
```

---

## 🎨 User Experience

### Recommendation Flow

1. **Discovery**: User sees "💡 You have 5 new recommendations" notification
2. **Review**: Click to see recommendations dashboard
3. **Details**: Click recommendation to see:
   - Current state analysis
   - Proposed change
   - Estimated savings
   - Quality impact assessment
   - Implementation steps
4. **Decision**: Accept, Reject, or Request More Info
5. **Implementation**: If accepted, follow guided steps
6. **Verification**: After implementation, verify actual savings

### Budget Alert Flow

1. **Warning Alert** (80% threshold):
   - Email + dashboard notification
   - "Budget ABC is at 82% utilization"
   - Shows current spend, forecast, days remaining
   - Suggests reviewing high-cost activities

2. **Critical Alert** (95% threshold):
   - Email + dashboard notification + Slack (if configured)
   - "Budget ABC is at 97% utilization"
   - Shows exhaustion prediction
   - Suggests immediate cost reduction measures
   - Links to recommendations

3. **Exceeded Alert** (100%+):
   - Urgent email + dashboard + Slack
   - "Budget ABC has been exceeded"
   - Shows overage amount
   - Links to emergency cost reduction guide
   - Option to request budget increase

---

## 🔒 Security & Permissions

### Role-Based Access

| Feature | User | Org Admin | Platform Admin |
|---------|------|-----------|----------------|
| View own costs | ✅ | ✅ | ✅ |
| View org costs | ❌ | ✅ | ✅ |
| View all org costs | ❌ | ❌ | ✅ |
| Create budgets | ❌ | ✅ | ✅ |
| Modify budgets | ❌ | ✅ | ✅ |
| View recommendations | ✅ | ✅ | ✅ |
| Accept recommendations | ❌ | ✅ | ✅ |
| Update pricing | ❌ | ❌ | ✅ |
| View savings opportunities | ✅ | ✅ | ✅ |
| Assign opportunities | ❌ | ✅ | ✅ |

### Data Privacy

- Users can only see their own detailed usage
- Org admins see aggregated org data (no individual user details without permission)
- Platform admins see all data (audit logged)
- Cost data encrypted at rest
- API endpoints require authentication
- Budget alerts respect notification preferences

---

## 📈 Performance Requirements

### Response Times
- Cost dashboard load: <2 seconds
- API queries: <500ms (p95)
- Forecast generation: <3 seconds
- Recommendation generation: <5 seconds (background ok)

### Data Volumes
- Support 1M+ API calls per day
- Store 2 years of cost history
- Generate forecasts for 10,000+ organizations
- Process 100+ budgets per organization

### Caching Strategy
- Cost analysis: 15-minute TTL
- Model pricing: 1-hour TTL
- Forecasts: 24-hour TTL
- Recommendations: 1-week TTL

---

## 🧪 Testing Strategy

### Unit Tests
- Cost calculation accuracy
- Forecast algorithm correctness
- Recommendation scoring logic
- Savings calculation formulas
- Budget threshold detection

### Integration Tests
- End-to-end cost tracking
- Budget alert triggering
- Recommendation generation pipeline
- API endpoint functionality
- Database integrity

### Performance Tests
- Cost aggregation at scale
- Dashboard load time with large datasets
- Forecast generation speed
- Concurrent budget checks

### Validation Tests
- Pricing accuracy verification
- Forecast accuracy measurement
- Recommendation success rate
- Savings verification

---

## 📋 Implementation Checklist

### Phase 1: Foundation (Week 1)
- [ ] Create database migration
- [ ] Implement model_pricing table population
- [ ] Build Cost Analysis Engine
- [ ] Create basic API endpoints
- [ ] Add cost columns to api_usage_logs

### Phase 2: Budget Management (Week 2)
- [ ] Implement Budget Manager
- [ ] Create budget CRUD endpoints
- [ ] Build budget monitoring task
- [ ] Integrate with Smart Alerts
- [ ] Create budget dashboard

### Phase 3: Forecasting (Week 3)
- [ ] Build Forecasting Engine
- [ ] Implement time series algorithms
- [ ] Create forecast endpoints
- [ ] Build forecasting task
- [ ] Add forecast visualizations

### Phase 4: Recommendations (Week 4)
- [ ] Implement Recommendation Engine
- [ ] Build savings detector
- [ ] Create recommendation endpoints
- [ ] Build recommendation generation task
- [ ] Create recommendations dashboard

### Phase 5: Integration & Polish (Week 5)
- [ ] Complete all background tasks
- [ ] Build comprehensive dashboard
- [ ] Write documentation
- [ ] Performance optimization
- [ ] Testing and QA

---

## 🎯 Success Criteria

### Functional Requirements
- ✅ Accurate cost tracking (±1% of actual)
- ✅ Real-time budget monitoring
- ✅ 7-day forecast accuracy >85%
- ✅ Generate 10+ recommendations per org/month
- ✅ Detect 5+ savings opportunities per org/month

### Performance Requirements
- ✅ Dashboard loads in <2 seconds
- ✅ Cost calculations updated hourly
- ✅ Budget alerts within 15 minutes
- ✅ Support 10,000+ active budgets

### Business Requirements
- ✅ Enable 30-50% cost reduction
- ✅ 90% user adoption of recommendations
- ✅ Zero budget surprises
- ✅ ROI positive within 1 month

---

## 📚 Documentation Deliverables

1. **API Documentation**: OpenAPI spec for all endpoints
2. **User Guide**: Dashboard usage and best practices
3. **Admin Guide**: Budget setup and management
4. **Cost Optimization Playbook**: Step-by-step optimization strategies
5. **Pricing Guide**: Model pricing and calculation methods
6. **Integration Guide**: Connecting cost data to external systems

---

## 🔮 Future Enhancements (Post-v1)

### Phase 2 Features
- Multi-cloud cost optimization (AWS, GCP, Azure)
- Infrastructure cost tracking (compute, storage)
- Automated model switching (with approval workflow)
- Custom pricing contracts
- Real-time budget enforcement
- Cost allocation tags

### Advanced Features
- ML-based anomaly detection for costs
- Predictive cost modeling with ML
- What-if scenario analysis
- Cost optimization advisor chatbot
- Integration with finance systems
- Chargeback/showback reporting

---

## 📞 Support & Resources

- **Documentation**: `/docs/cost-optimization/`
- **API Reference**: `/api/docs#cost-optimization`
- **Slack Channel**: `#cost-optimization`
- **Support Email**: `cost-support@ops-center.dev`

---

*Last Updated: January 26, 2026*
*Epic Owner: Development Team*
*Status: 🚧 In Progress*
