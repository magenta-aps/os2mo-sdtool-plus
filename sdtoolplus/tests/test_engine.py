# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from sqlalchemy import Engine

from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.db.engine import get_db_url
from sdtoolplus.db.engine import get_engine


def test_get_db_url(sdtoolplus_settings: SDToolPlusSettings):
    # Act
    url = get_db_url(sdtoolplus_settings)

    # Assert
    assert url == "postgresql+psycopg2://sdtool_plus:secret@sd-db/sdtool_plus"


def test_get_engine(sdtoolplus_settings: SDToolPlusSettings):
    # Act
    engine = get_engine(sdtoolplus_settings)

    # Assert
    assert isinstance(engine, Engine)
    assert str(engine.url) == "postgresql+psycopg2://sdtool_plus:***@sd-db/sdtool_plus"
