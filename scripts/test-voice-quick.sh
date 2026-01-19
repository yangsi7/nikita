#!/usr/bin/env bash
# Quick voice API smoke test - runs in <10 seconds
# Usage: ./scripts/test-voice-quick.sh [local|prod]

BASE="${1:-prod}"
[[ "$BASE" == "local" ]] && URL="http://localhost:8000" || URL="https://nikita-api-7xw52ajcea-uc.a.run.app"
USER_ID="c539927d-6d0c-42ea-b1c8-a3169e4421b0"

echo "Voice API Quick Test - $BASE"
echo "================================"

# Health
H=$(curl -s -o /dev/null -w "%{http_code}" "$URL/health" --max-time 5)
[[ "$H" == "200" ]] && echo "✅ Health: OK" || echo "❌ Health: $H"

# Availability
A=$(curl -s -o /dev/null -w "%{http_code}" "$URL/api/v1/voice/availability/$USER_ID" --max-time 10)
[[ "$A" == "200" ]] && echo "✅ Availability: OK" || echo "❌ Availability: $A"

# Initiate (403 = correct for game_over)
I=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$URL/api/v1/voice/initiate" -H "Content-Type: application/json" -d "{\"user_id\":\"$USER_ID\"}" --max-time 10)
[[ "$I" == "403" || "$I" == "200" ]] && echo "✅ Initiate: OK ($I)" || echo "❌ Initiate: $I"

# Pre-call
P=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$URL/api/v1/voice/pre-call" -H "Content-Type: application/json" -d '{"phone_number":"+15555555555"}' --max-time 10)
[[ "$P" == "200" ]] && echo "✅ Pre-call: OK" || echo "❌ Pre-call: $P"

# Server-tool (401/422 = expected without valid token)
S=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$URL/api/v1/voice/server-tool" -H "Content-Type: application/json" -d '{"tool_name":"get_context","signed_token":"test","data":{}}' --max-time 10)
[[ "$S" =~ ^4[0-9][0-9]$ ]] && echo "✅ Server-tool: OK (rejects invalid)" || echo "❌ Server-tool: $S"

# Webhook (401 = expected without signature)
W=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$URL/api/v1/voice/webhook" -H "Content-Type: application/json" -d '{"event_type":"test","session_id":"x","data":{}}' --max-time 10)
[[ "$W" =~ ^4[0-9][0-9]$ ]] && echo "✅ Webhook: OK (requires signature)" || echo "❌ Webhook: $W"

echo "================================"
echo "Done!"
