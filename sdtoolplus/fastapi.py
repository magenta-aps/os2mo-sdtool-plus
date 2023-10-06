# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
from prometheus_fastapi_instrumentator import Instrumentator

from .app import App
from .tree_diff_executor import TreeDiffExecutor


def create_app(**kwargs) -> FastAPI:
    app = FastAPI(sdtoolplus=App())
    Instrumentator().instrument(app).expose(app)

    @app.get("/")
    async def index() -> dict[str, str]:
        return {"name": "sdtoolplus"}

    @app.post("/trigger")
    async def trigger(request: Request, response: Response) -> list[dict]:
        sdtoolplus: App = request.app.extra["sdtoolplus"]
        executor: TreeDiffExecutor = sdtoolplus.get_tree_diff_executor()
        results: list[dict] = [
            {"operation": str(operation), "result": str(result)}
            for operation, mutation, result in executor.execute()
        ]
        return results

    return app
