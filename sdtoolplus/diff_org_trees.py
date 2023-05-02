# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from collections.abc import Iterator
from dataclasses import dataclass

from anytree import Node
from deepdiff import DeepDiff
from deepdiff.model import DiffLevel


@dataclass
class Operation:
    path: str


@dataclass
class RemoveOperation(Operation):
    uuid: str


@dataclass
class UpdateOperation(Operation):
    uuid: str
    attr: str
    value: str


@dataclass
class AddOperation(Operation):
    obj: Node


class OrgTreeDiff:
    def __init__(self, mo_org_tree, sd_org_tree):
        self.deepdiff = DeepDiff(
            mo_org_tree,
            sd_org_tree,
            report_repetition=True,
            iterable_compare_func=self._deepdiff_compare_func,
            view="tree",
        )

    def _deepdiff_compare_func(self, x, y, level: DiffLevel = None):
        return x.uuid == y.uuid

    def get_operations(self) -> Iterator[Operation]:
        already_emitted = set()

        # Emit removal operations
        for item in self.deepdiff.get("iterable_item_removed", []):
            if item.get_root_key() == "descendants":
                if item.t1.uuid not in already_emitted:
                    yield RemoveOperation(
                        uuid=item.t1.uuid,
                        path=item.path(),
                    )
                    already_emitted.add(item.t1.uuid)

        # Emit update operations
        for iterable_name in ("attribute_removed", "values_changed"):
            iterable = self.deepdiff.get(iterable_name, [])
            for item in iterable:
                if item.get_root_key() == "descendants":
                    attr = item.path().split(".")[-1]
                    if attr in ("name", "parent_uuid"):
                        yield UpdateOperation(
                            uuid=item.up.t1.uuid,
                            attr=attr,
                            value=item.t2,
                            path=item.path(),
                        )
                        already_emitted.add(item.up.t1.uuid)

        # Emit add operations
        for item in self.deepdiff.get("iterable_item_added", []):
            if item.get_root_key() == "descendants":
                if item.t2.uuid not in already_emitted:
                    yield AddOperation(
                        obj=item.t2,
                        path=item.path(),
                    )
                    already_emitted.add(item.t2.uuid)


def run_diff(mo_org_tree, sd_org_tree):
    diff = OrgTreeDiff(mo_org_tree, sd_org_tree)
    for op in diff.get_operations():
        print(op)
