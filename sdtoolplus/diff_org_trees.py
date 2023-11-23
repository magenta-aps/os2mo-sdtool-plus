# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from collections.abc import Iterator
from uuid import UUID

import structlog
from pydantic import BaseModel

from .mo_org_unit_importer import OrgUnitNode


logger = structlog.get_logger()


class Nodes(BaseModel):
    unit: OrgUnitNode
    parent: OrgUnitNode

    class Config:
        arbitrary_types_allowed = True


def _uuid_to_nodes_map(tree: OrgUnitNode) -> dict[UUID, Nodes]:
    """
    A map from a UUID tree node to a Nodes object containing the
    OrgUnitNodes of the unit itself and its parent.

    Args:
        tree: the tree (MO or SD) to create the map from

    Returns:
        A dict mapping from a UUID tree node to a Nodes object
        (see description above)
    """

    def add_node_children(node: OrgUnitNode, parent_map: dict[UUID, Nodes]):
        for child in node.children:
            parent_map[child.uuid] = Nodes(unit=child, parent=node)
            add_node_children(child, parent_map)
        return parent_map

    return add_node_children(tree, dict())


class OrgTreeDiff:
    def __init__(
        self,
        mo_org_tree: OrgUnitNode,
        sd_org_tree: OrgUnitNode,
    ):
        self.mo_org_tree = mo_org_tree
        self.sd_org_tree = sd_org_tree

        logger.info("Comparing the SD and MO trees")
        self._compare_trees()

    def _compare_trees(self) -> None:
        sd_uuid_map = _uuid_to_nodes_map(self.sd_org_tree)
        mo_uuid_map = _uuid_to_nodes_map(self.mo_org_tree)

        # New SD units which should be added to MO
        self.units_to_add = [
            sd_nodes.unit
            for unit_uuid, sd_nodes in sd_uuid_map.items()
            if unit_uuid not in mo_uuid_map.keys()
        ]

        # Units to rename or move
        self.units_to_update = [
            sd_nodes.unit
            for unit_uuid, sd_nodes in sd_uuid_map.items()
            if (
                unit_uuid in mo_uuid_map.keys()
                and OrgTreeDiff._should_be_updated(sd_nodes, mo_uuid_map[unit_uuid])
            )
        ]

    @staticmethod
    def _should_be_updated(sd_nodes: Nodes, mo_nodes: Nodes) -> bool:
        """
        Check if a unit should be updated

        Args:
            sd_nodes: The SD nodes (unit itself and its parent)
            mo_nodes: The MO nodes (unit itself and its parent)

        Returns:
            True if the unit should be updated and False otherwise
        """
        return (
            mo_nodes.parent.uuid != sd_nodes.parent.uuid
            or mo_nodes.unit.name != sd_nodes.unit.name
        )

    def get_units_to_add(self) -> Iterator[OrgUnitNode]:
        for unit in self.units_to_add:
            yield unit

    def get_units_to_update(self) -> Iterator[OrgUnitNode]:
        for unit in self.units_to_update:
            yield unit
