#!/bin/bash
# Deployment Verification Script
# Run after every Cloud Run deployment to verify service health
#
# Usage:
#   ./scripts/smoke-test.sh
#   ./scripts/smoke-test.sh --verbose
#   SERVICE_URL=https://custom-url.run.app ./scripts/smoke-test.sh

set -e

# Configuration
SERVICE_URL=${SERVICE_URL:-"https://nikita-api-1040094048579.us-central1.run.app"}
PROJECT=${PROJECT:-"gcp-transcribe-test"}
VERBOSE=${VERBOSE:-false}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "==================================="
echo "Nikita API Deployment Verification"
echo "==================================="
echo "Service URL: $SERVICE_URL"
echo "Project: $PROJECT"
echo ""

# Track failures
FAILURES=0

# Function to check endpoint
check_endpoint() {
    local endpoint=$1
    local expected_status=$2
    local description=$3

    echo -n "Testing $endpoint... "

    response=$(curl -s -w "%{http_code}" -o /tmp/response.txt "$SERVICE_URL$endpoint" 2>/dev/null || echo "000")
    body=$(cat /tmp/response.txt 2>/dev/null || echo "")

    if [ "$response" == "$expected_status" ]; then
        echo -e "${GREEN}PASS${NC} ($response)"
        if [ "$VERBOSE" == "true" ] && [ -n "$body" ]; then
            echo "   Response: $body"
        fi
        return 0
    else
        echo -e "${RED}FAIL${NC} (expected $expected_status, got $response)"
        if [ -n "$body" ]; then
            echo "   Response: $body"
        fi
        return 1
    fi
}

# Function to check JSON field
check_json_field() {
    local endpoint=$1
    local field=$2
    local expected=$3

    echo -n "Checking $endpoint.$field == '$expected'... "

    value=$(curl -s "$SERVICE_URL$endpoint" | jq -r ".$field" 2>/dev/null || echo "null")

    if [ "$value" == "$expected" ]; then
        echo -e "${GREEN}PASS${NC}"
        return 0
    else
        echo -e "${RED}FAIL${NC} (got '$value')"
        return 1
    fi
}

# 1. Health Endpoint
echo ""
echo "1. Health Checks"
echo "----------------"

check_endpoint "/health" "200" "Basic health" || ((FAILURES++))
check_json_field "/health" "status" "healthy" || ((FAILURES++))

check_endpoint "/health/deep" "200" "Deep health" || ((FAILURES++))
check_json_field "/health/deep" "database" "connected" || ((FAILURES++))

# 2. API Endpoints
echo ""
echo "2. Root Endpoint"
echo "----------------"

check_endpoint "/" "200" "Root" || ((FAILURES++))

# 3. Log Check
echo ""
echo "3. Recent Error Logs"
echo "--------------------"

# Get timestamp for 15 minutes ago (macOS compatible)
if [[ "$OSTYPE" == "darwin"* ]]; then
    TIMESTAMP=$(date -u -v-15M +%Y-%m-%dT%H:%M:%SZ)
else
    TIMESTAMP=$(date -u -d "-15 minutes" +%Y-%m-%dT%H:%M:%SZ)
fi

echo "Checking for errors since $TIMESTAMP..."

ERROR_COUNT=$(gcloud logging read \
    "resource.type=cloud_run_revision AND severity>=ERROR AND timestamp>=\"$TIMESTAMP\"" \
    --limit=100 \
    --project "$PROJECT" \
    --format=json 2>/dev/null | jq length)

if [ "$ERROR_COUNT" == "0" ] || [ -z "$ERROR_COUNT" ]; then
    echo -e "${GREEN}PASS${NC} - No errors in last 15 minutes"
else
    echo -e "${YELLOW}WARNING${NC} - $ERROR_COUNT errors found"

    if [ "$VERBOSE" == "true" ]; then
        echo ""
        echo "Recent errors:"
        gcloud logging read \
            "resource.type=cloud_run_revision AND severity>=ERROR AND timestamp>=\"$TIMESTAMP\"" \
            --limit=5 \
            --project "$PROJECT" \
            --format="table(timestamp,textPayload)" 2>/dev/null
    fi
fi

# 4. Current Revision
echo ""
echo "4. Deployment Info"
echo "------------------"

REVISION=$(gcloud run services describe nikita-api \
    --region us-central1 \
    --project "$PROJECT" \
    --format="value(status.traffic[0].revisionName)" 2>/dev/null || echo "unknown")

TRAFFIC=$(gcloud run services describe nikita-api \
    --region us-central1 \
    --project "$PROJECT" \
    --format="value(status.traffic[0].percent)" 2>/dev/null || echo "unknown")

echo "Current revision: $REVISION"
echo "Traffic: $TRAFFIC%"

# Summary
echo ""
echo "==================================="
if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}All checks passed!${NC}"
    exit 0
else
    echo -e "${RED}$FAILURES check(s) failed${NC}"
    exit 1
fi
