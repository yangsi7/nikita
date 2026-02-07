"""Prompt templates for Nikita persona and game scenarios.

.. deprecated:: 0.9.0
    This module is deprecated and will be removed in version 2.0.0.
    Use :mod:`nikita.pipeline` instead for prompt generation.

    The context_engine module has been removed as of Spec 042.
    All prompt generation now happens via the unified pipeline at nikita/pipeline/.
"""
import warnings

warnings.warn(
    "nikita.prompts is deprecated and will be removed in v2.0. "
    "Use nikita.pipeline instead for unified prompt generation.",
    DeprecationWarning,
    stacklevel=2,
)
