# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0

import structlog

from sdtoolplus.config import Mode
from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitId
from sdtoolplus.models import UnitTimeline

logger = structlog.stdlib.get_logger()


def _sd_inst_id_prefix(key: str, inst_id: str) -> str:
    return f"{inst_id}-{key}"


def _prefix_eng_user_key(
    settings: SDToolPlusSettings, user_key: str, inst_id: str
) -> str:
    if settings.mode == Mode.MUNICIPALITY:
        return user_key
    return _sd_inst_id_prefix(user_key, inst_id)


def _split_engagement_user_key(
    settings: SDToolPlusSettings, user_key: str
) -> tuple[str, str]:
    if settings.mode == Mode.MUNICIPALITY:
        return settings.sd_institution_identifier, user_key
    institution_identifier, employment_id = user_key.split("-")
    return institution_identifier, employment_id


def prefix_unit_id_with_inst_id(
    settings: SDToolPlusSettings, unit_timeline: UnitTimeline, inst_id: str
) -> UnitTimeline:
    if settings.mode == Mode.MUNICIPALITY:
        return unit_timeline

    unit_id_intervals = tuple(
        UnitId(
            start=interval.start,
            end=interval.end,
            value=_sd_inst_id_prefix(interval.value, inst_id),  # type: ignore
        )
        for interval in unit_timeline.unit_id.intervals
    )

    prefixed_unit_timeline = UnitTimeline(
        active=unit_timeline.active,
        name=unit_timeline.name,
        unit_id=Timeline[UnitId](intervals=unit_id_intervals),
        unit_level=unit_timeline.unit_level,
        parent=unit_timeline.parent,
    )
    logger.debug(
        "SD timeline with prefixed unit_id", timeline=prefixed_unit_timeline.dict()
    )

    return prefixed_unit_timeline
