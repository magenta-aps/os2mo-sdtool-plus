# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from functools import cache
from typing import Self
from typing import TypeAlias
from uuid import UUID

import anytree
import pydantic
from gql import gql
from pydantic import parse_obj_as
from ramodels.mo import Validity

OrgUUID: TypeAlias = UUID
OrgUnitUUID: TypeAlias = UUID
OrgUnitLevelUUID: TypeAlias = UUID


class OrgUnit(pydantic.BaseModel):
    uuid: OrgUnitUUID
    parent_uuid: OrgUnitUUID | None
    name: str
    org_unit_level_uuid: OrgUnitLevelUUID | None
    validity: Validity | None


class OrgUnitNode(anytree.AnyNode):
    def __init__(
        self,
        uuid: OrgUnitUUID | None = None,
        parent_uuid: OrgUnitUUID | None = None,
        name: str | None = None,
        parent: Self | None = None,
        children: list["OrgUnitNode"] | None = None,
        org_unit_level_uuid: OrgUnitLevelUUID | None = None,
        validity: Validity | None = None,
    ):
        super().__init__(parent=parent, children=children)
        self._instance = OrgUnit(
            uuid=uuid,
            parent_uuid=parent_uuid,
            name=name,
            org_unit_level_uuid=org_unit_level_uuid,
            validity=validity,
        )

    @classmethod
    def from_org_unit(cls, org_unit: OrgUnit) -> "OrgUnitNode":
        return cls(
            uuid=org_unit.uuid,
            parent_uuid=org_unit.parent_uuid,
            name=org_unit.name,
            org_unit_level_uuid=org_unit.org_unit_level_uuid,
            validity=org_unit.validity,
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
    def parent_uuid(self) -> OrgUnitUUID | None:
        return self._instance.parent_uuid

    @property
    def name(self) -> str:
        return self._instance.name

    @property
    def org_unit_level_uuid(self) -> OrgUnitLevelUUID | None:
        return self._instance.org_unit_level_uuid

    @property
    def validity(self) -> Validity | None:
        return self._instance.validity


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
                            current {
                                uuid
                                parent_uuid
                                name
                                org_unit_level_uuid
                            }
                        }
                    }
                }
                """
            )
        )
        org_units: list[dict] = [
            n["current"]
            for n in doc["org_units"]["objects"]
            if n["current"] is not None
        ]
        return parse_obj_as(list[OrgUnit], org_units)

    def as_single_tree(self, path: str = "") -> OrgUnitNode:
        """
        Generates a (sub)tree of OUs from the units in MO.
        The feature is most easily explained by an example. Assume the OU
        tree in MO looks like this:

             A (uuidA)
            / \
          B    C (uuidC)
         / \  / \
        D  E F   G (uuidG)
                / \
               H   I

        Calling the function as 'instance.as_single_tree("uuidC/uuidG")'
        returns the tree:

                root (UUID of the MO organisation)
                / \
               H   I

        If 'path' is the empty string, the whole tree is returned
        """

        children = self._build_trees(self.get_org_units())
        root = OrgUnitNode(
            uuid=self.get_org_uuid(),
            parent_uuid=None,
            name="<root>",
            children=children,
            org_unit_level_uuid=None,
        )

        if path:
            resolver = anytree.Resolver("uuid")
            new_root = resolver.get(root, path)
            root = OrgUnitNode(
                uuid=self.get_org_uuid(),
                parent_uuid=None,
                name="<root>",
                children=new_root.children,
                org_unit_level_uuid=None,
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
            node.parent_uuid for node in nodes if node.parent_uuid != root_org_uuid
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
