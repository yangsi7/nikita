"""Memory pipeline for Nikita.

Provides two backends:
- SupabaseMemory (recommended): pgVector-based, <100ms search, no cold start
- NikitaMemory (deprecated): Neo4j/Graphiti, 30-73s cold start

Spec 042 T1.5: SupabaseMemory exported alongside NikitaMemory with deprecation.
"""

import warnings

from nikita.memory.supabase_memory import (
    EmbeddingError,
    SupabaseMemory,
    get_supabase_memory_client,
)

# Re-export for backward compatibility (deprecated)
from nikita.memory.graphiti_client import NikitaMemory as _NikitaMemory
from nikita.memory.graphiti_client import get_memory_client as _get_memory_client


def NikitaMemory(*args, **kwargs):
    """Deprecated: Use SupabaseMemory instead."""
    warnings.warn(
        "NikitaMemory is deprecated and will be removed in v2.0. "
        "Use SupabaseMemory instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _NikitaMemory(*args, **kwargs)


def get_memory_client(*args, **kwargs):
    """Deprecated: Use get_supabase_memory_client instead."""
    warnings.warn(
        "get_memory_client is deprecated and will be removed in v2.0. "
        "Use get_supabase_memory_client instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return _get_memory_client(*args, **kwargs)


__all__ = [
    "SupabaseMemory",
    "EmbeddingError",
    "get_supabase_memory_client",
    "NikitaMemory",
    "get_memory_client",
]
