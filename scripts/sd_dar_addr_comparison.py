# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from operator import itemgetter
from typing import cast
from uuid import UUID
from uuid import uuid4

import click
from anytree.cachedsearch import find_by_attr
from httpx import Client
from httpx import Timeout
from more_itertools import first
from sdclient.client import SDClient
from sdclient.responses import Department

from sdtoolplus.addresses import DARAddressUUID
from sdtoolplus.mo_class import MOClass
from sdtoolplus.mo_class import MOOrgUnitLevelMap
from sdtoolplus.mo_org_unit_importer import OrgUnitNode
from sdtoolplus.models import AddressTypeUserKey
from sdtoolplus.sd.addresses import get_addresses
from sdtoolplus.sd.importer import get_sd_departments
from sdtoolplus.sd.importer import get_sd_tree


class FakeMOOrgUnitTypeMap(MOOrgUnitLevelMap):
    def __init__(self):
        self.fake_uuid = uuid4()

    def __getitem__(self, item: str) -> MOClass:
        return MOClass(uuid=self.fake_uuid, user_key="not used", name="not used")


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


def _remove_if_obsolete(
    sd_dep_with_postal_addresses: list[tuple[Department, str | None]],
    sd_tree: OrgUnitNode,
    obsolete_uuid: UUID,
) -> list[tuple[Department, str | None]]:
    non_obsolete_departments: list[tuple[Department, str | None]] = []
    for sd_dep, addr in sd_dep_with_postal_addresses:
        node = find_by_attr(sd_tree, sd_dep.DepartmentUUIDIdentifier, "uuid")
        if node is None:
            continue
        ancestor_uuids = [ancestor.uuid for ancestor in node.ancestors]
        if obsolete_uuid not in ancestor_uuids + [node.uuid]:
            non_obsolete_departments.append((sd_dep, addr))
    return non_obsolete_departments


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
@click.option(
    "--exclude-obsolete-uuid",
    "exclude_obsolete_uuid",
    type=click.UUID,
    help="The UUID of the top obsolete unit ('Udgåede afdelinger'). "
    "If set, units below this unit will be excluded",
)
def main(
    username: str,
    password: str,
    institution_identifier: str,
    exclude_obsolete_uuid: UUID,
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
    print("Total number of SD units:", len(sd_dep_with_postal_addresses))

    if exclude_obsolete_uuid:
        print("Excluding obsolete units...")
        sd_tree = get_sd_tree(
            sd_client,
            institution_identifier,
            FakeMOOrgUnitTypeMap(),  # Not important when we are not writing to MO
            build_full_tree=True,
        )
        sd_dep_with_postal_addresses = _remove_if_obsolete(
            sd_dep_with_postal_addresses,
            sd_tree,
            exclude_obsolete_uuid,
        )
        print("Number of SD units after exclude:", len(sd_dep_with_postal_addresses))

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
    errors = []
    for sd_dep, addr in sd_dep_with_postal_addresses:
        try:
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
        except Exception as err:
            print(str(err))
            errors.append(
                (
                    str(sd_dep.DepartmentUUIDIdentifier),
                    cast(str, sd_dep.DepartmentName),
                    addr or "",
                    str(err),
                )
            )

    # Sort after 1) category and 2) unit name
    csv.sort(key=itemgetter(3, 0))
    csv.insert(0, csv_header)

    with open("/tmp/adresser.csv", "w") as fp:
        fp.writelines([";".join(line) + "\n" for line in csv])

    with open("/tmp/errors.csv", "w") as fp:
        fp.writelines([";".join(line) + "\n" for line in errors])


if __name__ == "__main__":
    main()
