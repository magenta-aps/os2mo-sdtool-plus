# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from anytree import RenderTree

from sdtoolplus.mo_org_unit_importer import OrgUnitNode


def tree_as_string(tree: OrgUnitNode) -> str:
    """
    Get a printable string version of an organisation tree

    Args:
        tree: the tree to print

    Returns:
        A string version of the tree
    """
    return "\n".join(
        (f"{pre}{node.name} ({str(node.uuid)})" for pre, _, node in RenderTree(tree))
    )
