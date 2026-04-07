-- DEBT-006: Add unique constraint on elevenlabs_session_id (partial index, NULLs allowed)
-- Prevents duplicate voice call records for the same ElevenLabs session.
CREATE UNIQUE INDEX IF NOT EXISTS idx_voice_calls_session_id
  ON voice_calls(elevenlabs_session_id)
  WHERE elevenlabs_session_id IS NOT NULL;
