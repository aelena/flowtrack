"""Throughput numbers for the dashboard.

Deliberately small. Two questions, both about tasks closed over time: how many
in the last seven days against the seven before, and a weekly series to see the
shape rather than one number in isolation.

Everything here counts `completed_at`, never `updated_at`. See the migration
a1c7f2e93b40 for why that distinction exists at all, and note that rows carried
over by its backfill are flagged: the response says how many of the tasks it
counted have an estimated date, so a chart can mark that part of itself instead
of presenting a guess as a measurement.
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..dependencies import verify_api_key
from ..models import Task, TaskStatus

router = APIRouter(prefix="/api/metrics", tags=["metrics"], dependencies=[Depends(verify_api_key)])

# Enough weeks to see a shape, few enough to read on one line.
DEFAULT_WEEKS = 12
MAX_WEEKS = 52

# Below this, a change in either direction is noise on a personal tracker.
# Two tasks either way in a week says nothing about a trend.
TREND_THRESHOLD = 2


def _trend(current: int, previous: int) -> str:
    """Up, down, or flat, with a dead band.

    A tool used by one person has weeks with three tasks in them. Reporting
    "down 33 percent" for two tasks fewer would be arithmetic pretending to be
    information.
    """
    if abs(current - previous) < TREND_THRESHOLD:
        return "flat"
    return "up" if current > previous else "down"


@router.get("/throughput")
async def throughput(
    weeks: int = Query(DEFAULT_WEEKS, ge=1, le=MAX_WEEKS),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(UTC)
    # Buckets are aligned to day boundaries, so a page opened twice in one
    # afternoon gives the same answer instead of shifting under the reader.
    #
    # They end at the *end* of today, not the start of it. Aligning to midnight
    # this morning put everything completed since then at a negative offset and
    # dropped it: on the first live run, 64 tasks had a completion date and only
    # 45 were counted, and the missing 19 were all closed that day. A dashboard
    # that ignores today's work is worse than one that shows nothing, because
    # nobody checks a number that looks plausible.
    end = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    week_starts = [end - timedelta(days=7 * (i + 1)) for i in range(weeks)]
    window_start = week_starts[-1]

    rows = (
        await db.execute(
            select(Task.completed_at, Task.completed_at_estimated).where(
                Task.status == TaskStatus.done,
                Task.completed_at.isnot(None),
                Task.completed_at >= window_start,
            )
        )
    ).all()

    buckets = [0] * weeks
    estimated_counted = 0
    for completed_at, estimated in rows:
        # Which bucket, counting back from the end of today in seven-day blocks.
        days_ago = (end - completed_at).days
        index = days_ago // 7
        if 0 <= index < weeks:
            buckets[index] += 1
            if estimated:
                estimated_counted += 1

    last_7 = buckets[0]
    previous_7 = buckets[1] if weeks > 1 else 0

    return {
        "last_7_days": last_7,
        "previous_7_days": previous_7,
        "change": last_7 - previous_7,
        "trend": _trend(last_7, previous_7),
        # Oldest week first, which is the direction a chart is drawn in.
        "weeks": [
            {"week_start": week_starts[i].date().isoformat(), "completed": buckets[i]}
            for i in reversed(range(weeks))
        ],
        "estimated_counted": estimated_counted,
        "total_counted": sum(buckets),
    }
