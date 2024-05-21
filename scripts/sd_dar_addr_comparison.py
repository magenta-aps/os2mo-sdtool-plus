# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from operator import itemgetter
from typing import cast
from uuid import UUID

import click
from fastramqpi.raclients.graph.client import GraphQLClient
from gql import gql
from httpx import Client
from httpx import Timeout
from more_itertools import first
from more_itertools import one
from sdclient.client import SDClient
from sdclient.responses import Department

from sdtoolplus.addresses import DARAddressUUID
from sdtoolplus.models import AddressTypeUserKey
from sdtoolplus.sd.addresses import get_addresses
from sdtoolplus.sd.importer import get_sd_departments


QUERY_GET_LINE_MANAGEMENT_CLASS = gql(
    """
    query GetLineManagementClass {
      classes(filter: {facet_user_keys: "org_unit_hierarchy", user_keys: "linjeorg"}) {
        objects {
          current {
            uuid
            user_key
            name
          }
        }
      }
    }
    """
)

QUERY_GET_ORG_UNIT = gql(
    """
    query GetOrgUnit {
      org_units {
        objects {
          current {
            org_unit_hierarchy
            uuid
          }
        }
      }
    }
    """
)


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


def _get_line_management_class(gql_client: GraphQLClient) -> UUID:
    r = gql_client.execute(QUERY_GET_LINE_MANAGEMENT_CLASS)
    return UUID(one(r["classes"]["objects"])["current"]["uuid"])


def _get_mo_org_unit_hierarchy(gql_client: GraphQLClient) -> dict[UUID, UUID | None]:
    r = gql_client.execute(QUERY_GET_ORG_UNIT)
    objs = r["org_units"]["objects"]
    return {
        UUID(obj["current"]["uuid"]): obj["current"]["org_unit_hierarchy"]
        for obj in objs
    }


def _is_line_management(
    sd_dep_addr: tuple[Department, str | None],
    mo_org_unit_hierarchy: dict[UUID, UUID | None],
    line_management_class: UUID,
) -> bool:
    return (
        mo_org_unit_hierarchy[sd_dep_addr[0].DepartmentUUIDIdentifier]
        == line_management_class
    )


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
    "--auth-server",
    "auth_server",
    type=click.STRING,
    default="http://localhost:8090/auth",
    help="Keycloak auth server URL",
)
@click.option(
    "--client-id",
    "client_id",
    type=click.STRING,
    default="dipex",
    help="Keycloak client id",
)
@click.option(
    "--client-secret",
    "client_secret",
    type=click.STRING,
    required=True,
    help="Keycloak client secret for the DIPEX client",
)
@click.option(
    "--mo-base-url",
    "mo_base_url",
    type=click.STRING,
    default="http://localhost:5000",
    help="Base URL for calling MO",
)
def main(
    username: str,
    password: str,
    institution_identifier: str,
    auth_server: str,
    client_id: str,
    client_secret: str,
    mo_base_url: str,
):
    sd_client = SDClient(username, password)

    timeout = 120
    gql_client = GraphQLClient(
        url=f"{mo_base_url}/graphql/v22",
        client_id=client_id,
        client_secret=client_secret,
        auth_server=auth_server,  # type: ignore
        auth_realm="mo",
        execute_timeout=timeout,
        httpx_client_kwargs={"timeout": timeout},
        sync=True,
    )

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

    line_mgmt_class = _get_line_management_class(gql_client)

    print("Get MO org unit hierarchies")
    mo_org_unit_hierarchy = _get_mo_org_unit_hierarchy(gql_client)

    print("Filter out OUs not part of line management")
    sd_dep_with_postal_addresses = [
        sd_dep_addr
        for sd_dep_addr in sd_dep_with_postal_addresses
        if _is_line_management(sd_dep_addr, mo_org_unit_hierarchy, line_mgmt_class)
    ]
    print("Number of SD units after filtering:", len(sd_dep_with_postal_addresses))

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
