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
import dataclasses

from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
from fastramqpi.metrics import dipex_last_success_timestamp  # a Prometheus `Gauge`
from prometheus_fastapi_instrumentator import Instrumentator

from .app import App
from .config import SDToolPlusSettings


def create_app(**kwargs) -> FastAPI:
    settings = SDToolPlusSettings()
    app = FastAPI(sdtoolplus=App(settings))
    Instrumentator().instrument(app).expose(app)

    @app.get("/")
    async def index() -> dict[str, str]:
        return {"name": "sdtoolplus"}

    @app.post("/trigger")
    async def trigger(request: Request, response: Response) -> list[dict]:
        sdtoolplus: App = request.app.extra["sdtoolplus"]
        results: list[dict] = [
            {
                "description": str(operation),
                "type": operation.__class__.__name__,
                "data": dataclasses.asdict(operation),
                "mutation_result": str(result),
                "fix_departments_result": str(fix_departments_result),
            }
            for operation, mutation, result, fix_departments_result in sdtoolplus.execute()
        ]
        dipex_last_success_timestamp.set_to_current_time()
        return results

    @app.post("/trigger/dry")
    async def trigger_dry(request: Request, response: Response) -> list[dict]:
        sdtoolplus: App = request.app.extra["sdtoolplus"]
        results: list[dict] = [
            {
                "description": str(operation),
                "type": operation.__class__.__name__,
                "data": dataclasses.asdict(operation),
            }
            for operation, mutation in sdtoolplus.execute_dry()
        ]
        return results

    return app
