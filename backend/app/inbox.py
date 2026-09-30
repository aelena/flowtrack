"""The clip inbox.

A clip is captured before you know where the idea belongs — that is the whole
point of clipping something off the web — so the clipper must be able to save
without naming a project. `project_id` is NOT NULL, and making it nullable
would mean a migration plus changes to export and backup. A reserved project
does the same job with no schema change.

Matched by name, case-insensitively, and created on first use. Rename it in the
UI and the next clip creates a fresh one; that is recoverable (re-file the clips
and delete the empty project) and cheaper than a column.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Project

INBOX_NAME = "Inbox"

INBOX_DESCRIPTION = (
    "Ideas clipped from the web before they had a home. Re-file a clip under a "
    "real project once you know where it belongs, or delete it. Created "
    "automatically by the FlowTrack Clipper."
)


async def find_inbox_project(db: AsyncSession) -> Project | None:
    """The inbox if it exists, without creating it."""
    result = await db.execute(
        select(Project)
        .where(func.lower(Project.work_name) == INBOX_NAME.lower())
        .order_by(Project.created_at)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def resolve_inbox_project(db: AsyncSession) -> Project:
    """Return the inbox project, creating it the first time a clip needs it."""
    existing = await find_inbox_project(db)
    if existing:
        return existing

    project = Project(work_name=INBOX_NAME, description=INBOX_DESCRIPTION)
    db.add(project)
    try:
        await db.commit()
    except IntegrityError:
        # Nothing enforces uniqueness on work_name, so this is not the usual
        # race guard — it is here so a concurrent create cannot 500 the capture.
        await db.rollback()
        found = await find_inbox_project(db)
        if found:
            return found
        raise
    await db.refresh(project)
    return project
