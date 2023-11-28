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
from uuid import UUID

import structlog
from fastapi import FastAPI
from fastapi import Request
from fastramqpi.metrics import dipex_last_success_timestamp  # a Prometheus `Gauge`
from prometheus_fastapi_instrumentator import Instrumentator

from .app import App
from .config import SDToolPlusSettings
from .tree_tools import tree_as_string


logger = structlog.get_logger()


def create_app(**kwargs) -> FastAPI:
    settings = SDToolPlusSettings()
    app = FastAPI(sdtoolplus=App(settings))
    Instrumentator().instrument(app).expose(app)

    @app.get("/")
    async def index() -> dict[str, str]:
        return {"name": "sdtoolplus"}

    @app.get("/tree/mo")
    async def print_mo_tree(request: Request) -> str:
        """
        For debugging problems. Prints the part of the MO tree that
        should be compared to the SD tree.
        """
        sdtoolplus: App = request.app.extra["sdtoolplus"]
        mo_tree = sdtoolplus.get_mo_tree()
        return tree_as_string(mo_tree)

    @app.get("/tree/sd")
    async def print_sd_tree(request: Request) -> str:
        """
        For debugging problems. Prints the SD tree.
        """
        sdtoolplus: App = request.app.extra["sdtoolplus"]
        sd_tree = sdtoolplus.get_sd_tree()
        return tree_as_string(sd_tree)

    @app.post("/trigger")
    async def trigger(
        request: Request, org_unit: UUID | None = None, dry_run: bool = False
    ) -> list[dict]:
        logger.info("Starting run", org_unit=str(org_unit), dry_run=dry_run)

        sdtoolplus: App = request.app.extra["sdtoolplus"]
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
        dipex_last_success_timestamp.set_to_current_time()

        logger.info("Run completed!")

        return results

    return app
