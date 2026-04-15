# Diagram: Voice Call Flow

**Type**: Behavioral — Sequence Flow
**Scope**: Inbound and outbound voice call paths end-to-end
**Sources**:
- `nikita/agents/voice/inbound.py` — InboundCallHandler.handle_incoming_call()
- `nikita/agents/voice/server_tools.py` — ServerToolHandler (get_context, get_memory, score_turn, update_memory)
- `nikita/agents/voice/service.py` — VoiceService.initiate_call()
- `nikita/agents/voice/scheduling.py` — VoiceEventScheduler
- `nikita/api/routes/voice.py` — POST /pre-call (line 941), POST /server-tool (line 349), POST /webhook

---

```
+===================================================================+
|  INBOUND CALL FLOW                                                |
+===================================================================+

  (User's phone rings Twilio number +41787950009)
          |
          v
  [Twilio] --> POST /api/v1/voice/pre-call
          |
          v
  +--[ InboundCallHandler.handle_incoming_call() ]--+
  | inbound.py                                      |
  |                                                 |
  | 1. HMAC signature validation                    |
  |       (verify_elevenlabs_signature)             |
  |       |                                         |
  |       +--> Invalid: 401 [EXIT]                  |
  |                                                 |
  | 2. Phone lookup                                 |
  |       UserRepository.get_by_phone_number()      |
  |       |                                         |
  |       +--> Not found:                           |
  |            accept_call=False                    |
  |            dynamic_variables=defaults [EXIT]    |
  |                                                 |
  | 3. Onboarding status check                      |
  |       onboarding_status IN (completed, skipped)?|
  |       |                                         |
  |       +--> Not complete:                        |
  |            accept_call=False                    |
  |            first_message="wait for Meta-Nikita" |
  |            [EXIT]                               |
  |                                                 |
  | 4. Availability check (chapter-based prob.)     |
  |       Ch1=10%, Ch2=30%, Ch3=50%,               |
  |       Ch4=70%, Ch5=95%                          |
  |       |                                         |
  |       +--> Unavailable:                         |
  |            accept_call=False + reason msg [EXIT]|
  |                                                 |
  | 5. Build dynamic_variables                      |
  |       build_dynamic_variables(user)             |
  |       11 vars: user_name, chapter,              |
  |       relationship_score, engagement_state,     |
  |       nikita_mood, nikita_energy, time_of_day,  |
  |       recent_topics, open_threads,              |
  |       secret__user_id, secret__signed_token     |
  |                                                 |
  | 6. Build conversation_config_override           |
  |       a. Load ready_prompt (platform='voice')   |
  |          from ready_prompts table               |
  |       b. Fallback: cached_voice_prompt on users |
  |       c. Fallback: VoiceAgentConfig.generate()  |
  |       d. OpeningSelector.select() -> first_msg  |
  |       e. TTSConfigService.get_chapter_settings()|
  |          (stability, similarity_boost, speed,   |
  |           expressive_mode=True, voice_id)       |
  |                                                 |
  | 7. VoiceSessionManager.create_session()         |
  |                                                 |
  | 8. Return accept_call=True                      |
  |       + dynamic_variables                       |
  |       + conversation_config_override            |
  +-------------------------------------------------+
          |
          v
  [ElevenLabs picks up] <-- dynamic_variables injected into prompt
          |
          | DURING CALL (ElevenLabs --> POST /api/v1/voice/server-tool)
          |
          v
  +--[ ServerToolHandler.handle() ]--+
  | server_tools.py                  |
  |                                  |
  | Validate signed token (HMAC)     |
  | token format: user_id:session_id |
  |   :timestamp:signature           |
  | TTL: 1800s (30 min)              |
  |                                  |
  | Route by tool_name:              |
  |                                  |
  | get_context [timeout: 2s]        |
  |   user facts + memories +        |
  |   life events + vices            |
  |   --> today_summary, backstory   |
  |   --> recent_summaries           |
  |                                  |
  | get_memory [timeout: 2s]         |
  |   SupabaseMemory.search()        |
  |   pgVector semantic search       |
  |   --> memory_facts (top-k)       |
  |   --> conversation_threads       |
  |                                  |
  | score_turn [timeout: 2s]         |
  |   VoiceCallScorer.score_turn()   |
  |   metric deltas (-5 to +5 each)  |
  |   --> user_metrics UPDATE        |
  |   --> score_history INSERT       |
  |                                  |
  | update_memory [timeout: 2s]      |
  |   SupabaseMemory.add_fact()      |
  |   pgVector dedup (0.95 cosine)   |
  |   --> memory_facts INSERT        |
  +----------------------------------+

  (User hangs up)
          |
          v
  [ElevenLabs] --> POST /api/v1/voice/webhook
          |
          v
  +--[ voice.py: handle_webhook() ]--+
  | Verify ElevenLabs signature      |
  | Fetch transcript from ElevenLabs |
  | --> conversations INSERT         |
  |     (platform='voice')           |
  |                                  |
  | PipelineOrchestrator.process(    |
  |   platform='voice')              |
  | --> all 11 stages run            |
  | (same as text path, Diagram 01)  |
  +----------------------------------+


+===================================================================+
|  OUTBOUND CALL FLOW                                               |
+===================================================================+

  [pg_cron] every 1 min
  --> POST /tasks/deliver
          |
          v
  +--[ tasks.py: deliver_pending_messages() ]--+
  | Query scheduled_events WHERE               |
  |   platform='voice' AND                     |
  |   deliver_at <= NOW() AND                  |
  |   delivered=False                          |
  |                                            |
  | --> VoiceService.initiate_call(user_id)    |
  |       ElevenLabs SDK call                  |
  |       POST ElevenLabs API                  |
  |       --> voice_calls INSERT               |
  |       Returns: call_sid, session_id        |
  |                                            |
  | --> mark event delivered                   |
  +--------------------------------------------+

  +-- Scheduling source (upstream) --+
  | VoiceEventScheduler              |
  | scheduling.py                    |
  |                                  |
  | get_chapter_delay():             |
  |   Ch1: 120-300s                  |
  |   Ch2: 60-180s                   |
  |   Ch3: 30-120s                   |
  |   Ch4: 10-60s                    |
  |   Ch5: 5-30s                     |
  |                                  |
  | Writes to scheduled_events       |
  | (platform='voice')               |
  | Triggered by TouchpointStage     |
  | or cross-platform follow-up      |
  +----------------------------------+


+===================================================================+
|  SESSION LIFECYCLE (inbound.py: VoiceSessionManager)              |
+===================================================================+

  create_session()       --> state: ACTIVE
          |
     (call drop)
          |
          v
  handle_disconnect()    --> state: DISCONNECTED
          |
          +---< elapsed < 30s? >
          |                |
        yes               no
          |                |
  attempt_recovery()  finalize_session()
   state: ACTIVE      state: FINALIZED
  (reconnect ok)       (session done)

  TTL eviction: sessions older than 3600s evicted on next call.

Legend:
  --> sync call / data write
  ..> async / non-blocking
  [EXIT] returns immediately; no ElevenLabs call accepted
  < > decision / branch point
  [timeout: Ns] server tool falls back to cache_friendly defaults on timeout
```

---

**Key Actors**

| Actor | File | Role |
|-------|------|------|
| InboundCallHandler | `nikita/agents/voice/inbound.py` | Pre-call webhook handler |
| VoiceSessionManager | `nikita/agents/voice/inbound.py` | Session state tracking |
| ServerToolHandler | `nikita/agents/voice/server_tools.py` | During-call tool dispatch |
| VoiceService | `nikita/agents/voice/service.py` | Outbound call initiation |
| VoiceEventScheduler | `nikita/agents/voice/scheduling.py` | Chapter-based delay scheduling |

**API Endpoints**

| Endpoint | Method | Handler | Purpose |
|----------|--------|---------|---------|
| `/api/v1/voice/pre-call` | POST | `handle_pre_call()` | Twilio inbound webhook |
| `/api/v1/voice/server-tool` | POST | `ServerToolHandler.handle()` | During-call tool calls |
| `/api/v1/voice/webhook` | POST | `handle_webhook()` | Call end event |
| `/api/v1/voice/initiate` | POST | `VoiceService.initiate_call()` | Outbound call start |

**Database Tables Written**

| Table | Operation |
|-------|-----------|
| `voice_calls` | INSERT on call start (initiate) and end (webhook) |
| `conversations` | INSERT on webhook (transcript persisted) |
| `user_metrics` | UPDATE via score_turn server tool |
| `score_history` | INSERT via score_turn server tool |
| `memory_facts` | INSERT via update_memory server tool (pgVector) |
| `scheduled_events` | INSERT by VoiceEventScheduler for outbound |
