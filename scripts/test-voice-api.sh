#!/usr/bin/env bash
#
# Voice API E2E Test Script
# Run: ./scripts/test-voice-api.sh [local|prod]
#
# Rapid feedback without user intervention - tests all 5 voice endpoints
#

set -euo pipefail

# Configuration
ENV="${1:-prod}"
if [[ "$ENV" == "local" ]]; then
    BASE_URL="http://localhost:8000"
else
    BASE_URL="https://nikita-api-7xw52ajcea-uc.a.run.app"
fi

# Test user ID (from Supabase)
TEST_USER_ID="c539927d-6d0c-42ea-b1c8-a3169e4421b0"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "====================================="
echo "Voice API E2E Tests"
echo "Environment: $ENV"
echo "Base URL: $BASE_URL"
echo "====================================="
echo ""

PASSED=0
FAILED=0
WARNINGS=0

# Helper function to run a test
run_test() {
    local name="$1"
    local method="$2"
    local endpoint="$3"
    local data="${4:-}"
    local expected_status="${5:-200}"

    echo -n "Testing $name... "

    if [[ "$method" == "GET" ]]; then
        RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint" 2>/dev/null)
    else
        RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data" 2>/dev/null)
    fi

    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [[ "$HTTP_CODE" == "$expected_status" ]]; then
        echo -e "${GREEN}PASS${NC} (HTTP $HTTP_CODE)"
        ((PASSED++))
        # Show response summary
        echo "  └─ Response: $(echo "$BODY" | jq -c '.' 2>/dev/null | head -c 200)..."
    elif [[ "$expected_status" == "4xx" && "$HTTP_CODE" =~ ^4[0-9][0-9]$ ]]; then
        echo -e "${GREEN}PASS${NC} (HTTP $HTTP_CODE - expected 4xx)"
        ((PASSED++))
        echo "  └─ Response: $(echo "$BODY" | jq -c '.' 2>/dev/null | head -c 200)..."
    else
        echo -e "${RED}FAIL${NC} (HTTP $HTTP_CODE, expected $expected_status)"
        ((FAILED++))
        echo "  └─ Response: $BODY"
    fi
}

# Health check
echo "--- Health Check ---"
run_test "Health Endpoint" "GET" "/health" "" "200"
echo ""

# Voice API Tests
echo "--- Voice API Endpoints ---"

# 1. GET /availability/{user_id} - With valid user
run_test "Availability (valid user)" "GET" "/api/v1/voice/availability/$TEST_USER_ID" "" "200"

# 2. GET /availability/{user_id} - With invalid user (should 404)
run_test "Availability (invalid user)" "GET" "/api/v1/voice/availability/00000000-0000-0000-0000-000000000000" "" "404"

# 3. POST /initiate - With valid user (may 403 if game_over)
echo -n "Testing Initiate Call... "
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/v1/voice/initiate" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\": \"$TEST_USER_ID\"}" 2>/dev/null)
HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [[ "$HTTP_CODE" == "200" ]]; then
    echo -e "${GREEN}PASS${NC} (HTTP 200 - call initiated)"
    ((PASSED++))
    # Extract session_id for later tests
    SESSION_ID=$(echo "$BODY" | jq -r '.session_id' 2>/dev/null)
    SIGNED_TOKEN=$(echo "$BODY" | jq -r '.signed_token' 2>/dev/null)
    echo "  └─ session_id: $SESSION_ID"
elif [[ "$HTTP_CODE" == "403" ]]; then
    echo -e "${YELLOW}WARN${NC} (HTTP 403 - expected for game_over user)"
    ((WARNINGS++))
    echo "  └─ $BODY"
    SESSION_ID=""
    SIGNED_TOKEN=""
else
    echo -e "${RED}FAIL${NC} (HTTP $HTTP_CODE)"
    ((FAILED++))
    echo "  └─ $BODY"
    SESSION_ID=""
    SIGNED_TOKEN=""
fi

# 4. POST /pre-call - Pre-call webhook (inbound)
run_test "Pre-call Webhook (unknown caller)" "POST" "/api/v1/voice/pre-call" \
    '{"phone_number": "+15555555555"}' "200"

run_test "Pre-call Webhook (missing phone)" "POST" "/api/v1/voice/pre-call" \
    '{}' "4xx"

# 5. POST /server-tool - Server tool endpoint
# Test with invalid token (should fail gracefully)
run_test "Server Tool (invalid token)" "POST" "/api/v1/voice/server-tool" \
    '{"tool_name": "get_context", "signed_token": "invalid_token", "data": {}}' "4xx"

# If we have a valid token from initiate, test with it
if [[ -n "${SIGNED_TOKEN:-}" && "$SIGNED_TOKEN" != "null" ]]; then
    run_test "Server Tool (valid token)" "POST" "/api/v1/voice/server-tool" \
        "{\"tool_name\": \"get_context\", \"signed_token\": \"$SIGNED_TOKEN\", \"data\": {}}" "200"
fi

# 6. POST /webhook - Webhook endpoint
run_test "Webhook (call_ended)" "POST" "/api/v1/voice/webhook" \
    '{"event_type": "call_ended", "session_id": "test-session", "data": {"duration_seconds": 60}}' "200"

echo ""
echo "====================================="
echo -e "Results: ${GREEN}$PASSED passed${NC}, ${YELLOW}$WARNINGS warnings${NC}, ${RED}$FAILED failed${NC}"
echo "====================================="

# Exit with error if any tests failed
if [[ $FAILED -gt 0 ]]; then
    exit 1
fi
