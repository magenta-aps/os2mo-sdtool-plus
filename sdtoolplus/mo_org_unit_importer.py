# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from functools import cache
from typing import TypeAlias
from uuid import UUID

import anytree
import pydantic
from gql import gql
from more_itertools import one
from pydantic import parse_obj_as


OrgUUID: TypeAlias = UUID
OrgUnitUUID: TypeAlias = UUID


class OrgUnit(pydantic.BaseModel, anytree.NodeMixin):
    uuid: OrgUnitUUID
    parent_uuid: OrgUnitUUID | None
    name: str
    child_org_units: list["OrgUnit"] = pydantic.Field(default_factory=list)

    @property
    def children(self):
        return tuple(self.child_org_units)

    @property
    def is_leaf(self):
        return self.child_org_units == []


class MOOrgTreeImport:
    def __init__(self, session):
        self.session = session

    @cache
    def get_org_uuid(self) -> OrgUUID:
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
        return parse_obj_as(OrgUUID, doc["org"]["uuid"])

    @cache
    def get_org_units(self) -> list[OrgUnit]:
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
        org_units: list[dict] = [one(n["objects"]) for n in doc["org_units"]]
        return parse_obj_as(list[OrgUnit], org_units)

    def as_single_tree(self) -> OrgUnit:
        children = self._build_trees(self.get_org_units())
        root = OrgUnit(
            uuid=self.get_org_uuid(),
            parent_uuid=None,
            name="<root>",
            child_org_units=children,
        )
        return root

    def _build_trees(self, nodes) -> list[OrgUnit]:
        # Based on: https://stackoverflow.com/a/72497630

        root_org_uuid = self.get_org_uuid()

        # Root nodes and their indexes
        root_nodes = [node for node in nodes if node.parent_uuid == root_org_uuid]
        root_idxs = [nodes.index(node) for node in root_nodes]

        # Child nodes
        parent_id_vals = {
            node.parent_uuid
            for node in nodes
            if node.parent_uuid != root_org_uuid
        }

        while root_nodes:
            focus_node = root_nodes[0]
            if focus_node.uuid in parent_id_vals:
                focus_node.child_org_units = []

            focus_node_children = list(
                filter(
                    lambda node: node.parent_uuid == focus_node.uuid,
                    nodes,
                )
            )
            focus_node.child_org_units = focus_node_children
            for node in focus_node_children:
                root_nodes.append(node)

            root_nodes.remove(focus_node)

        # Return roots containing child nodes, each child node containing its child
        # nodes, and so on.
        return [nodes[idx] for idx in root_idxs]
