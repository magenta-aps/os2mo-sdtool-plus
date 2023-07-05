# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from uuid import UUID

from more_itertools import one

from sdtoolplus.mo_org_unit_importer import OrgUnitNode
from sdclient.responses import GetOrganizationResponse, GetDepartmentResponse, \
    DepartmentReference, Department


def _create_node(
        dep_uuid: UUID,
        dep_name: str,
        parent: OrgUnitNode,
        existing_nodes: dict[UUID, OrgUnitNode]
) -> OrgUnitNode:
    """
    Create a node in the SD AnyNode tree and add the node to the dict
    of existing nodes.

    Args:
        dep_uuid: the SD department UUID
        dep_name: the SD department name
        parent: the parent of this node
        existing_nodes: dictionary of already existing nodes

    Returns:
        The created node
    """

    new_node = OrgUnitNode(
        uuid=dep_uuid,
        parent_uuid=parent.uuid,
        parent=parent,
        name=dep_name
    )

    existing_nodes[dep_uuid] = new_node

    return new_node


def _get_sd_departments_map(
        sd_departments: GetDepartmentResponse
) -> dict[UUID, Department]:
    """
    A mapping from an SD department UUID to the SD departments itself.

    Args:
        sd_departments: the GetDepartmentResponse from SD

    Returns:
        A mapping from an SD department UUID to the SD department itself.
    """

    return {
        department.DepartmentUUIDIdentifier: department
        for department in sd_departments.Department
    }


def _process_node(
        dep_ref: DepartmentReference,
        root_node: OrgUnitNode,
        sd_departments_map: dict[UUID, Department],
        existing_nodes: dict[UUID, OrgUnitNode]
) -> OrgUnitNode:
    """
    Process a node in the SD "tree", i.e. process a node in the
    DepartmentReference structure returned from the SD GetOrganization
    endpoint.

    Args:
        dep_ref: the DepartmentReference to process
        root_node: the root node of the SD tree
        sd_departments_map: a mapping from an SD department UUID to the
          SD departments itself.
        existing_nodes: dictionary of already existing nodes

    Returns:
        The SD tree node representing the SD department.
    """

    dep_uuid = dep_ref.DepartmentUUIDIdentifier
    dep_name = sd_departments_map[dep_uuid].DepartmentName

    if dep_uuid in existing_nodes:
        return existing_nodes[dep_uuid]

    if len(dep_ref.DepartmentReference) > 0:
        parent_dep_ref = one(dep_ref.DepartmentReference)

        parent = _process_node(
            parent_dep_ref,
            root_node,
            sd_departments_map,
            existing_nodes
        )

        new_node = _create_node(dep_uuid, dep_name, parent, existing_nodes)
        return new_node

    new_node = _create_node(dep_uuid, dep_name, root_node, existing_nodes)
    return new_node


def build_tree(
        sd_org: GetOrganizationResponse,
        sd_departments: GetDepartmentResponse,
) -> OrgUnitNode:
    """
    Build the SD organization unit tree structure.

    Args:
        sd_org: the response from the SD endpoint GetOrganization
        sd_departments: the response from the SD endpoint GetDepartment

    Returns:
        The SD organization unit tree structure.
    """

    root_node = OrgUnitNode(
        uuid=sd_org.InstitutionUUIDIdentifier,
        parent_uuid=None,
        name="<root>"
    )

    sd_departments_map = _get_sd_departments_map(sd_departments)

    existing_nodes = {}
    for dep_refs in one(sd_org.Organization).DepartmentReference:
        _process_node(
            dep_refs, root_node, sd_departments_map, existing_nodes)

    return root_node
