"""record when a task was completed, and backfill an estimate

Revision ID: a1c7f2e93b40
Revises: 3263ecb5dcb5
Create Date: 2026-09-01 13:10:00.000000

updated_at could not answer "when was this finished". Editing the title of a
done task moves it, and so does reopening and re-closing one, so any throughput
number built on it counts edits as completions.

The backfill sets completed_at = updated_at for tasks already done, which is a
guess: for most it is close, for any that were edited after closing it is late,
and there is no way to recover the real date. completed_at_estimated marks every
one of those rows so a chart can say which part of itself is a guess rather than
presenting all of it as measurement. Anyone cloning this repo fresh has no
backfilled rows at all and gets exact data from the first task they close.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1c7f2e93b40"
down_revision: str | None = "3263ecb5dcb5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "tasks",
        sa.Column(
            "completed_at_estimated",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    # The enum is stored by member name, which happens to equal the value here.
    op.execute(
        """
        UPDATE tasks
           SET completed_at = updated_at,
               completed_at_estimated = true
         WHERE status = 'done'
           AND completed_at IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("tasks", "completed_at_estimated")
    op.drop_column("tasks", "completed_at")
