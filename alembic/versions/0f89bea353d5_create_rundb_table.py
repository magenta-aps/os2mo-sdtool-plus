# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
"""create rundb table

Revision ID: 0f89bea353d5
Revises:
Create Date: 2023-11-30 14:56:26.866561

"""
from typing import Sequence
from typing import Union

from alembic import op  # type: ignore
from sdtoolplus.db.models import RunDB

# revision identifiers, used by Alembic.
revision: str = "0f89bea353d5"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(RunDB.__tablename__, *RunDB.__table__.c)


def downgrade() -> None:
    op.drop_table("rundb")
