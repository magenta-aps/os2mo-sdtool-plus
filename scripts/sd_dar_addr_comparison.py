# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from operator import itemgetter

import click
from httpx import Client
from httpx import Timeout
from more_itertools import first
from sdclient.client import SDClient
from sdclient.responses import Department

from sdtoolplus.addresses import DARAddressUUID
from sdtoolplus.models import AddressTypeUserKey
from sdtoolplus.sd.addresses import get_addresses
from sdtoolplus.sd.importer import get_sd_departments


httpx_client = Client(
    base_url="https://api.dataforsyningen.dk/",
    timeout=Timeout(timeout=30),
)


def get_dar_cat_and_uuid(addr: str) -> tuple[str, DARAddressUUID]:
    params = {"betegnelse": addr}
    r = httpx_client.get(url="datavask/adresser", params=params).json()
    return r["kategori"], DARAddressUUID(first(r["resultater"])["adresse"]["id"])


def get_dar_address(dar_id: DARAddressUUID) -> str:
    r = httpx_client.get(f"adresser/{str(dar_id)}")
    if r.status_code == 200:
        return r.json()["adressebetegnelse"]
    return "DAR UUID ikke fundet!"


def format_csv_field(field: str | None) -> str:
    return field if field is not None else "-"


@click.command()
@click.option(
    "--username",
    "username",
    type=click.STRING,
    envvar="SD_USERNAME",
    # required=True,
    help="SD username",
)
@click.option(
    "--password",
    "password",
    type=click.STRING,
    envvar="SD_PASSWORD",
    # required=True,
    help="SD password",
)
@click.option(
    "--institution-identifier",
    "institution_identifier",
    type=click.STRING,
    envvar="SD_INSTITUTION_IDENTIFIER",
    # required=True,
    help="SD institution identifier",
)
def main(
    username: str,
    password: str,
    institution_identifier: str,
):
    sd_client = SDClient(username, password)

    print("Get SD departments and their addresses")
    sd_departments = get_sd_departments(
        sd_client=sd_client,
        institution_identifier=institution_identifier,
        activation_date=datetime.now().date(),
        deactivation_date=datetime(9999, 12, 31),
        fetch_postal_addr=True,
    )

    print("Create SD department -> postal address map")
    sd_dep_with_postal_addresses: list[tuple[Department, str | None]] = [
        (sd_dep, addr.name)
        for sd_dep in sd_departments.Department
        for addr in get_addresses(sd_dep)
        if addr.address_type.user_key == AddressTypeUserKey.POSTAL_ADDR.value
    ]

    print("Generate CSV file")
    csv_header = (
        "Enhed",
        "UUID",
        "SD adresse",
        "DAR kategori",
        "Vasket adresse",
        "DAR UUID",
    )

    csv = []
    for sd_dep, addr in sd_dep_with_postal_addresses:
        assert addr is not None

        print(
            f"{str(sd_dep.DepartmentUUIDIdentifier)}\t{sd_dep.DepartmentName}\t\t{addr}"
        )

        category, dar_uuid = get_dar_cat_and_uuid(addr)
        dar_addr_str = get_dar_address(dar_uuid)

        csv.append(
            (
                sd_dep.DepartmentName,
                str(sd_dep.DepartmentUUIDIdentifier),
                addr,
                category,
                dar_addr_str,
                str(dar_uuid),
            )
        )

    # Sort after 1) category and 2) unit name
    csv.sort(key=itemgetter(3, 0))
    csv.insert(0, csv_header)

    with open("/tmp/adresser.csv", "w") as fp:
        fp.writelines([";".join(line) + "\n" for line in csv])


if __name__ == "__main__":
    main()
