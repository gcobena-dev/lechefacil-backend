"""Add ANIMAL_CERTIFICATE to the attachments owner type

Revision ID: d4b8e1c7f905
Revises: c9d1e4f7a2b3
Create Date: 2026-09-12 00:00:00.000000

Scans of an animal's paper certificate are stored in `attachments` like every
other file, under their own owner type. Same reason the OCR photos got one in
c0a6f86862f8: the owner type is what keeps them out of the animal's photo
gallery, so no existing query has to learn about them.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4b8e1c7f905"
down_revision: Union[str, Sequence[str], None] = "c9d1e4f7a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_VALUES = ("ANIMAL", "HEALTH_EVENT", "MILK_PRODUCTION_OCR")
NEW_VALUES = (*OLD_VALUES, "ANIMAL_CERTIFICATE")


def upgrade() -> None:
    # `schema` explícito: el search_path del rol que corre las migraciones no
    # siempre incluye `lechefacil`, y start.sh corre con `set -e`.
    op.alter_column(
        "attachments",
        "owner_type",
        existing_type=sa.Enum(*OLD_VALUES, name="ownertype", native_enum=False),
        type_=sa.Enum(*NEW_VALUES, name="ownertype", native_enum=False),
        existing_nullable=False,
        schema="lechefacil",
    )


def downgrade() -> None:
    # The rows would no longer fit the narrowed type, so they go first. The
    # files stay in the bucket; only the records pointing at them are dropped.
    op.execute(
        "DELETE FROM lechefacil.attachments WHERE owner_type = 'ANIMAL_CERTIFICATE'"
    )
    op.alter_column(
        "attachments",
        "owner_type",
        existing_type=sa.Enum(*NEW_VALUES, name="ownertype", native_enum=False),
        type_=sa.Enum(*OLD_VALUES, name="ownertype", native_enum=False),
        existing_nullable=False,
        schema="lechefacil",
    )
