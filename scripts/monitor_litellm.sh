#!/bin/bash

# LiteLLM Monitoring Script
# Provides real-time monitoring and health checks for LiteLLM service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# LiteLLM Configuration
LITELLM_HOST=${LITELLM_HOST:-localhost}
LITELLM_PORT=${LITELLM_PORT:-4000}
LITELLM_MASTER_KEY=${LITELLM_MASTER_KEY:-d85bcec2690d3f12779c0690d26d16370e434c0d7422bef5c5105f0a39b36a3a}
LITELLM_URL="http://${LITELLM_HOST}:${LITELLM_PORT}"

# Functions
print_header() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  LiteLLM Monitoring Dashboard${NC}"
    echo -e "${BLUE}  $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

check_container_status() {
    echo -e "${YELLOW}📦 Container Status:${NC}"
    if docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep litellm > /dev/null 2>&1; then
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep litellm | while read line; do
            echo -e "  ${GREEN}✓${NC} $line"
        done
    else
        echo -e "  ${RED}✗ LiteLLM container not running${NC}"
        return 1
    fi
    echo ""
}

check_health() {
    echo -e "${YELLOW}🏥 Health Check:${NC}"
    
    # Check if service is reachable
    if ! curl -s --max-time 5 "${LITELLM_URL}/health" > /dev/null 2>&1; then
        echo -e "  ${RED}✗ Service not reachable${NC}"
        return 1
    fi
    
    # Get health status with auth
    HEALTH=$(curl -s -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" "${LITELLM_URL}/health" 2>/dev/null || echo '{"error": "failed"}')
    
    if echo "$HEALTH" | jq -e '.healthy_endpoints' > /dev/null 2>&1; then
        HEALTHY_COUNT=$(echo "$HEALTH" | jq '.healthy_endpoints | length' 2>/dev/null || echo 0)
        UNHEALTHY_COUNT=$(echo "$HEALTH" | jq '.unhealthy_endpoints | length' 2>/dev/null || echo 0)
        
        echo -e "  ${GREEN}✓ Service is responding${NC}"
        echo -e "  ${GREEN}✓ Healthy endpoints: ${HEALTHY_COUNT}${NC}"
        if [ "$UNHEALTHY_COUNT" -gt 0 ]; then
            echo -e "  ${YELLOW}⚠ Unhealthy endpoints: ${UNHEALTHY_COUNT}${NC}"
        fi
    else
        echo -e "  ${YELLOW}⚠ Health check returned unexpected format${NC}"
    fi
    echo ""
}

check_models() {
    echo -e "${YELLOW}🤖 Available Models:${NC}"
    
    MODELS=$(curl -s -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
        "${LITELLM_URL}/v1/models" 2>/dev/null || echo '{"data":[]}')
    
    MODEL_COUNT=$(echo "$MODELS" | jq '.data | length' 2>/dev/null || echo 0)
    
    if [ "$MODEL_COUNT" -gt 0 ]; then
        echo -e "  ${GREEN}✓ Total models loaded: ${MODEL_COUNT}${NC}"
        echo "$MODELS" | jq -r '.data[] | "    • \(.id)"' 2>/dev/null | head -10
        if [ "$MODEL_COUNT" -gt 10 ]; then
            echo -e "    ${BLUE}... and $((MODEL_COUNT - 10)) more${NC}"
        fi
    else
        echo -e "  ${RED}✗ No models loaded${NC}"
    fi
    echo ""
}

check_logs() {
    echo -e "${YELLOW}📋 Recent Logs (last 10 lines):${NC}"
    if docker logs unicorn-litellm-wilmer --tail 10 2>&1 | grep -E "(ERROR|WARN|error|warning)" > /dev/null; then
        docker logs unicorn-litellm-wilmer --tail 10 2>&1 | grep -E "(ERROR|WARN|error|warning)" | while read line; do
            echo -e "  ${RED}⚠${NC} $line"
        done
    else
        echo -e "  ${GREEN}✓ No errors or warnings in recent logs${NC}"
    fi
    echo ""
}

check_database() {
    echo -e "${YELLOW}💾 Database Status:${NC}"
    
    # Check if database is accessible from LiteLLM container
    if docker exec unicorn-litellm-wilmer env | grep DATABASE_URL > /dev/null 2>&1; then
        DB_URL=$(docker exec unicorn-litellm-wilmer env | grep DATABASE_URL | cut -d= -f2-)
        echo -e "  ${GREEN}✓ Database URL configured${NC}"
        echo -e "    ${BLUE}${DB_URL}${NC}"
    else
        echo -e "  ${RED}✗ Database URL not found${NC}"
    fi
    echo ""
}

check_performance() {
    echo -e "${YELLOW}⚡ Performance Metrics:${NC}"
    
    # Get container stats
    STATS=$(docker stats unicorn-litellm-wilmer --no-stream --format "{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" 2>/dev/null || echo "N/A\tN/A\tN/A")
    
    CPU=$(echo "$STATS" | cut -f1)
    MEM=$(echo "$STATS" | cut -f2)
    NET=$(echo "$STATS" | cut -f3)
    
    echo -e "  CPU Usage:     ${BLUE}${CPU}${NC}"
    echo -e "  Memory Usage:  ${BLUE}${MEM}${NC}"
    echo -e "  Network I/O:   ${BLUE}${NET}${NC}"
    echo ""
}

test_inference() {
    echo -e "${YELLOW}🧪 Inference Test:${NC}"
    
    # Test with a simple prompt
    RESPONSE=$(curl -s -X POST "${LITELLM_URL}/v1/chat/completions" \
        -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
        -H "Content-Type: application/json" \
        -d '{
            "model": "llama-3.3-70b-groq",
            "messages": [{"role": "user", "content": "Say test"}],
            "max_tokens": 5
        }' 2>/dev/null)
    
    if echo "$RESPONSE" | jq -e '.choices[0].message.content' > /dev/null 2>&1; then
        CONTENT=$(echo "$RESPONSE" | jq -r '.choices[0].message.content')
        TOKENS=$(echo "$RESPONSE" | jq -r '.usage.total_tokens')
        LATENCY=$(echo "$RESPONSE" | jq -r '.usage.total_time // 0')
        
        echo -e "  ${GREEN}✓ Inference successful${NC}"
        echo -e "    Response: ${BLUE}${CONTENT}${NC}"
        echo -e "    Tokens: ${BLUE}${TOKENS}${NC}"
        if [ "$LATENCY" != "0" ]; then
            echo -e "    Latency: ${BLUE}${LATENCY}s${NC}"
        fi
    else
        echo -e "  ${RED}✗ Inference test failed${NC}"
        echo "$RESPONSE" | jq -r '.error.message // "Unknown error"' 2>/dev/null | sed 's/^/    /'
    fi
    echo ""
}

show_usage_stats() {
    echo -e "${YELLOW}📊 Usage Statistics (24h):${NC}"
    
    # This would query the backend API for usage stats
    # For now, show a placeholder
    echo -e "  ${BLUE}ℹ${NC}  Detailed usage statistics available in Grafana dashboard"
    echo -e "  ${BLUE}ℹ${NC}  Access at: https://grafana.kubeworkz.io/d/litellm-monitoring"
    echo ""
}

show_alerts() {
    echo -e "${YELLOW}🚨 Active Alerts:${NC}"
    
    # Check for common issues
    ALERTS=0
    
    # Check error rate in logs
    ERROR_COUNT=$(docker logs unicorn-litellm-wilmer --since 5m 2>&1 | grep -c ERROR || echo 0)
    if [ "$ERROR_COUNT" -gt 10 ]; then
        echo -e "  ${RED}⚠ High error rate: ${ERROR_COUNT} errors in last 5 minutes${NC}"
        ALERTS=$((ALERTS + 1))
    fi
    
    # Check memory usage
    MEM_PERCENT=$(docker stats unicorn-litellm-wilmer --no-stream --format "{{.MemPerc}}" 2>/dev/null | tr -d '%' || echo 0)
    if (( $(echo "$MEM_PERCENT > 80" | bc -l 2>/dev/null || echo 0) )); then
        echo -e "  ${YELLOW}⚠ High memory usage: ${MEM_PERCENT}%${NC}"
        ALERTS=$((ALERTS + 1))
    fi
    
    if [ "$ALERTS" -eq 0 ]; then
        echo -e "  ${GREEN}✓ No active alerts${NC}"
    fi
    echo ""
}

# Main execution
print_header
check_container_status
check_health
check_models
check_database
check_performance
test_inference
show_alerts

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Monitoring complete!${NC}"
echo ""
echo -e "For continuous monitoring, consider:"
echo -e "  • Deploying Prometheus + Grafana stack"
echo -e "  • Setting up alerting via AlertManager"
echo -e "  • Enabling detailed logging"
echo ""
echo -e "Run this script with: ${BLUE}./monitor_litellm.sh${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
