"""fix_attach_unique_constraint_soft_delete

Revision ID: 4d76d7417c55
Revises: a7b8c9d0e1f2
Create Date: 2026-04-05 11:19:18.942129

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d76d7417c55'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ux_attach_owner_pos", "attachments", type_="unique")
    op.execute(
        """
        CREATE UNIQUE INDEX ux_attach_owner_pos
        ON lechefacil.attachments (tenant_id, owner_type, owner_id, "position")
        WHERE deleted_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS lechefacil.ux_attach_owner_pos")
    op.create_unique_constraint(
        "ux_attach_owner_pos",
        "attachments",
        ["tenant_id", "owner_type", "owner_id", "position"],
    )
