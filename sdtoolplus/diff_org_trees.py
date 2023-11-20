# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import abc
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Self
from uuid import UUID
from uuid import uuid4

from anytree.cachedsearch import find
from deepdiff import DeepDiff
from deepdiff.diff import DiffLevel
from deepdiff.helper import CannotCompare
from ramodels.mo import Validity

from .mo_class import MOClass
from .mo_org_unit_importer import OrgUnitNode


class Operation(abc.ABC):
    """This class defines an `Operation` interface which *must* be implemented by the
    subclasses of `Operation`.

    To construct class instances, we use a class method `from_diff_level` (rather than
    defining an `__init__` taking a `DiffLevel` instance as an argument), as the
    `__init__` method is controlled by the `@dataclass` decorator used on
    `RemoveOperation`, `AddOperation`, etc. (See subclasses below.)
    """

    @classmethod
    def from_diff_level(
        cls,
        diff_level: DiffLevel,
        org_unit_type: MOClass,
    ) -> Self | None:
        """Given a `DiffLevel` instance, produce the relevant `Operation` instance.

        When overridden by subclasses, this method is expected to return either an
        instance of that subclass, or None.

        `DiffLevel` objects are part of the `deepdiff` API and represent individual
        nodes in a given `DeepDiff` instance.
        """
        raise NotImplementedError("must be implemented by subclass")

    def __str__(self):
        """Return a string describing the concrete operation to perform, i.e. giving
        details of what will be removed, updated or added."""
        raise NotImplementedError("must be implemented by subclass")

    def __init__(self):
        self._diff_level = None
        super().__init__()


@dataclass
class MoveOperation(Operation):
    uuid: UUID  # The unit to move
    parent: UUID  # The new parent
    name: str  # The (new) name of the unit
    validity: Validity

    @classmethod
    def from_diff_level(
        cls,
        diff_level: DiffLevel,
        org_unit_type: MOClass,
    ) -> Self | None:
        MoveOperation._get_new_parent(diff_level)
        instance = cls(
            uuid=diff_level.t1.uuid,
            parent=MoveOperation._get_new_parent(diff_level),
            name=MoveOperation._get_unit_name(diff_level),
            validity=Validity(from_date=datetime.now()),
        )
        instance._diff_level = diff_level
        return instance

    @staticmethod
    def _get_new_parent(diff_level: DiffLevel) -> UUID:
        sd_tree = diff_level.all_up.t2
        ou_to_move = find(sd_tree, filter_=lambda node: node.uuid == diff_level.t1.uuid)
        return ou_to_move.parent.uuid

    @staticmethod
    def _get_unit_name(diff_level: DiffLevel) -> str:
        sd_tree = diff_level.all_up.t2
        ou_to_move = find(sd_tree, filter_=lambda node: node.uuid == diff_level.t1.uuid)
        return ou_to_move.name

    def __str__(self):
        return f"Move {self._diff_level.t1} from {self._diff_level.up.up.t1} to {MoveOperation._get_new_parent(self._diff_level)}"


@dataclass
class UpdateOperation(Operation):
    uuid: UUID
    attr: str
    value: str
    validity: Validity

    @classmethod
    def from_diff_level(
        cls,
        diff_level: DiffLevel,
        org_unit_type: MOClass,
    ) -> Self | None:
        attr = diff_level.path().split(".")[-1]
        if attr in cls._supported_attrs():
            instance = cls(
                uuid=diff_level.up.t1.uuid,
                attr=attr,
                value=str(diff_level.t2),
                validity=diff_level.up.t2.validity,
            )
            instance._diff_level = diff_level
            return instance
        return None

    @classmethod
    def _supported_attrs(cls) -> set[str]:
        return {"name", "org_unit_level_uuid"}

    def __str__(self):
        return f"Update {self._diff_level.up.t1} {self.attr} to {self.value}"


@dataclass
class AddOperation(Operation):
    uuid: UUID
    parent_uuid: UUID
    name: str
    org_unit_type_uuid: UUID
    org_unit_level_uuid: UUID
    validity: Validity

    @classmethod
    def from_diff_level(
        cls,
        diff_level: DiffLevel,
        org_unit_type: MOClass,
    ) -> Self | None:
        instance = cls(
            uuid=diff_level.t2.uuid,
            parent_uuid=diff_level.up.up.t1.uuid,
            name=diff_level.t2.name,
            org_unit_type_uuid=org_unit_type.uuid,
            org_unit_level_uuid=diff_level.t2.org_unit_level_uuid,
            validity=diff_level.t2.validity,
        )
        instance._diff_level = diff_level
        return instance

    def __str__(self):
        return f"Add {self._diff_level.t2} as child of MO org unit {self._diff_level.up.up.t1}"


AnyOperation = AddOperation | UpdateOperation | MoveOperation | None


class OrgTreeDiff:
    def __init__(
        self,
        mo_org_tree: OrgUnitNode,
        sd_org_tree: OrgUnitNode,
        mo_org_unit_type: MOClass,
    ):
        # "ID-based" difference between the two org trees. Used to find the org units
        # that need to be removed or updated.
        self.uuid_deepdiff = self._get_deepdiff_instance(
            mo_org_tree,
            sd_org_tree,
            iterable_compare_func=self._compare_on_uuid,
        )
        # "Structural" difference between the two org trees. Used to find the org units
        # that need to be added.
        self.structural_deepdiff = self._get_deepdiff_instance(mo_org_tree, sd_org_tree)
        # Class in MO `org_unit_type` facet to use when emitting operations
        self._mo_org_unit_type = mo_org_unit_type

    def _get_deepdiff_instance(
        self, mo_org_tree: OrgUnitNode, sd_org_tree: OrgUnitNode, **kwargs
    ) -> DeepDiff:
        diff = DeepDiff(
            mo_org_tree,
            sd_org_tree,
            view="tree",
            include_obj_callback=self._is_relevant,
            **kwargs,
        )
        return diff

    @staticmethod
    def _is_relevant(node, path: str) -> bool:
        known_attrs = ("uuid", "parent_uuid", "name", "org_unit_level_uuid")
        name: str = path.split(".")[-1]
        if "__" in name:
            return False
        if name in known_attrs or "children" in name:
            return True
        return False

    @staticmethod
    def _compare_on_uuid(x, y, level: DiffLevel = None) -> bool:
        if isinstance(x, OrgUnitNode) and isinstance(y, OrgUnitNode):
            return x.uuid == y.uuid
        raise CannotCompare() from None

    @staticmethod
    def _root_key_children_filter(items: list[DiffLevel]) -> list[DiffLevel]:
        return [item for item in items if item.get_root_key() == "children"]

    def get_operations(
        self,
    ) -> Iterator[AnyOperation]:
        # Get items to move, add and update
        move_items = list(self.uuid_deepdiff.get("iterable_item_removed", []))
        add_items = list(self.structural_deepdiff.get("iterable_item_added", []))
        update_items = list(self.uuid_deepdiff.get("attribute_removed", [])) + list(
            self.uuid_deepdiff.get("values_changed", [])
        )

        # Filter based on the item root key
        move_items = OrgTreeDiff._root_key_children_filter(move_items)
        add_items = OrgTreeDiff._root_key_children_filter(add_items)
        update_items = OrgTreeDiff._root_key_children_filter(update_items)

        # Only add an "Add" item if it is not also moved
        move_items_uuids = [item.t1.uuid for item in move_items]
        add_items = [item for item in add_items if item.t2.uuid not in move_items_uuids]

        # Emit add operations from "structural diff"
        for item in add_items:
            yield AddOperation.from_diff_level(item, self._mo_org_unit_type)

        # Emit move operations from "id-based diff"
        for item in move_items:
            yield MoveOperation.from_diff_level(item, self._mo_org_unit_type)

        # Emit update operations from "id-based diff"
        for item in update_items:
            operation = UpdateOperation.from_diff_level(item, self._mo_org_unit_type)
            if operation:
                yield operation
