# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import asyncio
from datetime import date
from datetime import datetime

import click
import httpx
from fastramqpi.ra_utils.tqdm_wrapper import tqdm
from more_itertools import one
from sdclient.client import SDClient
from sdclient.requests import GetEmploymentChangedRequest
from sdclient.responses import GetEmploymentChangedResponse
from tenacity import retry
from tenacity import stop_after_attempt
from tenacity import wait_fixed

from sdtoolplus.models import EngagementSyncPayload
from sdtoolplus.models import OrgUnitSyncPayload
from sdtoolplus.models import PersonSyncPayload
from sdtoolplus.sd.person import get_all_sd_persons
from sdtoolplus.sd.timeline import get_all_departments

BASE_START_DATE = datetime(1970, 1, 1)


@retry(reraise=True, stop=stop_after_attempt(3), wait=wait_fixed(2))
def httpx_post(url, *args, **kwargs):
    return httpx.post(url=url, *args, **kwargs)


async def get_sd_person_employments(
    sd_client: SDClient,
    institution_identifier: str,
    cpr: str,
) -> GetEmploymentChangedResponse:
    return await asyncio.to_thread(
        sd_client.get_employment_changed,
        GetEmploymentChangedRequest(
            InstitutionIdentifier=institution_identifier,
            PersonCivilRegistrationIdentifier=cpr,
            EmploymentIdentifier=None,
            ActivationDate=date.min,
            DeactivationDate=date.max,
        ),
    )


@click.command()
@click.option(
    "--username",
    "username",
    type=click.STRING,
    envvar="SD_USERNAME",
    required=True,
    help="SD username",
)
@click.option(
    "--password",
    "password",
    type=click.STRING,
    envvar="SD_PASSWORD",
    required=True,
    help="SD password",
)
@click.option(
    "--institution-identifier",
    "institution_identifier",
    type=click.STRING,
    envvar="SD_INSTITUTION_IDENTIFIER",
    required=True,
    help="SD institution identifier",
)
def main(
    username: str,
    password: str,
    institution_identifier: str,
):
    """Trigger a sync of everything in an SD inst to MO"""

    async def trigger_sync_all_persons(
        inst: str,
    ) -> None:
        """
        Sync all persons from SD to MO

        Args:
            gql_client: The GraphQL client
            inst: The institution identifier for which to sync

        Returns:
            Dictionary with status
        """
        persons = await get_all_sd_persons(
            sd_client=sd_client, institution_identifier=inst
        )
        payloads = [
            PersonSyncPayload(institution_identifier=inst, cpr=person.cpr)
            for person in persons
        ]
        # # TODO create events instead
        errors = set()

        for payload in tqdm(payloads):
            res = httpx_post(
                "http://localhost:8000/timeline/sync/person",
                json=payload.dict(),
            )
            if res.status_code != 200:
                errors.add(payload.cpr)
                click.echo(f"Error syncing person: {payload.cpr}, {res.text}")
            employments = await get_sd_person_employments(
                sd_client=sd_client, institution_identifier=inst, cpr=payload.cpr
            )
            for employment in one(employments.Person).Employment:
                employment_payload = EngagementSyncPayload(
                    institution_identifier=inst,
                    cpr=payload.cpr,
                    employment_identifier=employment.EmploymentIdentifier,
                )
                res = httpx_post(
                    "http://localhost:8000/timeline/sync/person",
                    json=employment_payload.dict(),
                )
                if res.status_code != 200:
                    errors.add(payload.cpr)
                    click.echo(
                        f"Error syncing employment for person: {payload.cpr}, {res.text}"
                    )
        click.echo(f"Synced {len(payloads) - len(errors)}/{len(payloads)} successfully")
        click.echo(f"Could not sync the following persons: {errors}")

    async def trigger_sync_all_departments(
        inst: str,
    ) -> None:
        """
        Sync all departments from SD to MO

        Args:
            gql_client: The GraphQL client
            inst: The institution identifier for which to sync

        Returns:
            Dictionary with status
        """
        departments = await get_all_departments(sd_client=sd_client, inst_id=inst)
        # TODO create events instead

        errors = set()
        for d in tqdm(departments):
            payload = OrgUnitSyncPayload(institution_identifier=inst, org_unit=d)
            res = httpx_post(
                "http://localhost:8000/timeline/sync/ou",
                json=payload.dict(),
            )
            if res.status_code != 200:
                errors.add(d)
                click.echo(f"Error syncing department: {d}, {res.text}")
        click.echo(
            f"Synced {len(departments) - len(errors)}/{len(departments)} successfully"
        )
        click.echo(f"Could not sync the following units {errors}")

    sd_client = SDClient(username, password)

    asyncio.run(trigger_sync_all_departments(inst=institution_identifier))
    asyncio.run(trigger_sync_all_persons(inst=institution_identifier))


if __name__ == "__main__":
    main()
