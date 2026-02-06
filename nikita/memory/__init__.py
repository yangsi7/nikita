"""Memory pipeline for Nikita.

Spec 042 T1.5: SupabaseMemory is the primary backend.
NikitaMemory (Neo4j/Graphiti) has been removed.

All memory operations now use SupabaseMemory with pgVector for semantic search.
"""

from nikita.memory.supabase_memory import (
    EmbeddingError,
    SupabaseMemory,
    get_supabase_memory_client as get_memory_client,
)

__all__ = [
    "SupabaseMemory",
    "EmbeddingError",
    "get_memory_client",
]
