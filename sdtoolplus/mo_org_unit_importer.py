# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import logging
import uuid
from functools import cache

import anytree
import click
from anytree import RenderTree
from anytree.importer import DictImporter
from deepdiff import DeepDiff
from gql import gql
from pydantic import AnyHttpUrl
from ra_utils.job_settings import JobSettings
from raclients.graph.client import GraphQLClient


logger = logging.getLogger(__name__)


class MOOrgTreeImport:
    def __init__(self, session):
        self.session = session

    @cache
    def get_org_uuid(self) -> str:
        doc = self.session.execute(
            gql(
                """
                query GetOrgUUID {
                    org {
                        uuid
                    }
                }
                """
            )
        )
        return doc["org"]["uuid"]

    @cache
    def get_org_units(self) -> list[dict]:
        doc = self.session.execute(
            gql(
                """
                query GetOrgUnits {
                    org_units {
                        objects {
                            uuid
                            parent_uuid
                            name
                        }
                    }
                }
                """
            )
        )
        return [n["objects"][0] for n in doc["org_units"]]

    def as_anytree_root(self) -> anytree.Node:
        importer = DictImporter()
        return importer.import_(self.as_single_tree())

    def as_single_tree(self) -> dict:
        root = {
            "uuid": self.get_org_uuid(),
            "parent_uuid": None,
            "name": "<root>",
            "children": self._build_trees(self.get_org_units()),
        }
        return root

    def _build_trees(self, nodes) -> list[dict]:
        # Based on: https://stackoverflow.com/a/72497630

        root_org_uuid = self.get_org_uuid()

        # Root nodes and their indexes
        root_nodes = [node for node in nodes if node["parent_uuid"] == root_org_uuid]
        root_idxs = [nodes.index(node) for node in root_nodes]

        # Child nodes
        parent_id_vals = {
            node["parent_uuid"]
            for node in nodes
            if node["parent_uuid"] != root_org_uuid
        }

        while root_nodes:
            focus_node = root_nodes[0]
            if focus_node["uuid"] in parent_id_vals:
                focus_node["children"] = []

            for node in nodes:
                if node["parent_uuid"] == focus_node["uuid"]:
                    focus_node["children"].append(node)
                    root_nodes.append(node)

            root_nodes.remove(focus_node)

        # Return roots containing child nodes, each child node containing its child
        # nodes, and so on.
        return [nodes[idx] for idx in root_idxs]


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

    mo_import = MOOrgTreeImport(session)
    mo_root = mo_import.as_anytree_root()
    print(RenderTree(mo_root))

    sd_import = DictImporter()
    sd_root = sd_import.import_(
        {
            "uuid": str(uuid.uuid4()),
            "parent_uuid": None,
            "name": "<root>",
            "children": [],
        }
    )

    # Compare to SD org unit tree
    deepdiff = DeepDiff(mo_root, sd_root, ignore_order=True)
    print(deepdiff.pretty())


if __name__ == "__main__":
    main()
