# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import asyncio
from datetime import date

import structlog
from sdclient.requests import GetEmploymentChangedRequest

from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.depends import GraphQLClient
from sdtoolplus.depends import SDClient
from sdtoolplus.mo.timeline import get_all_mo_engagements
from sdtoolplus.mo.timeline import timeline_interval_to_mo_validity
from sdtoolplus.models import Engagement
from sdtoolplus.models import EngagementTimeline
from sdtoolplus.sd.timeline import get_employment_timeline

logger = structlog.stdlib.get_logger()


def _engagement_timeline_to_csv_line(
    engagement: Engagement,
    sd_eng_timeline: EngagementTimeline,
) -> list[str]:
    prefix_eng_str = (
        f"{engagement.institution_identifier}||"
        f"{engagement.cpr}||"
        f"{engagement.employment_identifier}"
    )

    eng_sd_units = []
    for sd_unit in sd_eng_timeline.eng_unit.intervals:
        mo_validity = timeline_interval_to_mo_validity(
            sd_unit.start, sd_unit.end
        )

        eng_sd_units.append(
            f"{prefix_eng_str}||{str(sd_unit.value)}||{mo_validity.from_.strftime('%Y-%m-%d')}||{mo_validity.to.strftime('%Y-%m-%d') if mo_validity.to is not None else 'None'}\n"
        )

    return eng_sd_units


async def csv_engagements(
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

    mo_engagements = await get_all_mo_engagements(
        gql_client=gql_client,
        settings=settings,
        cpr=cpr,
    )

    # Get the SD timeline for each engagement
    all_csv_lines = []
    for eng in mo_engagements:
        logger.info("Getting SD engagement timeline", engagement=eng)

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

        sd_eng_timeline = await get_employment_timeline(r_employment)
        csv_lines = _engagement_timeline_to_csv_line(eng, sd_eng_timeline)

        all_csv_lines.extend(csv_lines)

    # Remove "\n" for the last line
    all_csv_lines[-1] = all_csv_lines[-1][:-1]

    logger.info("Writing CSV file")
    with open("/tmp/engagements.csv", "w") as fp:
        fp.writelines(all_csv_lines)

    logger.info("Done generating engagement CSV file for the APOS importer")
