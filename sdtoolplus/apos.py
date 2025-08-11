# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import asyncio
import json
from datetime import date
from typing import Any

import structlog
from sdclient.exceptions import SDRootElementNotFound
from sdclient.requests import GetEmploymentChangedRequest

from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.depends import GraphQLClient
from sdtoolplus.depends import SDClient
from sdtoolplus.mo.timeline import get_mo_engagements
from sdtoolplus.mo.timeline import timeline_interval_to_mo_validity
from sdtoolplus.models import Engagement
from sdtoolplus.models import EngagementTimeline
from sdtoolplus.sd.timeline import get_employment_timeline

logger = structlog.stdlib.get_logger()


def _engagement_timeline_to_json(
    engagement: Engagement,
    sd_eng_timeline: EngagementTimeline,
) -> list[dict[str, str]]:
    """
    Returns an engagement dict like this:
    [
        {
            "sd_unit": "29356454-fa40-48a3-b6b1-05732b3ad652",
            "from": "2014-07-10",
            "to": "2020-12-31",
        },
        {
            "sd_unit": "1f52cffa-21b4-4aa7-b092-a94c19607b9f",
            "from": "2021-07-10",
            "to": "None",
        },
    ]
    """

    eng_sd_units = []
    for sd_unit in sd_eng_timeline.eng_unit.intervals:
        mo_validity = timeline_interval_to_mo_validity(sd_unit.start, sd_unit.end)

        eng_sd_units.append(
            {
                "sd_unit": str(sd_unit.value),
                "from": mo_validity.from_.strftime("%Y-%m-%d"),
                "to": mo_validity.to.strftime("%Y-%m-%d")
                if mo_validity.to is not None
                else "None",
            }
        )

    return eng_sd_units


async def json_engagements(
    sd_client: SDClient,
    gql_client: GraphQLClient,
    settings: SDToolPlusSettings,
    cpr: str | None = None,
) -> None:
    """
    Generate a CSV file with all MO engagements and their SD unit placement
    for the entire timeline. The data is stored in a local CSV file to be used
    by the APOS importer.
    """
    logger.info("Generating engagement CSV file for the APOS importer")

    try:
        with open("/tmp/engagements.json") as fp:
            engagements: dict[str, Any] = json.load(fp)
    except FileNotFoundError:
        engagements = {"engagements": dict()}

    mo_engagements = []
    next_cursor = engagements.get("next_cursor")
    while True:
        next_mo_engagements, next_cursor = await get_mo_engagements(
            gql_client=gql_client,
            settings=settings,
            next_cursor=next_cursor,
            cpr=cpr,
        )

        mo_engagements.extend(next_mo_engagements)
        logger.info("Number of engagements processed", n=len(mo_engagements))

        # Get the SD timeline for each engagement
        for eng in next_mo_engagements:
            logger.info("Getting SD engagement timeline", engagement=eng)

            try:
                r_employment = await asyncio.to_thread(
                    sd_client.get_employment_changed,
                    GetEmploymentChangedRequest(
                        InstitutionIdentifier=eng.institution_identifier,
                        PersonCivilRegistrationIdentifier=eng.cpr,
                        EmploymentIdentifier=eng.employment_identifier,
                        ActivationDate=date.min,
                        DeactivationDate=date.max,
                        DepartmentIndicator=True,
                        EmploymentStatusIndicator=True,
                        ProfessionIndicator=True,
                        WorkingTimeIndicator=True,
                        UUIDIndicator=True,
                    ),
                )
            except SDRootElementNotFound as error:
                logger.warning("Could not find engagement in SD", eng=eng, error=error)
                continue
            except Exception as error:
                logger.error(
                    "Failed to get SD engagement timeline", eng=eng, error=error
                )
                with open("/tmp/engagements.json", "w") as fp:
                    json.dump(engagements, fp)
                raise error

            sd_eng_timeline = await get_employment_timeline(r_employment)
            eng_list = _engagement_timeline_to_json(eng, sd_eng_timeline)

            eng_key = (
                f"{eng.institution_identifier},{eng.cpr},{eng.employment_identifier}"
            )
            engagements["engagements"][eng_key] = eng_list

        engagements["next_cursor"] = next_cursor

        if next_cursor is None:
            break

    with open("/tmp/engagements.json", "w") as fp:
        json.dump(engagements, fp)

    logger.info("Done generating engagement CSV file for the APOS importer")
