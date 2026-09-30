"""give a project a pre-mortem

Revision ID: d7e2a4b9c1f0
Revises: c4d9e1f27a3b
Create Date: 2026-09-21 12:00:00.000000

abandonment_criteria says when to stop. It does not say what is most likely to
bring that about, and by the time a project is stale enough to ask, the honest
answer is hard to give. The pre-mortem is written first: imagine the project
has failed, say why. Inline text on the row; longer documents are ordinary
uploads under the "premortem" folder and need no schema of their own.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d7e2a4b9c1f0"
down_revision: str | None = "c4d9e1f27a3b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("premortem", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "premortem")
