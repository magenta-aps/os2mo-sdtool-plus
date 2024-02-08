# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
"""
To run:

    $ cd os2mo-sdtool-plus
    $ export MORA_BASE=http://localhost:5000
    $ export AUTH_SERVER=...
    $ export CLIENT_SECRET=...
    $ poetry run docker/start.sh
"""
from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter
from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
from fastramqpi.main import FastRAMQPI
from fastramqpi.metrics import dipex_last_success_timestamp  # a Prometheus `Gauge`
from sqlalchemy import Engine
from starlette.status import HTTP_200_OK
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from .app import App
from .config import SDToolPlusSettings
from .db.engine import get_engine
from .db.rundb import get_status
from .db.rundb import persist_status
from .db.rundb import Status
from .tree_tools import tree_as_string


logger = structlog.get_logger()


def run_db_start_operations(
    engine: Engine, dry_run: bool, response: Response
) -> dict | None:
    logger.info("Checking RunDB status...")
    status_last_run = get_status(engine)
    if not status_last_run == Status.COMPLETED:
        logger.warn("Previous run did not complete successfully!")
        response.status_code = HTTP_500_INTERNAL_SERVER_ERROR
        return {"msg": "Previous run did not complete successfully!"}
    logger.info("Previous run completed successfully")

    if not dry_run:
        persist_status(engine, Status.RUNNING)

    return None


def run_db_end_operations(engine: Engine, dry_run: bool) -> None:
    if not dry_run:
        persist_status(engine, Status.COMPLETED)
    dipex_last_success_timestamp.set_to_current_time()


def create_fastramqpi(**kwargs: Any) -> FastRAMQPI:
    settings = kwargs.get("settings") or SDToolPlusSettings()

    fastramqpi = FastRAMQPI(
        application_name="os2mo-sdtool-plus",
        settings=settings.fastramqpi,
    )
    fastramqpi.add_context(settings=settings)

    sdtoolplus: App = App(settings)
    engine = get_engine(settings)

    fastapi_router = APIRouter()

    @fastapi_router.get("/tree/mo")
    async def print_mo_tree(request: Request) -> str:
        """
        For debugging problems. Prints the part of the MO tree that
        should be compared to the SD tree.
        """
        mo_tree = sdtoolplus.get_mo_tree()
        return tree_as_string(mo_tree)

    @fastapi_router.get("/tree/sd")
    async def print_sd_tree(request: Request) -> str:
        """
        For debugging problems. Prints the SD tree.
        """
        sd_tree = sdtoolplus.get_sd_tree()
        return tree_as_string(sd_tree)

    @fastapi_router.post("/trigger", status_code=HTTP_200_OK)
    async def trigger(
        response: Response,
        org_unit: UUID | None = None,
        dry_run: bool = False,
    ) -> list[dict] | dict:
        logger.info("Starting run", org_unit=str(org_unit), dry_run=dry_run)

        run_db_start_operations_resp = run_db_start_operations(
            engine, dry_run, response
        )
        if run_db_start_operations_resp is not None:
            return run_db_start_operations_resp

        results: list[dict] = [
            {
                "type": mutation.__class__.__name__,
                "unit": repr(org_unit_node),
                "mutation_result": str(result),
            }
            for org_unit_node, mutation, result in sdtoolplus.execute(
                org_unit=org_unit, dry_run=dry_run
            )
        ]
        logger.info("Finished adding or updating org unit objects")

        run_db_end_operations(engine, dry_run)
        logger.info("Run completed!")

        return results

    app = fastramqpi.get_app()
    app.include_router(fastapi_router)

    return fastramqpi


def create_app(**kwargs: Any) -> FastAPI:
    fastramqpi = create_fastramqpi(**kwargs)
    return fastramqpi.get_app()
