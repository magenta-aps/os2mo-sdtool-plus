# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import logging

import click
from anytree import RenderTree
from anytree.importer import DictImporter
from deepdiff import DeepDiff
from gql import gql
from ra_utils.job_settings import JobSettings
from raclients.graph.client import GraphQLClient


logger = logging.getLogger(__name__)


class MOOrgTreeImport:
    def __init__(self, session):
        self.session = session

    def visit_all(self, visitor):
        roots = self._build_trees(self.get_org_units())
        for root in roots:
            self._visit_subtree(visitor, root)

    def get_org_uuid(self):
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

    def get_org_units(self):
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

    def _build_trees(self, nodes):
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

            for i in nodes:
                if i["parent_uuid"] == focus_node["uuid"]:
                    focus_node["children"].append(i)
                    root_nodes.append(i)

            root_nodes.remove(focus_node)

        # Return roots containing child nodes, each child node containing its child
        # nodes, and so on.
        return [nodes[idx] for idx in root_idxs]

    def _visit_subtree(self, visitor, node, depth=0, path=None):
        if path is None:
            path = [node["name"]]

        visitor(node, depth=depth, path=path)

        # Visit child nodes, if any
        if "children" in node:
            sorted_children = sorted(node["children"], key=lambda child: child["name"])
            for child_node in sorted_children:
                path_copy = path + [child_node["name"]]
                self._visit_subtree(
                    visitor, child_node, depth=depth + 1, path=path_copy
                )

    def visitor(self, node, path, depth):
        print("{}{}".format("\t" * depth, path))


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
    auth_server: str,
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

    mo_org_tree_import = MOOrgTreeImport(session)

    # Display as tree on console
    mo_org_tree_import.visit_all(mo_org_tree_import.visitor)

    # Import to AnyTree
    importer = DictImporter()
    for subtree in mo_org_tree_import._build_trees(mo_org_tree_import.get_org_units()):
        root = importer.import_(subtree)
        print(RenderTree(root))

    # Compare to SD org unit tree
    deepdiff = DeepDiff(
        mo_org_tree_import._build_trees(mo_org_tree_import.get_org_units()),
        [],  # SD org unit tree goes here :)
        ignore_order=True,
    )
    print(deepdiff.pretty())


if __name__ == "__main__":
    main()
