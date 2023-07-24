# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
"""
To run:

    $ cd os2mo-sdtool-plus
    $ poetry shell
    $ export AUTH_SERVER=...
    $ export CLIENT_SECRET=...
    $ python -m sdtoolplus

"""
from uuid import uuid4

import click
from anytree import RenderTree
from pydantic import AnyHttpUrl
from ra_utils.job_settings import JobSettings
from raclients.graph.client import GraphQLClient
from sdclient.client import SDClient

from sdtoolplus.sd.importer import get_sd_tree
from .mo_org_unit_importer import MOOrgTreeImport
from .mo_org_unit_importer import OrgUnit
from .mo_org_unit_importer import OrgUnitUUID


def _get_mock_sd_org_tree(mo_org_tree) -> OrgUnit:
    mock_sd_root: OrgUnit = OrgUnit(
        uuid=mo_org_tree.get_org_uuid(),
        parent_uuid=None,
        name="<root>",
    )
    mock_sd_updated_child: OrgUnit = OrgUnit(
        uuid=OrgUnitUUID("f06ee470-9f17-566f-acbe-e938112d46d9"),
        parent_uuid=mo_org_tree.get_org_uuid(),
        name="Kolding Kommune II",
    )
    mock_sd_new_child: OrgUnit = OrgUnit(
        uuid=uuid4(),
        parent_uuid=mo_org_tree.get_org_uuid(),
        name="Something new",
    )
    mock_sd_root.children = [mock_sd_updated_child, mock_sd_new_child]
    return mock_sd_root


@click.command()
@click.option("--mora_base", envvar="MORA_BASE", default="http://localhost:5000")
@click.option("--client_id", envvar="CLIENT_ID", default="dipex")
@click.option("--client_secret", envvar="CLIENT_SECRET")
@click.option("--auth_realm", envvar="AUTH_REALM", default="mo")
@click.option("--auth_server", envvar="AUTH_SERVER")
@click.option("--sd-username", envvar="SD_USERNAME")
@click.option("--sd-password", envvar="SD_PASSWORD")
@click.option("--sd-institution-identifier", envvar="SD_INSTITUTION_IDENTIFIER")
def main(
    mora_base: str,
    client_id: str,
    client_secret: str,
    auth_realm: str,
    auth_server: AnyHttpUrl,
    sd_username: str,
    sd_password: str,
    sd_institution_identifier: str
) -> None:
    job_settings = JobSettings()
    job_settings.start_logging_based_on_settings()

    session = GraphQLClient(
        url=f"{mora_base}/graphql/v3",
        client_id=client_id,
        client_secret=client_secret,
        auth_realm=auth_realm,
        auth_server=auth_server,
        sync=True,
        httpx_client_kwargs={"timeout": None},
    )
    mo_org_tree = MOOrgTreeImport(session)

    sd_client = SDClient(sd_username, sd_password)
    sd_org_tree = get_sd_tree(sd_client, sd_institution_identifier)

    print(RenderTree(sd_org_tree).by_attr("uuid"))


if __name__ == "__main__":
    main()
