"""Psyche agent package (Spec 056).

Provides daily PsycheState generation and trigger-based analysis
for Nikita's psychological disposition.

Feature-flagged: all behavior gated behind psyche_agent_enabled.
"""

from __future__ import annotations


def is_psyche_agent_enabled() -> bool:
    """Check if the psyche agent feature is enabled.

    Reads from settings.psyche_agent_enabled (default: False).
    Gate ALL psyche behavior behind this check.
    """
    from nikita.config.settings import get_settings

    return get_settings().psyche_agent_enabled
