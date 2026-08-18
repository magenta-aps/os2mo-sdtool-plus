# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from enum import Enum
from zoneinfo import ZoneInfo

import structlog
from fastapi import Response
from fastramqpi.metrics import dipex_last_success_timestamp  # a Prometheus `Gauge`
from sqlalchemy import Engine
from sqlalchemy import delete
from sqlalchemy import desc
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from sdtoolplus.db.models import RunDB

logger = structlog.stdlib.get_logger()


class Status(Enum):
    COMPLETED = "completed"
    RUNNING = "running"


async def get_status(engine: Engine) -> Status:
    with Session(engine) as session:
        statement = select(RunDB.status).order_by(desc(RunDB.id)).limit(1)
        status = session.execute(statement).scalar_one_or_none()

        # status is only "None" the very first time the application is run
        # and should in this case return "COMPLETED" in order to not abort
        # the run when get_status() is called from main.py
        return Status(status) if status is not None else Status.COMPLETED


async def persist_status(engine: Engine, status: Status) -> None:
    with Session(engine) as session:
        run = RunDB(
            timestamp=datetime.now(tz=ZoneInfo("Europe/Copenhagen")),
            status=status.value,
        )
        session.add(run)
        session.commit()


async def delete_last_run(engine: Engine) -> None:
    with Session(engine) as session:
        last_run = select(RunDB.id).order_by(desc(RunDB.id)).limit(1)
        statement = delete(RunDB).where(RunDB.id == last_run)
        session.execute(statement)
        session.commit()


async def run_db_start_operations(
    engine: Engine, dry_run: bool, response: Response
) -> dict | None:
    if dry_run:
        return None

    logger.info("Checking RunDB status...")
    status_last_run = await get_status(engine)
    if not status_last_run == Status.COMPLETED:
        logger.warn("Previous run did not complete successfully!")
        response.status_code = HTTP_500_INTERNAL_SERVER_ERROR
        return {"msg": "Previous run did not complete successfully!"}
    logger.info("Previous run completed successfully")

    await persist_status(engine, Status.RUNNING)

    return None


async def run_db_end_operations(engine: Engine, dry_run: bool) -> None:
    if not dry_run:
        await persist_status(engine, Status.COMPLETED)
    dipex_last_success_timestamp.set_to_current_time()
