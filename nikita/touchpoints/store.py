"""TouchpointStore for database operations (Spec 025, Phase A: T004).

Repository pattern for scheduled_touchpoints table.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.scheduled_touchpoint import (
    ScheduledTouchpoint as ScheduledTouchpointDB,
)
from nikita.touchpoints.models import (
    ScheduledTouchpoint,
    TriggerContext,
    TriggerType,
)


class TouchpointStore:
    """Repository for scheduled touchpoints.

    Provides CRUD operations and queries for the scheduled_touchpoints table.

    Attributes:
        session: AsyncSession for database operations.
    """

    def __init__(self, session: AsyncSession):
        """Initialize store with database session.

        Args:
            session: SQLAlchemy async session.
        """
        self.session = session

    async def create(
        self,
        touchpoint: ScheduledTouchpoint | None = None,
        *,
        user_id: UUID | None = None,
        trigger_type: TriggerType | None = None,
        trigger_context: dict | None = None,
        delivery_at: datetime | None = None,
        chapter: int | None = None,
        message_content: str | None = None,
    ) -> ScheduledTouchpoint:
        """Create a new scheduled touchpoint.

        Can be called with a ScheduledTouchpoint model or with individual parameters.

        Args:
            touchpoint: ScheduledTouchpoint Pydantic model to persist.
            user_id: User's UUID (if not using touchpoint model).
            trigger_type: Type of trigger (if not using touchpoint model).
            trigger_context: Trigger context dict (if not using touchpoint model).
            delivery_at: Scheduled delivery time (if not using touchpoint model).
            chapter: Relationship chapter (if not using touchpoint model).
            message_content: Pre-generated message (if not using touchpoint model).

        Returns:
            Created touchpoint with ID assigned.
        """
        from uuid import uuid4

        if touchpoint is not None:
            # Using model
            db_touchpoint = ScheduledTouchpointDB(
                id=touchpoint.touchpoint_id,
                user_id=touchpoint.user_id,
                trigger_type=touchpoint.trigger_type.value,
                trigger_context=touchpoint.trigger_context.model_dump(),
                message_content=touchpoint.message_content,
                delivery_at=touchpoint.delivery_at,
                delivered=touchpoint.delivered,
                delivered_at=touchpoint.delivered_at,
                skipped=touchpoint.skipped,
                skip_reason=touchpoint.skip_reason,
            )
            self.session.add(db_touchpoint)
            await self.session.flush()
            return touchpoint
        else:
            # Using individual parameters
            if user_id is None or trigger_type is None or delivery_at is None:
                raise ValueError("user_id, trigger_type, and delivery_at are required")

            touchpoint_id = uuid4()
            db_touchpoint = ScheduledTouchpointDB(
                id=touchpoint_id,
                user_id=user_id,
                trigger_type=trigger_type.value,
                trigger_context=trigger_context or {},
                message_content=message_content,
                delivery_at=delivery_at,
                delivered=False,
                skipped=False,
            )
            self.session.add(db_touchpoint)
            await self.session.flush()

            # Return Pydantic model
            return self._to_pydantic(db_touchpoint)

    async def get(self, touchpoint_id: UUID) -> ScheduledTouchpoint | None:
        """Get a touchpoint by ID.

        Args:
            touchpoint_id: UUID of the touchpoint.

        Returns:
            ScheduledTouchpoint or None if not found.
        """
        result = await self.session.execute(
            select(ScheduledTouchpointDB).where(ScheduledTouchpointDB.id == touchpoint_id)
        )
        db_touchpoint = result.scalar_one_or_none()
        if db_touchpoint is None:
            return None
        return self._to_pydantic(db_touchpoint)

    async def get_due_touchpoints(self, limit: int = 50) -> list[ScheduledTouchpoint]:
        """Get touchpoints that are due for delivery.

        Args:
            limit: Maximum number of touchpoints to return.

        Returns:
            List of due touchpoints ordered by delivery_at.
        """
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(ScheduledTouchpointDB)
            .where(
                and_(
                    ScheduledTouchpointDB.delivered.is_(False),
                    ScheduledTouchpointDB.skipped.is_(False),
                    ScheduledTouchpointDB.delivery_at <= now,
                )
            )
            .order_by(ScheduledTouchpointDB.delivery_at)
            .limit(limit)
        )
        return [self._to_pydantic(tp) for tp in result.scalars().all()]

    async def get_user_touchpoints(
        self,
        user_id: UUID,
        since: datetime | None = None,
        include_delivered: bool = False,
    ) -> list[ScheduledTouchpoint]:
        """Get touchpoints for a user.

        Args:
            user_id: User's UUID.
            since: Only include touchpoints created after this time.
            include_delivered: Whether to include already-delivered touchpoints.

        Returns:
            List of touchpoints for the user.
        """
        conditions = [ScheduledTouchpointDB.user_id == user_id]

        if since is not None:
            conditions.append(ScheduledTouchpointDB.created_at >= since)

        if not include_delivered:
            conditions.append(ScheduledTouchpointDB.delivered.is_(False))
            conditions.append(ScheduledTouchpointDB.skipped.is_(False))

        result = await self.session.execute(
            select(ScheduledTouchpointDB)
            .where(and_(*conditions))
            .order_by(ScheduledTouchpointDB.delivery_at)
        )
        return [self._to_pydantic(tp) for tp in result.scalars().all()]

    async def get_recent_touchpoints(
        self,
        user_id: UUID,
        since: datetime | None = None,
        hours: float = 24.0,
        exclude_id: UUID | None = None,
    ) -> list[ScheduledTouchpoint]:
        """Get recent touchpoints for deduplication check.

        Args:
            user_id: User's UUID.
            since: Look back period start time.
            hours: Look back period in hours (used if since not provided).
            exclude_id: Optional touchpoint ID to exclude from results.

        Returns:
            List of touchpoints in the time window.
        """
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(hours=hours)

        touchpoints = await self.get_user_touchpoints(
            user_id=user_id,
            since=since,
            include_delivered=True,
        )

        if exclude_id:
            touchpoints = [tp for tp in touchpoints if tp.touchpoint_id != exclude_id]

        return touchpoints

    async def mark_delivered(self, touchpoint_id: UUID) -> ScheduledTouchpoint | None:
        """Mark a touchpoint as delivered.

        Args:
            touchpoint_id: UUID of the touchpoint.

        Returns:
            Updated touchpoint or None if not found.
        """
        result = await self.session.execute(
            select(ScheduledTouchpointDB).where(ScheduledTouchpointDB.id == touchpoint_id)
        )
        db_touchpoint = result.scalar_one_or_none()
        if db_touchpoint is None:
            return None

        db_touchpoint.delivered = True
        db_touchpoint.delivered_at = datetime.now(timezone.utc)
        await self.session.flush()
        return self._to_pydantic(db_touchpoint)

    async def mark_skipped(
        self,
        touchpoint_id: UUID,
        reason: str,
    ) -> ScheduledTouchpoint | None:
        """Mark a touchpoint as strategically skipped.

        Args:
            touchpoint_id: UUID of the touchpoint.
            reason: Reason for skipping.

        Returns:
            Updated touchpoint or None if not found.
        """
        result = await self.session.execute(
            select(ScheduledTouchpointDB).where(ScheduledTouchpointDB.id == touchpoint_id)
        )
        db_touchpoint = result.scalar_one_or_none()
        if db_touchpoint is None:
            return None

        db_touchpoint.skipped = True
        db_touchpoint.skip_reason = reason
        await self.session.flush()
        return self._to_pydantic(db_touchpoint)

    async def mark_failed(
        self,
        touchpoint_id: UUID,
    ) -> ScheduledTouchpoint | None:
        """Mark a touchpoint delivery as failed (for retry).

        Args:
            touchpoint_id: UUID of the touchpoint.

        Returns:
            Updated touchpoint or None if not found.
        """
        result = await self.session.execute(
            select(ScheduledTouchpointDB).where(ScheduledTouchpointDB.id == touchpoint_id)
        )
        db_touchpoint = result.scalar_one_or_none()
        if db_touchpoint is None:
            return None

        # Increment attempt counter (add column if needed)
        # For now, just push delivery time forward for retry
        db_touchpoint.delivery_at = datetime.now(timezone.utc) + timedelta(minutes=5)
        await self.session.flush()
        return self._to_pydantic(db_touchpoint)

    async def delete(self, touchpoint_id: UUID) -> bool:
        """Delete a touchpoint.

        Args:
            touchpoint_id: UUID of the touchpoint.

        Returns:
            True if deleted, False if not found.
        """
        result = await self.session.execute(
            select(ScheduledTouchpointDB).where(ScheduledTouchpointDB.id == touchpoint_id)
        )
        db_touchpoint = result.scalar_one_or_none()
        if db_touchpoint is None:
            return False

        await self.session.delete(db_touchpoint)
        await self.session.flush()
        return True

    async def count_pending(self, user_id: UUID | None = None) -> int:
        """Count pending touchpoints.

        Args:
            user_id: Optional user to filter by.

        Returns:
            Count of pending touchpoints.
        """
        from sqlalchemy import func

        conditions = [
            ScheduledTouchpointDB.delivered.is_(False),
            ScheduledTouchpointDB.skipped.is_(False),
        ]

        if user_id is not None:
            conditions.append(ScheduledTouchpointDB.user_id == user_id)

        result = await self.session.execute(
            select(func.count()).select_from(ScheduledTouchpointDB).where(and_(*conditions))
        )
        return result.scalar_one()

    def _to_pydantic(self, db_model: ScheduledTouchpointDB) -> ScheduledTouchpoint:
        """Convert database model to Pydantic model.

        Args:
            db_model: SQLAlchemy model instance.

        Returns:
            ScheduledTouchpoint Pydantic model.
        """
        trigger_context_data = db_model.trigger_context or {}
        trigger_context = TriggerContext(
            trigger_type=TriggerType(db_model.trigger_type),
            **{k: v for k, v in trigger_context_data.items() if k != "trigger_type"},
        )

        return ScheduledTouchpoint(
            touchpoint_id=db_model.id,
            user_id=db_model.user_id,
            trigger_type=TriggerType(db_model.trigger_type),
            trigger_context=trigger_context,
            message_content=db_model.message_content,
            delivery_at=db_model.delivery_at,
            delivered=db_model.delivered,
            delivered_at=db_model.delivered_at,
            skipped=db_model.skipped,
            skip_reason=db_model.skip_reason,
            created_at=db_model.created_at,
        )
