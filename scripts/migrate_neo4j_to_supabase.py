#!/usr/bin/env python3
"""Migrate memory facts from Neo4j/Graphiti to Supabase pgVector.

Spec 042 Phase 1 T1.4: One-time migration script.

Usage:
    python scripts/migrate_neo4j_to_supabase.py [--dry-run] [--user-id UUID]

Steps:
1. Connect to Neo4j and export all facts from 3 graphs
2. Generate embeddings via OpenAI text-embedding-3-small
3. Bulk insert to memory_facts table in Supabase
4. Validate counts match

AC-1.4.1: Connects to Neo4j, exports all facts from 3 graphs
AC-1.4.2: Generates embeddings for all exported facts
AC-1.4.3: Bulk inserts to memory_facts table
AC-1.4.4: Validates count of facts matches per graph_type
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from nikita.config.settings import get_settings
from nikita.memory.supabase_memory import SupabaseMemory

logger = logging.getLogger(__name__)


async def export_neo4j_facts(
    user_id: str,
) -> dict[str, list[dict]]:
    """Export facts from Neo4j graphs.

    Returns:
        Dict mapping graph_type -> list of fact dicts.
    """
    from nikita.memory.graphiti_client import get_memory_client

    facts: dict[str, list[dict]] = {
        "user": [],
        "relationship": [],
        "nikita": [],
    }

    try:
        async with await get_memory_client(user_id) as memory:
            for graph_type in ["user", "relationship", "nikita"]:
                group_id = memory._get_group_id(graph_type)
                logger.info(
                    f"[EXPORT] Searching {graph_type} graph (group={group_id})..."
                )

                try:
                    edges = await memory.graphiti.search(
                        query="*",
                        group_ids=[group_id],
                        num_results=500,
                    )
                    for edge in edges:
                        facts[graph_type].append({
                            "fact": edge.fact,
                            "created_at": (
                                edge.created_at.isoformat()
                                if hasattr(edge, "created_at") and edge.created_at
                                else datetime.now(timezone.utc).isoformat()
                            ),
                            "source": "neo4j_migration",
                        })
                    logger.info(
                        f"[EXPORT] {graph_type}: {len(facts[graph_type])} facts"
                    )
                except Exception as e:
                    logger.warning(f"[EXPORT] {graph_type} graph error: {e}")

    except Exception as e:
        logger.error(f"[EXPORT] Failed to connect to Neo4j: {e}")
        raise

    return facts


async def import_to_supabase(
    user_id: UUID,
    facts: dict[str, list[dict]],
    dry_run: bool = False,
) -> dict[str, int]:
    """Import facts to Supabase memory_facts table.

    Returns:
        Dict mapping graph_type -> count of imported facts.
    """
    settings = get_settings()

    from nikita.db.database import get_session_maker

    session_maker = get_session_maker()

    counts: dict[str, int] = {}

    async with session_maker() as session:
        memory = SupabaseMemory(
            session=session,
            user_id=user_id,
            openai_api_key=settings.openai_api_key or "",
        )

        for graph_type, fact_list in facts.items():
            if not fact_list:
                counts[graph_type] = 0
                continue

            logger.info(
                f"[IMPORT] Processing {len(fact_list)} {graph_type} facts..."
            )

            # Batch embed all texts
            texts = [f["fact"] for f in fact_list]

            if dry_run:
                logger.info(f"[DRY RUN] Would embed {len(texts)} texts and insert {len(fact_list)} facts")
                counts[graph_type] = len(fact_list)
                continue

            try:
                embeddings = await memory.generate_embeddings_batch(texts)
            except Exception as e:
                logger.error(f"[IMPORT] Embedding batch failed for {graph_type}: {e}")
                counts[graph_type] = 0
                continue

            # Insert facts with pre-generated embeddings
            imported = 0
            for fact_dict, embedding in zip(fact_list, embeddings):
                try:
                    await memory._repo.add_fact(
                        user_id=user_id,
                        fact=fact_dict["fact"],
                        graph_type=graph_type,
                        embedding=embedding,
                        source="neo4j_migration",
                        confidence=0.8,
                        metadata={"migrated_at": datetime.now(timezone.utc).isoformat()},
                    )
                    imported += 1
                except Exception as e:
                    logger.warning(f"[IMPORT] Failed to insert fact: {e}")

            counts[graph_type] = imported
            logger.info(f"[IMPORT] {graph_type}: {imported}/{len(fact_list)} imported")

        if not dry_run:
            await session.commit()

    return counts


def validate_counts(
    neo4j_counts: dict[str, int],
    supabase_counts: dict[str, int],
) -> bool:
    """Validate that Supabase counts match Neo4j per graph_type."""
    all_match = True
    for graph_type in ["user", "relationship", "nikita"]:
        neo4j_count = neo4j_counts.get(graph_type, 0)
        supa_count = supabase_counts.get(graph_type, 0)
        if neo4j_count != supa_count:
            logger.error(
                f"[VALIDATE] Mismatch for {graph_type}: "
                f"Neo4j={neo4j_count}, Supabase={supa_count}"
            )
            all_match = False
        else:
            logger.info(
                f"[VALIDATE] {graph_type}: {supa_count}/{neo4j_count} OK"
            )
    return all_match


async def run_migration(
    user_id: str,
    dry_run: bool = False,
    export_path: str | None = None,
) -> None:
    """Run the full Neo4j → Supabase migration."""
    logger.info(f"[MIGRATE] Starting migration for user {user_id} (dry_run={dry_run})")

    # Step 1: Export from Neo4j
    facts = await export_neo4j_facts(user_id)
    neo4j_counts = {gt: len(fl) for gt, fl in facts.items()}
    total = sum(neo4j_counts.values())
    logger.info(f"[MIGRATE] Exported {total} facts from Neo4j: {neo4j_counts}")

    # Optionally save export to JSON
    if export_path:
        with open(export_path, "w") as f:
            json.dump(facts, f, indent=2, default=str)
        logger.info(f"[MIGRATE] Saved export to {export_path}")

    if total == 0:
        logger.info("[MIGRATE] No facts to migrate. Done.")
        return

    # Step 2+3: Generate embeddings + insert
    user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
    supabase_counts = await import_to_supabase(user_uuid, facts, dry_run=dry_run)

    # Step 4: Validate
    if not dry_run:
        if validate_counts(neo4j_counts, supabase_counts):
            logger.info("[MIGRATE] Migration PASSED - all counts match")
        else:
            logger.error("[MIGRATE] Migration FAILED - count mismatch")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate memory facts from Neo4j to Supabase pgVector"
    )
    parser.add_argument(
        "--user-id",
        type=str,
        help="Migrate a specific user (UUID string)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Export and count without importing",
    )
    parser.add_argument(
        "--export-path",
        type=str,
        default=None,
        help="Save Neo4j export to JSON file",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if not args.user_id:
        logger.error("--user-id is required")
        sys.exit(1)

    asyncio.run(
        run_migration(
            user_id=args.user_id,
            dry_run=args.dry_run,
            export_path=args.export_path,
        )
    )


if __name__ == "__main__":
    main()
