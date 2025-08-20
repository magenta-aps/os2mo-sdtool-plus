# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import json
import re
from copy import copy
from datetime import date
from datetime import datetime
from datetime import timezone
from typing import Any

import click
import structlog.stdlib
from more_itertools import last
from sdclient.exceptions import SDRootElementNotFound
from sdclient.requests import GetEmploymentChangedRequest

from sdtoolplus.depends import SDClient
from sdtoolplus.mo.timeline import timeline_interval_to_mo_validity
from sdtoolplus.models import Engagement
from sdtoolplus.models import EngagementTimeline
from sdtoolplus.sd.timeline import get_employment_timeline

REGEX_CPR = re.compile("^\\d{10}$")
logger = structlog.stdlib.get_logger()


def _get_mo_engagements_from_postgres_csv() -> list[Engagement]:
    """
    Get the MO engagements from the CSV file generated directly from the MO
    DB with the script all-engagements.sql. Requires that the generated CSV
    file has been placed in the folder /tmp/engagements.csv. The
    engagements.csv has this format:

    user_key,employee,cpr
    II-12355,8c93f5e5-3ec3-44ce-9bbb-003cc199c82e,urn:dk:cpr:person:0101011234
    ...
    """
    with open("/tmp/engagements.csv") as fp:
        csv_lines = fp.readlines()

    mo_engagements = []
    for csv_line in csv_lines[1:]:
        inst_id_and_emp_id, _, urn = csv_line[:-1].split(",")
        try:
            inst_id, emp_id = inst_id_and_emp_id.split("-")
        except ValueError as error:
            logger.error("CSV line", csv_line=csv_line)
            raise error
        cpr = last(urn.split(":"))
        assert REGEX_CPR.match(cpr)

        mo_engagements.append(
            Engagement(
                institution_identifier=inst_id,
                cpr=cpr,
                employment_identifier=emp_id,
            )
        )

    return mo_engagements


def _engagement_timeline_to_json(
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


def _write_json(sd_engagements: dict[str, Any], filepath: str) -> None:
    with open(filepath, "w") as fp:
        json.dump(sd_engagements, fp)


def _get_eng_key(eng: Engagement) -> str:
    return f"{eng.institution_identifier},{eng.cpr},{eng.employment_identifier}"


@click.command()
@click.option(
    "--username",
    "username",
    envvar="SD_USERNAME",
    required=True,
    help="SD username",
)
@click.option(
    "--password",
    "password",
    envvar="SD_PASSWORD",
    required=True,
    help="SD password",
)
def main(username: str, password: str) -> None:
    """
    Generate a CSV file with all MO engagements and their SD unit placement
    for the entire timeline. The data is stored in a local CSV file to be used
    by the APOS importer.
    """
    logger.info("Generating engagement CSV file for the APOS importer")
    t_start = datetime.now(tz=timezone.utc)

    try:
        with open("/tmp/engagements.json") as fp:
            sd_engagements: dict[str, Any] = json.load(fp)
    except FileNotFoundError:
        sd_engagements = dict()
    logger.info("Already processed engagements", n=len(sd_engagements))

    try:
        with open("/tmp/engagements-not-found.json") as fp:
            sd_engagements_not_found: dict[str, Any] = json.load(fp)
    except FileNotFoundError:
        sd_engagements_not_found = dict()
    logger.info(
        "Already processed engagements (not found)", n=len(sd_engagements_not_found)
    )

    already_processed = copy(sd_engagements)
    already_processed.update(sd_engagements_not_found)

    mo_engagements = _get_mo_engagements_from_postgres_csv()
    mo_engagements = [
        eng for eng in mo_engagements if _get_eng_key(eng) not in already_processed
    ]
    logger.info("Engagements to process", n=len(mo_engagements))

    sd_client = SDClient(username, password)

    # Get the SD timeline for each engagement
    for i, eng in enumerate(mo_engagements):
        logger.info("Getting SD engagement timeline", engagement=eng, i=i)
        eng_key = _get_eng_key(eng)

        try:
            r_employment = sd_client.get_employment_changed(
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
            sd_engagements_not_found[eng_key] = eng.dict()
            continue
        except Exception as error:
            logger.error("Failed to get SD engagement timeline", eng=eng, error=error)
            _write_json(sd_engagements, "/tmp/engagements.json")
            _write_json(sd_engagements_not_found, "/tmp/engagements-not-found.json")
            raise error

        sd_eng_timeline = get_employment_timeline(r_employment)
        eng_list = _engagement_timeline_to_json(sd_eng_timeline)

        sd_engagements[eng_key] = eng_list

        if i % 100 == 0:
            logger.info(
                "Writing JSON", i=i, time=datetime.now(tz=timezone.utc) - t_start
            )
            _write_json(sd_engagements, "/tmp/engagements.json")
            _write_json(sd_engagements_not_found, "/tmp/engagements-not-found.json")

    _write_json(sd_engagements, "/tmp/engagements.json")
    _write_json(sd_engagements_not_found, "/tmp/engagements-not-found.json")

    now = datetime.now(tz=timezone.utc)
    logger.info(
        "Done generating engagement CSV file for the APOS importer",
        time=now - t_start,
    )


if __name__ == "__main__":
    main()
