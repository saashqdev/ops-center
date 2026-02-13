# LiteLLM Monitoring Setup - Quick Reference

## Overview
Complete monitoring infrastructure for LiteLLM multi-provider gateway using Prometheus, Grafana, and AlertManager.

## ✅ Completed Setup

### 1. Monitoring Stack Deployment
```bash
# Services Deployed on:
- Prometheus:        http://localhost:9090
- Grafana:           http://localhost:3001  (user: admin, pass: admin)
- AlertManager:      http://localhost:9093
- Node Exporter:     http://localhost:9100
- Postgres Exporter: http://localhost:9187
- Redis Exporter:    http://localhost:9121
- Docker Exporter:   http://localhost:9417
```

### 2. Grafana Dashboard
**Location:** `/config/grafana/dashboards/litellm_dashboard.json`

**Panels:**
- LiteLLM Status (UP/DOWN indicator)
- Request Rate (total requests vs errors)
- P95 Latency (5-minute window)
- Requests by Model (stacked bar chart)
- Requests by Provider (time series)
- Total Tokens Used (cumulative counter)
- Total Cost USD (cumulative cost)
- Error Rate (percentage)

**Access:**
```bash
# Local access (port 3001 to avoid conflict with Lago)
http://localhost:3001

# Via Traefik (production)
https://grafana.kubeworkz.io
```

**Default Credentials:**
- Username: `admin`
- Password: `admin` (change on first login)

### 3. Prometheus Configuration
**Location:** `/config/prometheus/prometheus.yml`

**LiteLLM Scrape Jobs:**
```yaml
# LiteLLM proxy metrics (native Prometheus export)
- job_name: 'litellm'
  scrape_interval: 10s
  static_configs:
    - targets: ['unicorn-litellm-wilmer:4000']
  metrics_path: /metrics

# LiteLLM usage metrics (custom backend endpoint)
- job_name: 'litellm-usage'
  scrape_interval: 30s
  static_configs:
    - targets: ['ops-center-direct:8084']
  metrics_path: /api/v1/llm/metrics
```

### 4. Alert Rules
**Location:** `/config/prometheus/rules/litellm_alerts.yml`

**Alert Groups (6 groups, 15 alerts):**

#### A. Availability Alerts
- **LiteLLMDown** (critical): Proxy down for 2+ minutes
- **LiteLLMUnhealthy** (warning): Health check fails for 5+ minutes

#### B. Performance Alerts
- **LiteLLMHighLatency** (warning): P95 latency > 10s for 10 minutes
- **LiteLLMHighErrorRate** (warning): Error rate > 5% for 5 minutes
- **LiteLLMCriticalErrorRate** (critical): Error rate > 20% for 2 minutes

#### C. Usage Alerts
- **LiteLLMHighRequestRate** (warning): > 100 req/s for 10 minutes (abuse detection)
- **LiteLLMTokenLimitApproaching** (info): > 1M tokens used in 1 hour
- **LiteLLMModelFailures** (warning): Model error rate > 10% for 5 minutes

#### D. Cost Alerts
- **LiteLLMHighDailyCost** (warning): Daily cost > $100
- **LiteLLMCostSpike** (warning): Cost increases 2x vs previous hour for 15 minutes

#### E. Database Alerts
- **LiteLLMDatabasePoolExhausted** (critical): All DB connections active for 5 minutes
- **LiteLLMSlowDatabaseQueries** (warning): P95 query time > 1s for 10 minutes

#### F. Provider Alerts
- **LiteLLMGroqProviderDown** (critical): Groq failure rate > 90% for 5 minutes
- **LiteLLMProviderRateLimited** (warning): > 10 rate limit errors in 5 minutes

### 5. Monitoring Script
**Location:** `/scripts/monitor_litellm.sh`

**Features:**
- Container status check
- Health endpoint validation
- Model availability verification
- Database connectivity test
- Performance metrics (CPU, memory, network)
- Live inference test
- Active alerts summary

**Usage:**
```bash
# Run once
./scripts/monitor_litellm.sh

# Run continuously (every 30s)
watch -n 30 ./scripts/monitor_litellm.sh
```

## 📊 Key Metrics

### LiteLLM Native Metrics (expected but NOT YET AVAILABLE)
```
# Request metrics
litellm_requests_total                    # Total requests counter
litellm_request_errors_total              # Total errors counter
litellm_request_duration_seconds          # Latency histogram

# Model metrics
litellm_model_requests_total{model="..."}  # Requests per model
litellm_model_errors_total{model="..."}    # Errors per model

# Token metrics
litellm_tokens_used_total                 # Total tokens consumed
litellm_prompt_tokens_total               # Prompt tokens
litellm_completion_tokens_total           # Completion tokens

# Cost metrics
litellm_total_cost_usd                    # Total cost in USD

# Provider metrics
litellm_provider_requests_total{provider="groq"}  # Requests per provider
litellm_provider_errors_total{provider="groq"}    # Errors per provider
```

### Backend Custom Metrics (TO BE IMPLEMENTED)
```
# Usage analytics from database
llm_credits_used_total{tenant_id="..."}   # Credits consumed per tenant
llm_requests_by_model{model="..."}        # Historical request counts
llm_cost_by_tenant{tenant_id="..."}       # Cost tracking per tenant
llm_response_time_seconds{model="..."}    # Response time histograms
```

## 🚨 Monitoring Stack Management

### Start Monitoring
```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

### Stop Monitoring
```bash
docker-compose -f docker-compose.monitoring.yml down
```

### View Logs
```bash
# Prometheus
docker logs ops-center-prometheus -f

# Grafana
docker logs ops-center-grafana -f

# AlertManager
docker logs ops-center-alertmanager -f
```

### Restart Services
```bash
# Restart all monitoring
docker-compose -f docker-compose.monitoring.yml restart

# Restart specific service
docker restart ops-center-prometheus
docker restart ops-center-grafana
```

## 🔧 Configuration Updates

### Reload Prometheus Config (no restart needed)
```bash
curl -X POST http://localhost:9090/-/reload
```

### Add New Alert Rules
1. Edit `/config/prometheus/rules/litellm_alerts.yml`
2. Reload Prometheus:
   ```bash
   curl -X POST http://localhost:9090/-/reload
   ```
3. Verify rules loaded:
   ```bash
   curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[] | .name'
   ```

### Import New Grafana Dashboard
1. Place JSON file in `/config/grafana/dashboards/`
2. Restart Grafana:
   ```bash
   docker restart ops-center-grafana
   ```

## 🎯 Current Status

✅ **Operational:**
- Prometheus scraping 7 exporters
- Grafana dashboard created
- 15 alert rules configured and loaded
- Monitoring script functional
- All monitoring containers running

⚠️ **Pending:**
- **LiteLLM native metrics not exposed** - `/metrics` endpoint returns 404
  * Need to enable Prometheus exporter in LiteLLM config
  * May require setting `LITELLM_ENABLE_PROMETHEUS=true` environment variable
  * Alternative: Use LiteLLM database logging and export metrics from backend

- **Backend metrics endpoint not implemented** - `/api/v1/llm/metrics` doesn't exist
  * Need to create FastAPI route in backend
  * Query litellm_db for usage statistics
  * Export as Prometheus format (counter/gauge/histogram)

- **AlertManager configuration needed** - Currently restarting
  * Need to configure `/config/alertmanager/alertmanager.yml`
  * Set up notification channels (email, Slack, webhook)
  * Define routing rules for alert severity

## 🔍 Troubleshooting

### Check Scrape Targets
```bash
# View all targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health, error: .lastError}'

# View only LiteLLM targets
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job | contains("litellm"))'
```

### Test Metrics Endpoint
```bash
# Test LiteLLM native metrics (currently 404)
curl http://localhost:4000/metrics

# Test backend custom metrics (not implemented)
curl http://localhost:8084/api/v1/llm/metrics
```

### Query Prometheus
```bash
# Check if metrics exist
curl -s 'http://localhost:9090/api/v1/label/__name__/values' | jq '.data[] | select(contains("litellm"))'

# Query specific metric
curl -s 'http://localhost:9090/api/v1/query?query=up{job="litellm"}' | jq .
```

### View Active Alerts
```bash
# All active alerts
curl -s http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | {alert: .labels.alertname, state: .state, value: .value}'

# Only firing alerts
curl -s http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | select(.state=="firing")'
```

## 📝 Next Steps

### Priority 1: Enable LiteLLM Metrics
1. Check LiteLLM documentation for Prometheus export
2. Update environment variables or config to enable metrics
3. Verify `/metrics` endpoint responds with Prometheus format
4. Confirm Prometheus can scrape the endpoint

### Priority 2: Implement Backend Metrics Endpoint
1. Create `/api/v1/llm/metrics` route in backend
2. Query `litellm_db` for:
   - Total requests (from `llm_transactions`)
   - Credits used (from `llm_credits`)
   - Response times (from `llm_transactions`)
   - Error counts (from `llm_transactions` WHERE status='error')
3. Format as Prometheus metrics:
   ```python
   from prometheus_client import generate_latest, Counter, Histogram, Gauge
   
   # Example metrics
   llm_requests = Counter('llm_requests_total', 'Total LLM requests', ['model', 'tenant'])
   llm_credits = Counter('llm_credits_used_total', 'Total credits used', ['tenant'])
   llm_latency = Histogram('llm_response_time_seconds', 'LLM response time', ['model'])
   ```

### Priority 3: Configure AlertManager
1. Create `/config/alertmanager/alertmanager.yml`
2. Configure notification receivers:
   - Email for critical alerts
   - Slack for warnings
   - Webhook for custom integrations
3. Set up routing based on severity and alert group
4. Test alert delivery

### Priority 4: Additional Dashboards
1. Create provider-specific dashboards (Groq, HuggingFace, local)
2. Add cost analysis dashboard
3. Create tenant usage dashboard
4. Build capacity planning dashboard

## 📚 Resources

- Prometheus Docs: https://prometheus.io/docs/
- Grafana Docs: https://grafana.com/docs/
- LiteLLM Docs: https://docs.litellm.ai/
- Prometheus Query Examples: https://prometheus.io/docs/prometheus/latest/querying/examples/

## 🔐 Security Notes

1. **Change Grafana default password immediately**
   ```bash
   # Access http://localhost:3001
   # Login with admin/admin
   # You'll be prompted to change password
   ```

2. **Restrict Prometheus access** - Currently open on port 9090
   - Use Traefik auth middleware in production
   - Or restrict to internal network only

3. **Protect metrics endpoints** - Ensure LiteLLM metrics require authentication
   - Set `LITELLM_MASTER_KEY` requirement for metrics endpoint
   - Use network policies to restrict scraper access

4. **AlertManager webhook security** - Use signed payloads for webhooks
   - Configure HMAC signatures
   - Validate webhook sources

## 📞 Support

For monitoring issues:
1. Check monitoring script output: `./scripts/monitor_litellm.sh`
2. Review Prometheus targets: http://localhost:9090/targets
3. Check container logs: `docker logs ops-center-prometheus`
4. Verify alert rules: http://localhost:9090/rules

---

**Last Updated:** 2026-02-13  
**Version:** 1.0  
**Status:** Monitoring stack deployed, metrics endpoints pending implementation
