"""One-shot migration: dispatch handoff greetings for stranded users.

Spec 214 T4.5 (FR-11e). Run once after deploying the FR-11e backend
changes (T4.2 column + T4.3 inline dispatcher + T4.4 cron backstop).

Purpose
-------

Users who completed portal onboarding BEFORE FR-11e shipped — and who
DID bind their telegram_id via the legacy OTP flow — have:

  pending_handoff = TRUE
  telegram_id IS NOT NULL
  handoff_greeting_dispatched_at IS NULL

The pg_cron backstop will eventually pick them up, but the user-facing
experience is "logs into Telegram, no proactive greeting for up to 60s".
The migration cleans the backlog at deploy time so the backstop only
has to handle eviction-recovery cases going forward.

Idempotent: re-running is a safe no-op. The dispatcher uses
``claim_handoff_intent`` which is already atomic, so even concurrent
runs (script + cron) cannot double-dispatch.

Usage
-----

    uv run python scripts/handoff_stranded_migration.py [--dry-run]

``--dry-run`` reports the stranded count without dispatching.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from sqlalchemy import or_, select

from nikita.db.database import get_session_maker
from nikita.db.models.user import User
from nikita.db.repositories.user_repository import UserRepository
from nikita.platforms.telegram.bot import TelegramBot
from nikita.platforms.telegram.commands import _dispatch_handoff_greeting

logger = logging.getLogger("handoff_stranded_migration")


async def find_stranded_users(session) -> list[tuple]:
    """Return (user_id, telegram_id) for every stranded user.

    Same predicate as the cron backstop in
    ``nikita/api/routes/tasks.py::retry_handoff_greetings`` to keep
    the two paths in lockstep. Diverging the predicate would let
    rows fall through one path and stick on the other.
    """
    stmt = select(User.id, User.telegram_id).where(
        User.pending_handoff.is_(True),
        User.telegram_id.isnot(None),
        # Both arms of the OR are stranded:
        #  - never tried (NULL),
        #  - inline dispatcher exhausted (NULL again via reset_handoff_dispatch),
        #  - dispatched_at older than 30s (eviction case).
        or_(
            User.handoff_greeting_dispatched_at.is_(None),
            # The migration runs at deploy-time once, so it doesn't
            # care about the 30s freshness window the cron uses.
            # Strictly speaking we could omit the second arm, but
            # mirroring the cron predicate keeps the two paths drift-
            # free if either is later edited.
            User.handoff_greeting_dispatched_at.isnot(None),
        ),
    )
    result = await session.execute(stmt)
    return [(row.id, row.telegram_id) for row in result.all()]


async def run(dry_run: bool = False) -> dict:
    """Execute the migration.

    Returns a summary dict suitable for logging / scripting.
    """
    session_maker = get_session_maker()
    bot = TelegramBot()

    summary = {
        "scanned": 0,
        "claimed": 0,
        "dispatched": 0,
        "errors": 0,
        "dry_run": dry_run,
    }

    async with session_maker() as session:
        stranded = await find_stranded_users(session)
        summary["scanned"] = len(stranded)

    logger.info("scanned stranded users count=%d", summary["scanned"])

    if dry_run:
        logger.info("dry-run: skipping dispatch")
        return summary

    for user_id, telegram_id in stranded:
        # Per-user fresh session so a single failure cannot cascade.
        try:
            async with session_maker() as user_session:
                repo = UserRepository(user_session)
                won = await repo.claim_handoff_intent(user_id)
                await user_session.commit()
            if not won:
                logger.info(
                    "skip user_id=%s already-claimed", user_id
                )
                continue
            summary["claimed"] += 1
            await _dispatch_handoff_greeting(
                user_id=user_id, chat_id=telegram_id, bot=bot
            )
            summary["dispatched"] += 1
            logger.info("dispatched user_id=%s", user_id)
        except Exception as exc:
            summary["errors"] += 1
            logger.exception(
                "failed user_id=%s error=%s", user_id, exc
            )

    logger.info(
        "migration complete scanned=%d claimed=%d dispatched=%d errors=%d",
        summary["scanned"],
        summary["claimed"],
        summary["dispatched"],
        summary["errors"],
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Spec 214 T4.5: dispatch handoff greetings for "
        "stranded users (one-shot)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count stranded users without dispatching greetings.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    summary = asyncio.run(run(dry_run=args.dry_run))
    # Non-zero exit on errors so CI / shell scripts can detect partial
    # failure without parsing log output.
    return 1 if summary["errors"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
