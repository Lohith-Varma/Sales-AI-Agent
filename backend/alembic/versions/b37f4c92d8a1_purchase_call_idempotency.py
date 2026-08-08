"""Link purchases to calls for idempotent sale completion.

Revision ID: b37f4c92d8a1
Revises: a91e6d1f20b4
"""

from typing import Union

from alembic import op
import sqlalchemy as sa

import app.db.base


revision: str = "b37f4c92d8a1"
down_revision: Union[str, None] = "a91e6d1f20b4"
branch_labels: Union[str, tuple[str, ...], None] = None
depends_on: Union[str, tuple[str, ...], None] = None


def upgrade() -> None:
    with op.batch_alter_table("purchases") as batch:
        batch.add_column(sa.Column("call_id", app.db.base.GUID(), nullable=True))
        batch.create_foreign_key("fk_purchases_call_id", "calls", ["call_id"], ["id"])
        batch.create_index("ix_purchases_call_id", ["call_id"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("purchases") as batch:
        batch.drop_index("ix_purchases_call_id")
        batch.drop_constraint("fk_purchases_call_id", type_="foreignkey")
        batch.drop_column("call_id")
