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


class OrgUnit(pydantic.BaseModel):
    uuid: OrgUnitUUID
    parent_uuid: OrgUnitUUID | None
    name: str


class OrgUnitNode(anytree.AnyNode):
    def __init__(
        self,
        uuid: OrgUnitUUID = None,
        parent_uuid: OrgUnitUUID = None,
        name: str = None,
        parent: "OrgUnitNode" = None,
        children: list["OrgUnitNode"] = None,
    ):
        super().__init__(parent=parent, children=children)
        self._instance = OrgUnit(uuid=uuid, parent_uuid=parent_uuid, name=name)

    @classmethod
    def from_org_unit(cls, org_unit: OrgUnit) -> "OrgUnitNode":
        return cls(
            uuid=org_unit.uuid,
            parent_uuid=org_unit.parent_uuid,
            name=org_unit.name,
        )

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.name}>"

    def __eq__(self, other) -> bool:
        if isinstance(other, OrgUnitNode):
            return self._instance.uuid == other._instance.uuid
        return super().__eq__(other)

    @property
    def uuid(self) -> OrgUnitUUID:
        return self._instance.uuid

    @property
    def parent_uuid(self) -> OrgUnitUUID:
        return self._instance.parent_uuid

    @property
    def name(self) -> str:
        return self._instance.name


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

    def as_single_tree(self) -> OrgUnitNode:
        children = self._build_trees(self.get_org_units())
        root = OrgUnitNode(
            uuid=self.get_org_uuid(),
            parent_uuid=None,
            name="<root>",
            children=children,
        )
        return root

    def _build_trees(self, org_units: list[OrgUnit]) -> list[OrgUnitNode]:
        # Convert list of `OrgUnit` objects to list of `OrgUnitNode` objects
        nodes = [OrgUnitNode.from_org_unit(org_unit) for org_unit in org_units]

        # Mutate the list of `OrgUnitNodes` in order to reconstruct the tree structure
        # given by the `uuid` and `parent_uuid` attributes.
        #
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
                focus_node.children = []

            focus_node_children = list(
                filter(
                    lambda node: node.parent_uuid == focus_node.uuid,
                    nodes,
                )
            )
            focus_node.children = focus_node_children
            for node in focus_node_children:
                root_nodes.append(node)

            root_nodes.remove(focus_node)

        # Return roots containing child nodes, each child node containing its child
        # nodes, and so on.
        return [nodes[idx] for idx in root_idxs]
