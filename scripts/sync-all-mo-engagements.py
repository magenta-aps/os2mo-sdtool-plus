# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import csv
from pathlib import Path

# This script is currently necessary due to performance issues with the engagements
# refresh mutator, i.e. calling /timeline/sync/engagement/all/mo will take forever to
# complete.
import click
import httpx
import structlog
from httpx import HTTPStatusError
from more_itertools import last

ENGAGEMENT_SYNC_URL = "http://localhost:8000/timeline/sync/engagement"

logger = structlog.stdlib.get_logger()


@click.command()
@click.option(
    "--engagements-csv-file",
    type=click.Path(exists=True),
    default=Path("/tmp/engagements.csv"),
    help="Path to the CSV file containing the engagements to sync",
)
def main(
    engagements_csv_file: Path,
) -> None:
    with open(engagements_csv_file, newline="") as fp:
        reader = csv.DictReader(fp)
        for i, row in enumerate(reader):
            institution_identifier, employment_identifier = row["user_key"].split("-")
            cpr = last(row["cpr"].split(":"))

            logger.info(
                "Syncing engagement",
                institution_identifier=institution_identifier,
                cpr=cpr,
                employment_identifier=employment_identifier,
                employee_uuid=row["employee"],
                counter=i,
            )

            r = httpx.post(
                ENGAGEMENT_SYNC_URL,
                json={
                    "institution_identifier": institution_identifier,
                    "cpr": cpr,
                    "employment_identifier": employment_identifier,
                },
            )
            try:
                r.raise_for_status()
            except HTTPStatusError as error:
                logger.error("Could not sync engagement", error=error)


if __name__ == "__main__":
    main()
