# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from functools import cache

import anytree
from anytree.importer import DictImporter
from gql import gql
from more_itertools import one


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
        return [one(n["objects"]) for n in doc["org_units"]]

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
