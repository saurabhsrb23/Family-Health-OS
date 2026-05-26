"""
Adherence calculation service.
Full implementation in Module 8.
Cache invalidation stub used by meals/workouts/measurements routes.
"""
import logging
from datetime import date
from uuid import UUID

from cache.redis_client import cache

logger = logging.getLogger(__name__)


def invalidate_adherence_cache(member_id: UUID, metric_date: date) -> None:
    """
    Invalidate adherence cache for a member on a specific date.
    Called whenever new health data is logged so computed adherence is recalculated.
    """
    date_str = metric_date.isoformat()
    for component in ("nutrition", "strength", "clinical"):
        cache.delete(f"adherence:{member_id}:{component}:{date_str}")
    cache.delete(f"adherence:rolling:{member_id}:nutrition")
    cache.delete(f"adherence:rolling:{member_id}:strength")
    cache.delete(f"adherence:rolling:{member_id}:clinical")
    logger.debug(f"Adherence cache invalidated for member {member_id} on {date_str}")
