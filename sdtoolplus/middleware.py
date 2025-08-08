# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from uuid import uuid4

import structlog.stdlib
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bound_contextvars

logger = structlog.stdlib.get_logger()


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = str(uuid4())
        with bound_contextvars(request_id=req_id):
            return await call_next(request)


class ExceptionLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as error:
            logger.exception("Uncaught exception", exc_info=error)
            raise error
