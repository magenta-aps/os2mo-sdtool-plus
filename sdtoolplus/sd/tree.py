# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import zoneinfo
from datetime import date
from datetime import datetime
from uuid import UUID

from more_itertools import one
from ramodels.mo import Validity
from sdclient.responses import Department
from sdclient.responses import DepartmentReference
from sdclient.responses import GetDepartmentResponse
from sdclient.responses import GetOrganizationResponse

from sdtoolplus.mo_class import MOClass
from sdtoolplus.mo_class import MOOrgUnitLevelMap
from sdtoolplus.mo_org_unit_importer import Address
from sdtoolplus.mo_org_unit_importer import OrgUnitNode
from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
from sdtoolplus.sd.addresses import get_addresses

_ASSUMED_SD_TIMEZONE = zoneinfo.ZoneInfo("Europe/Copenhagen")


def create_node(
    dep_uuid: OrgUnitUUID,
    dep_name: str,
    dep_identifier: str,
    dep_level_identifier: str,
    dep_validity: Validity,
    parent: OrgUnitNode,
    addresses: list[Address],
    existing_nodes: dict[OrgUnitUUID, OrgUnitNode],
    mo_org_unit_level_map: MOOrgUnitLevelMap,
) -> OrgUnitNode:
    """
    Create a node in the SD AnyNode tree and add the node to the dict
    of existing nodes.

    Args:
        dep_uuid: the SD department UUID
        dep_name: the SD department name
        dep_level_identifier: the SD department level identifier ("NY1", etc.)
        parent: the parent of this node
        existing_nodes: dictionary of already existing nodes
        mo_org_unit_level_map: dictionary-like object of MO org unit levels

    Returns:
        The created node
    """

    org_unit_level: MOClass = mo_org_unit_level_map[dep_level_identifier]

    new_node = OrgUnitNode(
        uuid=dep_uuid,
        parent_uuid=parent.uuid,
        user_key=dep_identifier,
        parent=parent,
        name=dep_name,
        org_unit_level_uuid=org_unit_level.uuid,
        addresses=addresses,
        validity=dep_validity,
    )

    existing_nodes[dep_uuid] = new_node

    return new_node


def _get_sd_departments_map(
    sd_departments: GetDepartmentResponse,
) -> dict[OrgUnitUUID, Department]:
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


def get_sd_validity(dep: Department) -> Validity:
    def convert_infinity_to_none(sd_date: date) -> date | None:
        if sd_date == date(9999, 12, 31):
            return None
        return sd_date  # `date' instance

    def date_to_datetime_in_tz(sd_date: date | None) -> datetime | None:
        if sd_date is not None:
            return datetime(
                year=sd_date.year,
                month=sd_date.month,
                day=sd_date.day,
                hour=0,
                minute=0,
                second=0,
                tzinfo=_ASSUMED_SD_TIMEZONE,
            )
        return sd_date  # None

    return Validity(
        from_date=date_to_datetime_in_tz(dep.ActivationDate),
        to_date=date_to_datetime_in_tz(convert_infinity_to_none(dep.DeactivationDate)),
    )


def _process_node(
    dep_ref: DepartmentReference,
    root_node: OrgUnitNode,
    sd_departments_map: dict[OrgUnitUUID, Department],
    existing_nodes: dict[OrgUnitUUID, OrgUnitNode],
    mo_org_unit_level_map: MOOrgUnitLevelMap,
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
    dep_identifier = sd_departments_map[dep_uuid].DepartmentIdentifier
    dep_level_identifier = sd_departments_map[dep_uuid].DepartmentLevelIdentifier
    dep_validity: Validity = get_sd_validity(sd_departments_map[dep_uuid])

    addresses = get_addresses(sd_departments_map[dep_uuid])

    if dep_uuid in existing_nodes:
        return existing_nodes[dep_uuid]

    if len(dep_ref.DepartmentReference) > 0:
        parent_dep_ref = one(dep_ref.DepartmentReference)

        parent = _process_node(
            parent_dep_ref,
            root_node,
            sd_departments_map,
            existing_nodes,
            mo_org_unit_level_map,
        )

        new_node = create_node(
            dep_uuid,
            dep_name,
            dep_identifier,
            dep_level_identifier,
            dep_validity,
            parent,
            addresses,
            existing_nodes,
            mo_org_unit_level_map,
        )
        return new_node

    new_node = create_node(
        dep_uuid,
        dep_name,
        dep_identifier,
        dep_level_identifier,
        dep_validity,
        root_node,
        addresses,
        existing_nodes,
        mo_org_unit_level_map,
    )

    return new_node


def build_tree(
    sd_org: GetOrganizationResponse,
    sd_departments: GetDepartmentResponse,
    mo_org_unit_level_map: MOOrgUnitLevelMap,
    sd_root_uuid: UUID | None = None,
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
        uuid=sd_org.InstitutionUUIDIdentifier if sd_root_uuid is None else sd_root_uuid,
        parent_uuid=None,
        user_key="root",
        name="<root>",
        org_unit_level_uuid=None,
    )

    sd_departments_map = _get_sd_departments_map(sd_departments)

    existing_nodes: dict[OrgUnitUUID, OrgUnitNode] = {}
    for dep_refs in one(sd_org.Organization).DepartmentReference:
        _process_node(
            dep_refs,
            root_node,
            sd_departments_map,
            existing_nodes,
            mo_org_unit_level_map,
        )

    return root_node
