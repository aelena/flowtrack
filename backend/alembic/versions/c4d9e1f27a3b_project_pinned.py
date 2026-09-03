"""let a project be pinned to the home page

Revision ID: c4d9e1f27a3b
Revises: a1c7f2e93b40
Create Date: 2026-09-03 10:00:00.000000

The home page showed the six most recently touched projects and nothing else,
so anything you cared about but had not opened this week fell off it. A pin
keeps a project there regardless, the way GitHub pins repositories to a
profile. It lives on the row, not in the browser, so it follows the data into
backups and onto other machines.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c4d9e1f27a3b"
down_revision: str | None = "a1c7f2e93b40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("projects", "pinned")
