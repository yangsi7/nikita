"""Context engineering module for Nikita.

This module implements the context engineering redesign (spec 012):
- Session detection (15 min timeout for text, call end for voice)
- Post-processing pipeline (8 stages)
- System prompt generation via MetaPromptService

Architecture:
- PRE-CONVERSATION: Generate rich system prompt via meta-prompts (~200ms)
- DURING CONVERSATION: Pure LLM conversation with optional retrieval (NO memory writes)
- POST-CONVERSATION: Async pipeline extracts facts, updates graphs, generates summaries

Key components:
- session_detector: Detect when text sessions have timed out
- post_processor: 8-stage pipeline for extracting and storing context
- template_generator: System prompt composition (now delegates to MetaPromptService)

Note: As of Dec 2025, template_generator and post_processor use MetaPromptService
for intelligent prompt generation via Claude Haiku meta-prompts, replacing the
old static f-string templates.

See: nikita/meta_prompts/ for the meta-prompt implementation.
"""

from nikita.context.post_processor import PostProcessor, process_conversations
from nikita.context.session_detector import SessionDetector
from nikita.context.template_generator import TemplateGenerator, generate_system_prompt

__all__ = [
    "SessionDetector",
    "PostProcessor",
    "process_conversations",
    "TemplateGenerator",
    "generate_system_prompt",
]
