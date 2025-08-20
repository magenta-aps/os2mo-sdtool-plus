# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import asyncio
import json
from datetime import date
from datetime import datetime
from pathlib import Path
from typing import Any

import click
import structlog
from fastramqpi.ra_utils.asyncio_utils import gather_with_concurrency
from pydantic import BaseSettings
from sdclient.client import SDClient
from sdclient.requests import GetEmploymentChangedAtDateRequest
from sdclient.requests import GetEmploymentChangedRequest
from sdclient.responses import GetEmploymentChangedAtDateResponse

from scripts.sd_engagement_json import _engagement_timeline_to_json
from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
from sdtoolplus.sd.timeline import get_employment_timeline

logger = structlog.stdlib.get_logger()

BASE_START_DATE = datetime(1970, 1, 1)


class ScriptSettings(BaseSettings):
    mo_subtree_paths_for_root: dict[str, list[OrgUnitUUID]] | None = None


async def get_changed_employments(
    sd_client: SDClient, institution_identifier: str, since: datetime
) -> GetEmploymentChangedAtDateResponse:
    return await asyncio.to_thread(
        sd_client.get_employment_changed_at_date,
        GetEmploymentChangedAtDateRequest(
            InstitutionIdentifier=institution_identifier,
            ActivationDate=since.date(),
            ActivationTime=since.time(),
            DeactivationDate=date.max,
        ),
    )


async def lookup_employment_timeline(
    sd_client: SDClient,
    institution_identifier: str,
    cpr: str,
    employment_identifier: str,
):
    r_employment = await asyncio.to_thread(
        sd_client.get_employment_changed,
        GetEmploymentChangedRequest(
            InstitutionIdentifier=institution_identifier,
            PersonCivilRegistrationIdentifier=cpr,
            EmploymentIdentifier=employment_identifier,
            ActivationDate=date.min,
            DeactivationDate=date.max,
            DepartmentIndicator=True,
            EmploymentStatusIndicator=True,
            ProfessionIndicator=True,
            WorkingTimeIndicator=True,
            UUIDIndicator=True,
        ),
    )
    sd_eng_timeline = get_employment_timeline(r_employment)
    eng_list = _engagement_timeline_to_json(sd_eng_timeline)
    return eng_list


@click.command()
@click.option(
    "--username",
    envvar="SD_USERNAME",
    required=True,
    help="SD username",
)
@click.option(
    "--password",
    envvar="SD_PASSWORD",
    required=True,
    help="SD password",
)
@click.option(
    "--file",
    "filepath",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="File to update",
)
@click.option(
    "--since",
    type=click.DateTime(),
    required=True,
    help="Update file with engagements since this date",
)
def main(
    username: str,
    password: str,
    filepath: Path,
    since: datetime,
):
    logger.info("Generating engagement JSON file for the APOS importer")

    with open(filepath) as fp:
        engagements: dict[str, Any] = json.load(fp)

    settings = ScriptSettings()
    assert settings.mo_subtree_paths_for_root is not None
    institution_identifiers = settings.mo_subtree_paths_for_root.keys()

    sd_client = SDClient(username, password)

    for institution_identifier in institution_identifiers:
        logger.info(
            "Processing institution", institution_identifier=institution_identifier
        )

        changed_employments = asyncio.run(
            get_changed_employments(
                sd_client=sd_client,
                institution_identifier=institution_identifier,
                since=since,
            )
        )

        tasks = []
        keys = []
        for person in changed_employments.Person:
            for eng in person.Employment:
                keys.append(
                    f"{institution_identifier},{person.PersonCivilRegistrationIdentifier},{eng.EmploymentIdentifier}"
                )
                tasks.append(
                    lookup_employment_timeline(
                        sd_client=sd_client,
                        institution_identifier=institution_identifier,
                        cpr=person.PersonCivilRegistrationIdentifier,
                        employment_identifier=eng.EmploymentIdentifier,
                    )
                )

        timelines = asyncio.run(gather_with_concurrency(5, *tasks))

        for eng_key, timeline in zip(keys, timelines):
            engagements[eng_key] = timeline

    output_file = filepath.parent.joinpath(f"{filepath.stem}-patched.json")
    with open(output_file, "w") as fp:
        json.dump(engagements, fp)


if __name__ == "__main__":
    main()
