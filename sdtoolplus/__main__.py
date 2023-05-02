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
from anytree.importer import DictImporter
from pydantic import AnyHttpUrl
from ra_utils.job_settings import JobSettings
from raclients.graph.client import GraphQLClient

from .diff_org_trees import run_diff
from .mo_org_unit_importer import MOOrgTreeImport


def _get_mock_sd_org_tree(mo_org_tree):
    sd_import = DictImporter()
    return sd_import.import_(
        {
            "uuid": mo_org_tree.get_org_uuid(),
            "parent_uuid": None,
            "name": "<root>",
            "children": [
                {
                    "uuid": "f06ee470-9f17-566f-acbe-e938112d46d9",
                    "parent_uuid": "3b866d97-0b1f-48e0-8078-686d96f430b3",
                    "name": "Kolding Kommune II",
                    "children": [],
                },
                {
                    "uuid": str(uuid4()),
                    "parent_uuid": "3b866d97-0b1f-48e0-8078-686d96f430b3",
                    "name": "Something new ...",
                    "children": [],
                },
            ],
        }
    )


@click.command()
@click.option("--mora_base", envvar="MORA_BASE", default="http://localhost:5000")
@click.option("--client_id", envvar="CLIENT_ID", default="dipex")
@click.option("--client_secret", envvar="CLIENT_SECRET")
@click.option("--auth_realm", envvar="AUTH_REALM", default="mo")
@click.option("--auth_server", envvar="AUTH_SERVER")
def main(
    mora_base: str,
    client_id: str,
    client_secret: str,
    auth_realm: str,
    auth_server: AnyHttpUrl,
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
    sd_org_tree = _get_mock_sd_org_tree(mo_org_tree)

    run_diff(mo_org_tree.as_anytree_root(), sd_org_tree)


if __name__ == "__main__":
    main()
