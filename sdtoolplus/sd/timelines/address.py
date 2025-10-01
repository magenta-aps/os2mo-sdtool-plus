# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from typing import cast
from uuid import UUID

from async_lru import alru_cache
from fastramqpi.os2mo_dar_client import AsyncDARClient

from sdtoolplus.addresses import logger
from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitPostalAddress
from sdtoolplus.models import combine_intervals


@alru_cache()
async def _get_dar_address(dar_client: AsyncDARClient, address: str) -> UUID | None:
    try:
        r = await dar_client.cleanse_single(address)
        value = r["id"]
        logger.debug("Found address in DAR", dar_uuid_address=value)
        return value
    except ValueError:
        logger.warning("No DAR address match", addr=address)
        return None
    except Exception as error:
        # This will happen when DAR is occasionally down. In this case,
        # the OU event fails and will be retried later.
        logger.error("Failed to get DAR address", addr=address)
        raise error


async def sd_postal_dar_address_strategy(
    sd_postal_address_timeline: Timeline[UnitPostalAddress],
) -> Timeline[UnitPostalAddress]:
    logger.info("Getting DAR address timeline")

    dar_client = AsyncDARClient()

    dar_uuid_intervals = []
    async with dar_client:
        for interval in sd_postal_address_timeline.intervals:
            logger.debug("Processing postal address interval", interval=interval.dict())

            interval_value = cast(str, interval.value)  # To make mypy happy...
            dar_uuid_address = await _get_dar_address(dar_client, interval_value)

            if dar_uuid_address is None:
                continue

            dar_uuid_intervals.append(
                UnitPostalAddress(
                    start=interval.start,
                    end=interval.end,
                    value=str(dar_uuid_address),
                )
            )

    desired_address_timeline = Timeline[UnitPostalAddress](
        intervals=combine_intervals(tuple(dar_uuid_intervals)),
    )

    logger.debug(
        "Desired DAR address timeline",
        desired_address_timeline=desired_address_timeline.dict(),
    )

    return desired_address_timeline


async def sd_postal_address_strategy(
    settings: SDToolPlusSettings,
    sd_postal_address_timeline: Timeline[UnitPostalAddress],
) -> Timeline[UnitPostalAddress]:
    """
    Strategy/state pattern for getting the SD postal address timeline based on
    the settings, i.e. whether to use text addresses or DAR (UUID) addresses or
    something else (the latter is not yet implemented).
    """
    if settings.use_dar_addresses:
        return await sd_postal_dar_address_strategy(sd_postal_address_timeline)
    return sd_postal_address_timeline
