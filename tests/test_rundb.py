# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from sqlalchemy import create_engine

from sdtoolplus.db.models import Base
from sdtoolplus.db.rundb import delete_last_run
from sdtoolplus.db.rundb import get_status
from sdtoolplus.db.rundb import persist_status
from sdtoolplus.db.rundb import Status


def test_persist_and_get_status():
    # Arrange
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    # Act
    persist_status(engine, Status.COMPLETED)
    persist_status(engine, Status.RUNNING)
    status = get_status(engine)

    # Assert
    assert status == Status.RUNNING


def test_status_is_completed_for_empty_table():
    # Arrange
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    # Act
    status = get_status(engine)

    # Assert
    assert status == Status.COMPLETED


def test_delete_last_run():
    # Arrange
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    persist_status(engine, Status.COMPLETED)
    persist_status(engine, Status.RUNNING)

    # Act
    delete_last_run(engine)

    # Assert
    status = get_status(engine)
    assert status == Status.COMPLETED
