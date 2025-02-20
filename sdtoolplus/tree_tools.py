# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from typing import Iterator

from anytree import RenderTree  # type: ignore

from sdtoolplus.mo_org_unit_importer import OrgUnitNode


def _sort_by_name(node_iter: Iterator[OrgUnitNode]) -> list[OrgUnitNode]:
    return sorted(node_iter, key=lambda node: node.name)


def tree_as_string(tree: OrgUnitNode) -> str:
    """
    Get a printable string version of an organisation tree

    Args:
        tree: the tree to print

    Returns:
        A string version of the tree
    """
    return "\n".join(
        (
            f"{pre}{node.name} ({str(node.uuid)})"
            for pre, _, node in RenderTree(tree, childiter=_sort_by_name)
        )
    )
