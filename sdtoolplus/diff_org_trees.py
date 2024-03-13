# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from collections.abc import Iterator
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

import structlog
from anytree.util import commonancestors
from more_itertools import partition
from pydantic import BaseModel

from .config import SDToolPlusSettings
from .graphql import GET_ENGAGEMENTS
from .graphql import get_graphql_client
from .mo_org_unit_importer import OrgUnitNode
from .mo_org_unit_importer import OrgUnitUUID

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
        settings: SDToolPlusSettings,
    ):
        self.mo_org_tree = mo_org_tree
        self.sd_org_tree = sd_org_tree
        self.settings = settings

        self.nodes_processed: set[OrgUnitUUID] = set()
        self.engs_in_subtree: set[OrgUnitUUID] = set()

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

        # Partition units into 1) the units to update without further checking
        # and 2) those that potentially should be moved to a subtree of on of
        # the obsolete units ("Udgåede afdelinger")
        units_to_update, units_to_move_to_obsolete_subtree = partition(
            self._in_obsolete_units_subtree, self.units_to_update
        )

        # Partition units into 1) those with active engagements and 2) those
        # who do not have active engagements
        units_to_move, units_not_to_move = partition(
            self._subtree_has_active_engagements, units_to_move_to_obsolete_subtree
        )

        self.units_to_update = list(units_to_update) + list(units_to_move)
        self.units_for_mails_alert = list(units_not_to_move)

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

    def _in_obsolete_units_subtree(self, unit: OrgUnitNode) -> bool:
        """
        Check if the unit is in the subtree of one of the obsolete units ("Udgåede afdelinger")

        Args:
             unit: the unit to check

        Returns:
            True if the unit is in one of the subtrees of obsolete units or False otherwise
        """
        ancestors_uuids = [node.uuid for node in commonancestors(unit)]
        return any(
            obsolete_unit_root in ancestors_uuids
            for obsolete_unit_root in self.settings.obsolete_unit_roots
        )

    def _has_active_engagements(self, org_unit_node: OrgUnitNode) -> bool:
        """
        Check if the unit has current or future active engagements

        Args:
            org_unit_node: the unit to check

        Returns:
            True if the unit has current or future active engagements or False otherwise
        """

        # TODO: has to be done in this way for now, but we will use the FastRAMQPI
        # GraphQL client in the future
        gql_client = get_graphql_client(self.settings)

        r = gql_client.execute(
            GET_ENGAGEMENTS,
            variable_values={
                "uuid": str(org_unit_node.uuid),
                "from_date": datetime.now(tz=ZoneInfo("Europe/Copenhagen")).isoformat(),
            },
        )

        return len(r["engagements"]["objects"]) > 0

    def _subtree_has_active_engagements(self, node: OrgUnitNode) -> bool:
        """
        Check if a node or the subtree of the node has active engagements.
        If so, add the node UUID to the self.engs_in_subtree set. The function
        will also (always) add the node to self.nodes_processed to enhance
        performance using memoization.
        """

        if node.uuid in self.nodes_processed:
            return True if node.uuid in self.engs_in_subtree else False

        def add_node_if_subtree_has_engagements(
            subtree_root: OrgUnitNode,
            node_to_process: OrgUnitNode,
            engs_in_subtree: set[OrgUnitUUID],
            nodes_processed: set[OrgUnitUUID],
        ) -> bool:
            nodes_processed.add(node_to_process.uuid)
            active_engs = self._has_active_engagements(node_to_process)
            if active_engs:
                engs_in_subtree.add(subtree_root.uuid)
                engs_in_subtree.add(node_to_process.uuid)
                return True

            return any(
                add_node_if_subtree_has_engagements(
                    subtree_root, n, engs_in_subtree, nodes_processed
                )
                for n in node_to_process.children
            )

        return add_node_if_subtree_has_engagements(
            node, node, self.engs_in_subtree, self.nodes_processed
        )

    def get_units_to_add(self) -> Iterator[OrgUnitNode]:
        for unit in self.units_to_add:
            yield unit

    def get_units_to_update(self) -> Iterator[OrgUnitNode]:
        for unit in self.units_to_update:
            yield unit

    def get_units_for_mails_alert(self) -> list[OrgUnitNode]:
        return self.units_for_mails_alert
