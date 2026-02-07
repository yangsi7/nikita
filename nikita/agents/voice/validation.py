"""ElevenLabs configuration validation module.

This module validates ElevenLabs configuration on application startup
to catch configuration drift early.

Usage:
    from nikita.agents.voice.validation import validate_elevenlabs_config

    # In app startup
    warnings = await validate_elevenlabs_config()
    for warning in warnings:
        logger.warning(warning)
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nikita.config.settings import Settings

logger = logging.getLogger(__name__)


class ElevenLabsConfigError(Exception):
    """Raised when ElevenLabs configuration is invalid."""

    pass


async def validate_elevenlabs_config(
    settings: "Settings | None" = None,
    strict: bool = False,
) -> list[str]:
    """Validate ElevenLabs configuration.

    Checks:
    1. API key is set
    2. Default agent ID is set (if voice features enabled)
    3. Agent exists in ElevenLabs (optional, can be slow)
    4. Server tools are configured (optional)

    Args:
        settings: Application settings (loads from get_settings if None)
        strict: If True, raise exception on critical errors. If False, return warnings.

    Returns:
        List of warning messages (empty if all valid)

    Raises:
        ElevenLabsConfigError: If strict=True and critical config is missing
    """
    if settings is None:
        from nikita.config.settings import get_settings
        settings = get_settings()

    warnings: list[str] = []
    errors: list[str] = []

    # Check API key
    if not settings.elevenlabs_api_key:
        msg = "ELEVENLABS_API_KEY not configured - voice features disabled"
        if strict:
            errors.append(msg)
        else:
            warnings.append(f"[ElevenLabs] {msg}")
    else:
        logger.info("✓ ElevenLabs: API key configured")

    # Check default agent ID
    if not settings.elevenlabs_default_agent_id:
        msg = "ELEVENLABS_DEFAULT_AGENT_ID not configured - voice calls disabled"
        if strict:
            errors.append(msg)
        else:
            warnings.append(f"[ElevenLabs] {msg}")
    else:
        agent_id = settings.elevenlabs_default_agent_id
        logger.info(f"✓ ElevenLabs: Main agent ID configured ({agent_id[:20]}...)")

    # Check Meta-Nikita agent ID (optional)
    if not settings.elevenlabs_meta_nikita_agent_id:
        warnings.append("[ElevenLabs] Meta-Nikita agent ID not configured - voice onboarding disabled")
    else:
        agent_id = settings.elevenlabs_meta_nikita_agent_id
        logger.info(f"✓ ElevenLabs: Meta-Nikita agent ID configured ({agent_id[:20]}...)")

    # Check webhook secret
    if not settings.elevenlabs_webhook_secret:
        warnings.append("[ElevenLabs] Webhook secret not configured - webhook validation disabled")
    else:
        logger.info("✓ ElevenLabs: Webhook secret configured")

    # Check phone number ID (optional)
    if not settings.elevenlabs_phone_number_id:
        warnings.append("[ElevenLabs] Phone number ID not configured - outbound calls disabled")
    else:
        logger.info("✓ ElevenLabs: Phone number ID configured")

    # Raise errors if strict mode
    if strict and errors:
        raise ElevenLabsConfigError("\n".join(errors))

    return warnings


async def validate_agent_exists(
    agent_id: str,
    api_key: str,
) -> tuple[bool, str | None]:
    """Validate that an agent exists in ElevenLabs.

    This makes an API call and can be slow. Use sparingly.

    Args:
        agent_id: ElevenLabs agent ID
        api_key: ElevenLabs API key

    Returns:
        Tuple of (exists, error_message)
    """
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://api.elevenlabs.io/v1/convai/agents/{agent_id}",
                headers={"xi-api-key": api_key},
            )

            if response.status_code == 200:
                data = response.json()
                agent_name = data.get("name", "Unknown")
                logger.info(f"✓ ElevenLabs: Agent '{agent_name}' exists ({agent_id})")
                return True, None
            elif response.status_code == 404:
                return False, f"Agent {agent_id} not found in ElevenLabs"
            else:
                return False, f"Failed to verify agent: HTTP {response.status_code}"

    except httpx.TimeoutException:
        return False, "Timeout while verifying agent (ElevenLabs API slow)"
    except Exception as e:
        return False, f"Error verifying agent: {e}"


async def validate_agent_has_tools(
    agent_id: str,
    api_key: str,
    expected_tools: list[str] | None = None,
) -> tuple[bool, list[str]]:
    """Validate that an agent has the expected server tools.

    Args:
        agent_id: ElevenLabs agent ID
        api_key: ElevenLabs API key
        expected_tools: List of expected tool names (None = skip check)

    Returns:
        Tuple of (all_present, missing_tools)
    """
    import httpx

    if expected_tools is None:
        expected_tools = ["get_context", "get_memory", "score_turn", "update_memory"]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://api.elevenlabs.io/v1/convai/agents/{agent_id}",
                headers={"xi-api-key": api_key},
            )

            if response.status_code != 200:
                return False, expected_tools

            data = response.json()
            tools = data.get("conversation_config", {}).get("agent", {}).get("prompt", {}).get("tools", [])
            tool_names = [t.get("name") for t in tools]

            missing = [t for t in expected_tools if t not in tool_names]

            if missing:
                logger.warning(f"[ElevenLabs] Agent {agent_id} missing tools: {missing}")
                return False, missing
            else:
                logger.info(f"✓ ElevenLabs: Agent has all {len(expected_tools)} expected tools")
                return True, []

    except Exception as e:
        logger.warning(f"[ElevenLabs] Failed to check tools: {e}")
        return False, expected_tools
