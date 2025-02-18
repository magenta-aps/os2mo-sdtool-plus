# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from typing import Any

from fastapi import FastAPI
from fastapi import Request


# This way of mocking the SD API was taken from the Omada code
def create_app(endpoint: str, api_response: Any) -> FastAPI:
    """This fake SD API is used for both manual and integration tests."""
    app = FastAPI()

    @app.get(f"/sdws/{endpoint}")
    async def get(request: Request) -> dict:
        return api_response

    return app
