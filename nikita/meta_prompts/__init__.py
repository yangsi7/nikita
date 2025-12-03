"""Meta-prompt module for intelligent prompt generation.

This module implements the meta-prompt architecture where all prompt
generation uses LLM-powered meta-prompts rather than static templates.

Key components:
- MetaPromptContext: All context needed for prompt generation
- GeneratedPrompt: Result of meta-prompt execution
- MetaPromptService: Central service for prompt generation
- ViceProfile: User's vice preference profile

Usage:
    from nikita.meta_prompts import MetaPromptService

    service = MetaPromptService(session)
    result = await service.generate_system_prompt(user_id)
"""

from nikita.meta_prompts.models import GeneratedPrompt, MetaPromptContext, ViceProfile
from nikita.meta_prompts.service import MetaPromptService

__all__ = [
    "MetaPromptContext",
    "GeneratedPrompt",
    "MetaPromptService",
    "ViceProfile",
]
