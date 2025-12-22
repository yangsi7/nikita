# E2E Journey Test Report

**Generated**: 2025-12-17T15:06:12.933091Z
**Test User**: Telegram ID 951219336
**Backend**: https://nikita-api-1040094048579.us-central1.run.app

## 1.1 - /start Command
*Timestamp: 2025-12-17T15:05:56.249148*

```json
{
  "action": "Send /start command",
  "telegram_id": 951219336,
  "response_status": 200,
  "response_body": "{\"status\":\"ok\"}"
}
```

## 1.2 - Check Registration State
*Timestamp: 2025-12-17T15:05:58.250749*

```json
{
  "check": "pending_registrations table",
  "expected": "Row with telegram_id=951219336 and otp_state='pending'",
  "note": "Query via Supabase MCP: SELECT * FROM pending_registrations WHERE telegram_id = 951219336"
}
```

## 1.3 - Email Input
*Timestamp: 2025-12-17T15:05:59.087055*

```json
{
  "action": "Send email for OTP",
  "email": "nikita.e2e.951219336@test.example.com",
  "response_status": 200,
  "response_body": "{\"status\":\"ok\"}"
}
```

## 1.4 - OTP State Check
*Timestamp: 2025-12-17T15:06:01.088931*

```json
{
  "check": "pending_registrations.otp_state",
  "expected": "'code_sent' or user entry created",
  "note": "OTP sent to nikita.e2e.951219336@test.example.com via Supabase Auth"
}
```

## 1.5 - OTP Verification
*Timestamp: 2025-12-17T15:06:01.927416*

```json
{
  "action": "Send OTP code",
  "otp": "123456 (test)",
  "response_status": 200,
  "response_body": "{\"status\":\"ok\"}",
  "note": "Real OTP verification requires email access or test bypass"
}
```

## 2.1 - Database Verification Queries
*Timestamp: 2025-12-17T15:06:03.929180*

```json
{
  "queries": [
    "SELECT * FROM pending_registrations WHERE telegram_id = 951219336",
    "SELECT * FROM users WHERE telegram_id = 951219336",
    "SELECT * FROM onboarding_states WHERE telegram_id = 951219336"
  ],
  "note": "Run these queries via Supabase MCP to verify state"
}
```

## 3.1 - Conversation Message
*Timestamp: 2025-12-17T15:06:04.774691*

```json
{
  "action": "Send conversation message",
  "message": "Hi Nikita! How are you doing today?",
  "response_status": 200,
  "response_body": "{\"status\":\"ok\"}"
}
```

## 4.1 - Post-Processing Trigger
*Timestamp: 2025-12-17T15:06:07.931225*

```json
{
  "action": "Trigger post-processing",
  "endpoint": "/tasks/process-conversations",
  "result": {
    "status_code": 404,
    "body": {
      "detail": "Not Found"
    }
  }
}
```

## 5.1 - Neo4j Memory Check
*Timestamp: 2025-12-17T15:06:12.932784*

```json
{
  "action": "Check Neo4j memory",
  "note": "Need user UUID to query /admin/debug/neo4j/{user_id}",
  "query": "SELECT id FROM users WHERE telegram_id = 951219336"
}
```

## Summary
*Timestamp: 2025-12-17T15:06:12.932852*

```json
{
  "test_telegram_id": 951219336,
  "test_email": "nikita.e2e.951219336@test.example.com",
  "phases_executed": [
    "1. Registration (OTP flow)",
    "2. Database state check",
    "3. Conversation test",
    "4. Post-processing trigger",
    "5. Neo4j memory check"
  ],
  "verification_queries": [
    "SELECT * FROM pending_registrations WHERE telegram_id = 951219336",
    "SELECT * FROM users WHERE telegram_id = 951219336",
    "SELECT * FROM user_metrics WHERE user_id = (SELECT id FROM users WHERE telegram_id = 951219336)",
    "SELECT * FROM conversations WHERE user_id = (SELECT id FROM users WHERE telegram_id = 951219336)",
    "SELECT * FROM onboarding_states WHERE telegram_id = 951219336"
  ],
  "cleanup_query": "DELETE FROM pending_registrations WHERE telegram_id = 951219336"
}
```
