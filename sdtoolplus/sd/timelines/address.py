# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from typing import cast

from fastramqpi.os2mo_dar_client import AsyncDARClient

from sdtoolplus.addresses import logger
from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitPostalAddress
from sdtoolplus.models import combine_intervals

DAR_ADDRESS_NOT_FOUND = "DAR address not found"


async def sd_postal_dar_address_strategy(
    sd_postal_address_timeline: Timeline[UnitPostalAddress],
) -> Timeline[UnitPostalAddress]:
    dar_client = AsyncDARClient()

    local_dar_cache: dict[str, str] = dict()

    dar_uuid_intervals = []
    async with dar_client:
        for interval in sd_postal_address_timeline.intervals:
            interval_value = cast(str, interval.value)  # To make mypy happy...
            dar_uuid_address = local_dar_cache.get(interval_value)

            if dar_uuid_address:
                # We have already just looked up the address
                value = (
                    dar_uuid_address
                    if not dar_uuid_address == DAR_ADDRESS_NOT_FOUND
                    else None
                )
            else:
                try:
                    r = await dar_client.cleanse_single(interval_value)
                    value = r["id"]
                    local_dar_cache[interval_value] = value
                except ValueError:
                    logger.warning("No DAR address match", addr=interval_value)
                    value = None
                    local_dar_cache[interval_value] = DAR_ADDRESS_NOT_FOUND
                except Exception as error:
                    # This will happen when DAR is occasionally down. In this case,
                    # the OU event fails and will be retried later.
                    logger.error("Failed to get DAR address", addr=interval.value)
                    raise error

            dar_uuid_intervals.append(
                UnitPostalAddress(
                    start=interval.start,
                    end=interval.end,
                    value=value,
                )
            )

    desired_address_timeline = Timeline[UnitPostalAddress](
        intervals=combine_intervals(tuple(dar_uuid_intervals)),
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
