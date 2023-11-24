# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
#
# Mostly copied from https://git.magenta.dk/rammearkitektur/sd-integration/-/blob/master/sdlon/log.py
import logging
from enum import Enum
from typing import Any

import structlog
from structlog.processors import CallsiteParameter


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


def _dont_log_graphql_responses(_: Any, __: str, event_dict: dict) -> dict:
    """Drop logs from `BaseHTTPXTransport._decode_response` (in
    `raclients.graph.transport`), which logs *all* GraphQL responses at DEBUG level.
    (https://git.magenta.dk/rammearkitektur/ra-clients/-/blob/master/raclients/graph/transport.py#L117)
    """
    module: str | None = event_dict.get("module")
    func_name: str | None = event_dict.get("func_name")
    if module == "transport" and func_name in (
        "_decode_response",
        "_construct_payload",
    ):
        raise structlog.DropEvent
    return event_dict


def setup_logging(log_level: LogLevel) -> None:
    log_level_value = logging.getLevelName(log_level.value)
    structlog.configure(
        processors=[
            structlog.processors.CallsiteParameterAdder(
                [CallsiteParameter.MODULE, CallsiteParameter.FUNC_NAME],
            ),
            _dont_log_graphql_responses,  # type: ignore
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level_value),
    )
