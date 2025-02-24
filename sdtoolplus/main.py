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
from fastapi import BackgroundTasks
from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
from fastramqpi.main import FastRAMQPI
from fastramqpi.metrics import dipex_last_success_timestamp  # a Prometheus `Gauge`
from fastramqpi.os2mo_dar_client import AsyncDARClient
from more_itertools import first
from sdclient.client import SDClient
from sqlalchemy import Engine
from starlette.status import HTTP_200_OK
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from .addresses import AddressFixer
from .app import App
from .config import SDToolPlusSettings
from .db.engine import get_engine
from .db.rundb import Status
from .db.rundb import delete_last_run
from .db.rundb import get_status
from .db.rundb import persist_status
from .depends import GraphQLClient
from .mo.timeline import get_ou_timeline
from .mo_class import MOOrgUnitLevelMap
from .mo_org_unit_importer import OrgUnitUUID
from .sd.timeline import get_department_timeline
from .timeline import update_ou
from .tree_tools import tree_as_string

logger = structlog.get_logger()


def run_db_start_operations(
    engine: Engine, dry_run: bool, response: Response
) -> dict | None:
    if dry_run:
        return None

    logger.info("Checking RunDB status...")
    status_last_run = get_status(engine)
    if not status_last_run == Status.COMPLETED:
        logger.warn("Previous run did not complete successfully!")
        response.status_code = HTTP_500_INTERNAL_SERVER_ERROR
        return {"msg": "Previous run did not complete successfully!"}
    logger.info("Previous run completed successfully")

    persist_status(engine, Status.RUNNING)

    return None


def run_db_end_operations(engine: Engine, dry_run: bool) -> None:
    if not dry_run:
        persist_status(engine, Status.COMPLETED)
    dipex_last_success_timestamp.set_to_current_time()


def background_run(
    settings: SDToolPlusSettings,
    engine: Engine,
    inst_ids: list[str],
    org_unit: UUID | None = None,
    dry_run: bool = False,
) -> None:
    """
    Run org tree sync in background for all institutions.

    Args:
        settings: the SDToolPlusSettings
        engine: the SQLAlchemy DB engine
        inst_ids: list of the SD InstitutionIdentifiers
        org_unit: if not None, only run for this unit
        dry_run: if True, no changes will be written in MO
    """
    sdtoolplus: App = App(settings, first(inst_ids))

    for ii in inst_ids:
        logger.info("Starting background run", inst_id=ii)
        sdtoolplus.set_inst_id(ii)
        for org_unit_node, mutation, result in sdtoolplus.execute(
            org_unit=org_unit, dry_run=dry_run
        ):
            logger.info(
                "Processed unit",
                org_unit_name=org_unit_node.name,
                org_unit_uuid=str(org_unit_node.uuid),
            )

        logger.info("Finished background run", inst_id=ii)

        # Send email notifications for illegal moves
        if settings.email_notifications_enabled and not dry_run:
            sdtoolplus.send_email_notification()

    run_db_end_operations(engine, dry_run)
    logger.info("Run completed!")


def create_fastramqpi(**kwargs: Any) -> FastRAMQPI:
    settings = kwargs.get("settings") or SDToolPlusSettings()

    fastramqpi = FastRAMQPI(
        application_name="os2mo-sdtool-plus",
        settings=settings.fastramqpi,
        graphql_client_cls=GraphQLClient,
        graphql_version=22,
    )
    fastramqpi.add_context(settings=settings)

    engine = get_engine(settings)

    fastapi_router = APIRouter()

    @fastapi_router.get("/tree/mo")
    async def print_mo_tree(request: Request) -> str:
        """
        For debugging problems. Prints the part of the MO tree that
        should be compared to the SD tree.
        """
        sdtoolplus: App = App(settings)
        mo_tree = sdtoolplus.get_mo_tree()
        return tree_as_string(mo_tree)

    @fastapi_router.get("/tree/sd")
    async def print_sd_tree(request: Request) -> str:
        """
        For debugging problems. Prints the SD tree.
        """
        sdtoolplus: App = App(settings)
        mo_org_unit_level_map = MOOrgUnitLevelMap(sdtoolplus.session)
        sd_tree = sdtoolplus.get_sd_tree(mo_org_unit_level_map)
        return tree_as_string(sd_tree)

    @fastapi_router.get("/rundb/status")
    def rundb_get_status() -> int:
        """
        Get the RunDB status and return a job-runner.sh (curl) friendly integer
        status.

        Returns:
            0 if status is "completed", 1 if status is "running" and 3 in case of
            an error.
        """
        try:
            status = get_status(engine)
            return 0 if status == Status.COMPLETED else 1
        except Exception:
            return 3

    @fastapi_router.post("/rundb/delete-last-run")
    def rundb_delete_last_run():
        delete_last_run(engine)
        return {"msg": "Last run deleted"}

    @fastapi_router.post("/trigger", status_code=HTTP_200_OK)
    async def trigger(
        response: Response,
        org_unit: UUID | None = None,
        inst_id: str | None = None,
        dry_run: bool = False,
    ) -> list[dict] | dict:
        logger.info("Starting run", org_unit=str(org_unit), dry_run=dry_run)

        run_db_start_operations_resp = run_db_start_operations(
            engine, dry_run, response
        )
        if run_db_start_operations_resp is not None:
            return run_db_start_operations_resp

        sdtoolplus: App = App(settings, inst_id)

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

        # Send email notifications for illegal moves
        if settings.email_notifications_enabled and not dry_run:
            sdtoolplus.send_email_notification()

        run_db_end_operations(engine, dry_run)
        logger.info("Run completed!")

        return results

    @fastapi_router.post("/trigger-all-inst-ids", status_code=HTTP_200_OK)
    async def trigger_all_inst_ids(
        response: Response,
        background_tasks: BackgroundTasks,
        org_unit: UUID | None = None,
        inst_id: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, str]:
        logger.info("Starting run", org_unit=str(org_unit), dry_run=dry_run)

        run_db_start_operations_resp = run_db_start_operations(
            engine, dry_run, response
        )
        if run_db_start_operations_resp is not None:
            return run_db_start_operations_resp

        if inst_id is not None:
            inst_ids = [inst_id]
        else:
            assert settings.mo_subtree_paths_for_root is not None
            inst_ids = list(settings.mo_subtree_paths_for_root.keys())

        background_tasks.add_task(
            background_run, settings, engine, inst_ids, org_unit, dry_run
        )

        return {"msg": "Org tree sync started in background"}

    @fastapi_router.post("/trigger/addresses", status_code=HTTP_200_OK)
    async def trigger_addresses(
        response: Response,
        gql_client: GraphQLClient,
        org_unit: UUID | None = None,
        inst_id: str | None = None,
        dry_run: bool = False,
    ) -> list[dict] | dict:
        logger.info("Starting address run", org_unit=str(org_unit), dry_run=dry_run)

        run_db_start_operations_resp = run_db_start_operations(
            engine, dry_run, response
        )
        if run_db_start_operations_resp is not None:
            return run_db_start_operations_resp

        addr_fixer = AddressFixer(
            gql_client,
            SDClient(
                settings.sd_username,
                settings.sd_password.get_secret_value(),
            ),
            AsyncDARClient(),
            settings,
            inst_id if inst_id is not None else settings.sd_institution_identifier,
        )

        results: list[dict] = [
            {
                "address_operation": operation.value,
                "address_type": addr.address_type.user_key,
                "unit": repr(org_unit_node),
                "address": addr.value,
            }
            async for operation, org_unit_node, addr in addr_fixer.fix_addresses(
                org_unit, dry_run
            )
        ]
        logger.info("Finished adding or updating org unit objects")

        run_db_end_operations(engine, dry_run)
        logger.info("Run completed!")

        return results

    @fastapi_router.post("/timeline/sync/ou", status_code=HTTP_200_OK)
    async def timeline_sync_ou(
        gql_client: GraphQLClient,
        org_unit: OrgUnitUUID,
        inst_id: str,
        dry_run: bool = False,
    ) -> dict:
        """
        Sync the entire org unit timeline for the given unit.

        Args:
            gql_client: The GraphQL client
            org_unit: The UUID of the org unit to sync.
            inst_id: The SD institution
            dry_run: If true, nothing will be written to MO.

        Returns:
            Dictionary with status
        """

        sd_client = SDClient(
            settings.sd_username,
            settings.sd_password.get_secret_value(),
        )
        sd_unit_timeline = get_department_timeline(sd_client, inst_id, org_unit)

        mo_unit_timeline = await get_ou_timeline(gql_client, org_unit)

        await update_ou(
            gql_client, org_unit, sd_unit_timeline, mo_unit_timeline, dry_run
        )

        return {"msg": "success"}

    app = fastramqpi.get_app()
    app.include_router(fastapi_router)

    return fastramqpi


def create_app(**kwargs: Any) -> FastAPI:
    fastramqpi = create_fastramqpi(**kwargs)
    return fastramqpi.get_app()
