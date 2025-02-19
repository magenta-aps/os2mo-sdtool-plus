# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from sqlalchemy import Engine
from sqlalchemy import create_engine

from sdtoolplus.config import SDToolPlusSettings


def get_db_url(settings: SDToolPlusSettings) -> str:
    return f"postgresql+psycopg2://{settings.db_user}:{settings.db_password.get_secret_value()}@{settings.db_host}/{settings.db_name}"


def get_engine(settings: SDToolPlusSettings) -> Engine:
    return create_engine(get_db_url(settings), pool_pre_ping=True)
