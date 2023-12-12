# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from enum import Enum
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy import desc
from sqlalchemy import Engine
from sqlalchemy import select
from sqlalchemy.orm import Session

from sdtoolplus.db.models import RunDB


logger = structlog.get_logger()


class Status(Enum):
    COMPLETED = "completed"
    RUNNING = "running"


def get_status(engine: Engine) -> Status:
    with Session(engine) as session:
        statement = select(RunDB.status).order_by(desc(RunDB.id)).limit(1)
        status = session.execute(statement).scalar_one_or_none()
        return Status(status) if status is not None else Status.COMPLETED


def persist_status(engine: Engine, status: Status) -> None:
    with Session(engine) as session:
        run = RunDB(
            timestamp=datetime.now(tz=ZoneInfo("Europe/Copenhagen")),
            status=status.value,
        )
        session.add(run)
        session.commit()
