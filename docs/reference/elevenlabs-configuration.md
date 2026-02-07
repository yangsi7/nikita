# ElevenLabs Configuration Reference

This document is the **single source of truth** for ElevenLabs Conversational AI configuration in the Nikita project.

## Active Agents

| Agent | Environment Variable | Current ID | Purpose |
|-------|---------------------|------------|---------|
| Nikita (Main) | `ELEVENLABS_DEFAULT_AGENT_ID` | *(set in env)* | Voice conversations with Nikita |
| Meta-Nikita | `ELEVENLABS_META_NIKITA_AGENT_ID` | `agent_4801kewekhxgekzap1bqdr62dxvc` | Voice onboarding (game intro) |

**Dashboard**: [ElevenLabs Conversational AI](https://elevenlabs.io/conversational-ai)

## Environment Variables

### Required

| Variable | Description | Where to Get |
|----------|-------------|--------------|
| `ELEVENLABS_API_KEY` | API access key | [Profile > API Keys](https://elevenlabs.io/app/settings/api-keys) |
| `ELEVENLABS_DEFAULT_AGENT_ID` | Main Nikita agent ID | Dashboard > Agents > Copy ID |
| `ELEVENLABS_WEBHOOK_SECRET` | HMAC verification secret | Dashboard > Webhooks > Secret |

### Optional (Production)

| Variable | Description | Where to Get |
|----------|-------------|--------------|
| `ELEVENLABS_META_NIKITA_AGENT_ID` | Meta-Nikita agent ID | Dashboard > Agents > Copy ID |
| `ELEVENLABS_PHONE_NUMBER_ID` | Phone number resource ID | Dashboard > Phone Numbers |

### Example .env

```bash
# ElevenLabs Configuration
ELEVENLABS_API_KEY=sk_xxxxxxxxxxxxxxxx
ELEVENLABS_DEFAULT_AGENT_ID=agent_xxxxxxxxxxxx
ELEVENLABS_WEBHOOK_SECRET=whsec_xxxxxxxxxxxx
ELEVENLABS_META_NIKITA_AGENT_ID=agent_4801kewekhxgekzap1bqdr62dxvc
ELEVENLABS_PHONE_NUMBER_ID=pn_xxxxxxxxxxxx
```

## Configuration Ownership Matrix

| Setting | Owner | Location | Sync Method |
|---------|-------|----------|-------------|
| **Agent IDs** | Code | `config/settings.py` env vars | Manual (update env var after recreation) |
| **System Prompt** | Code | `MetaPromptService.generate_system_prompt()` | Auto (sent at call initiation) |
| **Dynamic Variables** | Code | `DynamicVariables` class | Auto (sent at call initiation) |
| **TTS Settings** | Code | `TTSSettings` per chapter/mood | Auto (sent at call initiation) |
| **Voice Selection** | Dashboard | ElevenLabs dashboard | Manual (one-time setup) |
| **Server Tools (Main)** | Script | `scripts/configure_nikita_tools.py` | Run script after agent changes |
| **Server Tools (Meta)** | Script | `scripts/configure_meta_nikita_tools.py` | Run script after agent changes |
| **Knowledge Base** | Dashboard OR API | Either | API preferred (version controlled) |
| **Phone Number** | Dashboard | ElevenLabs dashboard | Manual (store ID in env var) |
| **Webhook URLs** | Script | Config scripts | Update when Cloud Run URL changes |

## Server Tools

### Main Nikita Agent (4 tools)

Configure via: `python scripts/configure_nikita_tools.py`

| Tool | Description | Endpoint |
|------|-------------|----------|
| `get_context` | Load user context at call start | `/api/v1/voice/server-tool` |
| `get_memory` | Query Graphiti for memories | `/api/v1/voice/server-tool` |
| `score_turn` | Score emotional exchanges | `/api/v1/voice/server-tool` |
| `update_memory` | Store new facts to memory | `/api/v1/voice/server-tool` |

### Meta-Nikita Agent (3 tools)

Configure via: `python scripts/configure_meta_nikita_tools.py`

| Tool | Description | Endpoint |
|------|-------------|----------|
| `collect_profile` | Store user profile info | `/api/v1/onboarding/server-tool` |
| `configure_preferences` | Store experience preferences | `/api/v1/onboarding/server-tool` |
| `complete_onboarding` | Finalize onboarding, hand off | `/api/v1/onboarding/server-tool` |

## Webhook Configuration

### Endpoints

| Webhook | URL | Purpose |
|---------|-----|---------|
| Pre-call | `{BACKEND_URL}/api/v1/voice/pre-call` | Lookup user by phone, return availability |
| Server Tool | `{BACKEND_URL}/api/v1/voice/server-tool` | Handle tool calls during conversation |
| Post-call | `{BACKEND_URL}/api/v1/voice/webhook` | Store transcript, trigger post-processing |
| Onboarding Tool | `{BACKEND_URL}/api/v1/onboarding/server-tool` | Handle onboarding tool calls |

### Current Backend URL

```
https://nikita-api-1040094048579.us-central1.run.app
```

> **Note**: Update scripts when Cloud Run URL changes.

## Development Workflow

### When Creating a New Agent

1. Create agent in [ElevenLabs Dashboard](https://elevenlabs.io/conversational-ai)
2. Copy agent ID to appropriate env var
3. Configure server tools:
   - Main Nikita: `python scripts/configure_nikita_tools.py`
   - Meta-Nikita: `python scripts/configure_meta_nikita_tools.py`
4. Update this documentation with new agent ID
5. Deploy with updated env vars:
   ```bash
   gcloud run deploy nikita-api --source . --region us-central1 --project gcp-transcribe-test
   ```

### When Changing Server Tool URLs

1. Note new Cloud Run URL after deployment
2. Update `BACKEND_URL` in configuration scripts
3. Re-run tool configuration scripts
4. Verify tools work via test call

### When Adding New Server Tool

1. Add endpoint in `nikita/api/routes/voice.py`
2. Add tool handler in `nikita/agents/voice/server_tools.py`
3. Add tool definition to configuration script
4. Run script to update ElevenLabs
5. Test via voice call

### When Recreating an Agent

1. Create new agent in dashboard
2. Configure voice, first message, system prompt in dashboard
3. Update env var with new agent ID
4. Run tool configuration script
5. Reassign phone number if applicable
6. Test via inbound call

## Startup Validation

The application validates ElevenLabs configuration on startup:

```python
# Checked during startup:
# - ELEVENLABS_API_KEY is set
# - ELEVENLABS_DEFAULT_AGENT_ID is set (if voice enabled)
# - Agent exists in ElevenLabs (optional, can be slow)
```

Validation warnings appear in logs:
```
✓ ElevenLabs: API key configured
✓ ElevenLabs: Main agent ID configured (agent_xxx...)
⚠ ElevenLabs: Meta-Nikita agent ID not configured (onboarding disabled)
```

## TTS Settings by Chapter

| Chapter | Stability | Similarity | Speed | Personality |
|---------|-----------|------------|-------|-------------|
| 1 | 0.75 | 0.65 | 0.95 | Reserved, cautious |
| 2 | 0.65 | 0.70 | 1.00 | Warming up |
| 3 | 0.55 | 0.80 | 1.05 | Playful, teasing |
| 4 | 0.50 | 0.85 | 1.05 | Affectionate |
| 5 | 0.45 | 0.90 | 1.10 | Passionate, intimate |

Configured in: `nikita/agents/voice/tts_config.py`

## Related Documentation

- [Console Setup Guide](../guides/elevenlabs-console-setup.md) - Dynamic variables and tool descriptions
- [Voice Agent Spec](../../specs/007-voice-agent/spec.md) - Requirements and acceptance criteria
- [Voice Onboarding Spec](../../specs/028-voice-onboarding/spec.md) - Meta-Nikita requirements

## Troubleshooting

### Agent Not Found Error

```
Error: Agent {agent_id} not found
```

**Cause**: Agent was deleted or ID is incorrect.

**Fix**:
1. Verify agent exists in dashboard
2. Update env var with correct ID
3. Redeploy

### Server Tools Not Working

```
Error: Tool execution failed
```

**Cause**: Tools not configured or webhook URL changed.

**Fix**:
1. Run appropriate configuration script
2. Verify webhook URL matches current deployment
3. Check Cloud Run logs for errors

### HMAC Signature Mismatch

```
Error: Invalid webhook signature
```

**Cause**: Webhook secret mismatch between dashboard and env var.

**Fix**:
1. Copy webhook secret from dashboard
2. Update `ELEVENLABS_WEBHOOK_SECRET` env var
3. Redeploy
