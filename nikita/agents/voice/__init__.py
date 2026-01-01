"""Nikita voice agent - ElevenLabs Conversational AI 2.0 powered voice interface.

This module provides voice call handling for Nikita using ElevenLabs' Conversational AI SDK.
It implements the same personality and game mechanics as the text agent but through
real-time voice conversations.

Key Features (Spec 007):
- FR-001: Call initiation from portal/Telegram
- FR-005: Same personality across text/voice
- FR-006: Voice call scoring (aggregate per-call)
- FR-007: Server tools (get_context, get_memory, score_turn, update_memory)
- FR-016/FR-017: Emotional voice expression (chapter/mood-based TTS)
- FR-018: Dynamic variables injection
- FR-019/FR-020: Outbound/inbound phone calls via Twilio
- FR-022/FR-023: Server tool resilience (timeouts, fallbacks)
- FR-026: HMAC webhook verification

Architecture:
- Uses ElevenLabs Conversational AI 2.0 with Server Tools pattern
- Server tools call back to our API for context/memory/scoring
- Same MetaPromptService for personality/context
- Same NikitaMemory for knowledge graphs
- Post-call processing via webhooks
"""

import logging
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from nikita.agents.voice.models import (
        VoiceContext,
        ServerToolRequest,
        ServerToolResponse,
        CallScore,
        TranscriptEntry,
        CallResult,
        TTSSettings,
        DynamicVariables,
        ConversationConfig,
    )
    from nikita.agents.voice.deps import VoiceAgentDeps
    from nikita.agents.voice.service import VoiceService
    from nikita.agents.voice.client import ElevenLabsClient
    from nikita.agents.voice.context import VoiceContextBuilder
    from nikita.agents.voice.scoring import VoiceCallScorer
    from nikita.agents.voice.tts_config import TTSConfigService
    from nikita.agents.voice.context import DynamicVariablesBuilder, ConversationConfigBuilder
    from nikita.agents.voice.server_tools import ServerToolHandler


# Lazy imports to avoid circular dependencies
def get_voice_service() -> "VoiceService":
    """Get the voice service singleton."""
    from nikita.agents.voice.service import get_voice_service as _get_voice_service
    return _get_voice_service()


def get_elevenlabs_client() -> "ElevenLabsClient":
    """Get the ElevenLabs client singleton."""
    from nikita.agents.voice.client import get_elevenlabs_client as _get_client
    return _get_client()


def get_server_tool_handler() -> "ServerToolHandler":
    """Get the server tool handler singleton."""
    from nikita.agents.voice.server_tools import get_server_tool_handler as _get_handler
    return _get_handler()


def get_tts_config_service() -> "TTSConfigService":
    """Get the TTS config service singleton."""
    from nikita.agents.voice.tts_config import get_tts_config_service as _get_service
    return _get_service()


def get_dynamic_variables_builder() -> "DynamicVariablesBuilder":
    """Get the dynamic variables builder singleton."""
    from nikita.agents.voice.context import get_dynamic_variables_builder as _get_builder
    return _get_builder()


__all__ = [
    # Services
    "get_voice_service",
    "get_elevenlabs_client",
    "get_server_tool_handler",
    "get_tts_config_service",
    "get_dynamic_variables_builder",
    # Models (lazy import)
    "VoiceContext",
    "ServerToolRequest",
    "ServerToolResponse",
    "CallScore",
    "TranscriptEntry",
    "CallResult",
    "TTSSettings",
    "DynamicVariables",
    "ConversationConfig",
    # Deps (lazy import)
    "VoiceAgentDeps",
]
