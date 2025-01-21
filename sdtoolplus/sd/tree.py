# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import zoneinfo
from datetime import date
from datetime import datetime
from uuid import UUID

from anytree import find
from more_itertools import one
from ramodels.mo import Validity
from sdclient.client import SDClient
from sdclient.requests import GetDepartmentParentRequest
from sdclient.responses import Department
from sdclient.responses import DepartmentReference
from sdclient.responses import GetDepartmentParentResponse
from sdclient.responses import GetDepartmentResponse
from sdclient.responses import GetOrganizationResponse
from structlog import get_logger
from tenacity import retry
from tenacity import stop_after_attempt
from tenacity import wait_fixed

from sdtoolplus.config import SD_RETRY_ATTEMPTS
from sdtoolplus.config import SD_RETRY_WAIT_TIME
from sdtoolplus.mo_class import MOClass
from sdtoolplus.mo_class import MOOrgUnitLevelMap
from sdtoolplus.mo_org_unit_importer import Address
from sdtoolplus.mo_org_unit_importer import OrgUnitNode
from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
from sdtoolplus.sd.addresses import get_addresses

_ASSUMED_SD_TIMEZONE = zoneinfo.ZoneInfo("Europe/Copenhagen")

logger = get_logger()


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
        dep_identifier: the SD department identifier
        dep_level_identifier: the SD department level identifier ("NY1", etc.)
        dep_validity: the SD department validity
        parent: the parent of this node
        addresses: list of unit addresses
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


def _get_extra_nodes(
    sd_org: GetOrganizationResponse,
    sd_departments: GetDepartmentResponse,
) -> set[OrgUnitUUID]:
    """
    Get the "extra" units from the GetDepartments response which are
    not found in the response from GetOrganization.

    Args:
        sd_org: the response from the SD endpoint GetOrganization
        sd_departments: the response from the SD endpoint GetDepartment

    Returns:
        Set of UUIDs of the unit found in the response from GetDepartment,
        but not found in the response from GetOrganization
    """

    def add_unit(existing_nodes_uuids: set[OrgUnitUUID], dep_ref: DepartmentReference):
        existing_nodes_uuids.add(dep_ref.DepartmentUUIDIdentifier)
        for d in dep_ref.DepartmentReference:
            add_unit(existing_nodes_uuids, d)

    dep_refs = one(sd_org.Organization).DepartmentReference
    existing_nodes_uuids: set[OrgUnitUUID] = set()
    for dep_ref in dep_refs:
        add_unit(existing_nodes_uuids, dep_ref)

    get_departments_unit_uuids = set(
        dep.DepartmentUUIDIdentifier for dep in sd_departments.Department
    )

    return get_departments_unit_uuids.difference(existing_nodes_uuids)


# TODO: This retrying mechanism makes the (integration) test suite very slow. Work out
# a solution to this problem later
@retry(
    wait=wait_fixed(SD_RETRY_WAIT_TIME),
    stop=stop_after_attempt(SD_RETRY_ATTEMPTS),
    reraise=True,
)
def _get_department_parent(
    sd_client: SDClient, unit_uuid: OrgUnitUUID
) -> GetDepartmentParentResponse | None:
    return sd_client.get_department_parent(
        GetDepartmentParentRequest(
            EffectiveDate=datetime.now().date(),
            DepartmentUUIDIdentifier=unit_uuid,
        )
    )


def _get_parent_node(
    sd_client: SDClient,
    unit_uuid: OrgUnitUUID,
    root_node: OrgUnitNode,
    sd_departments_map: dict[OrgUnitUUID, Department],
    sd_institution_uuid_identifier: UUID,
    mo_org_unit_level_map: MOOrgUnitLevelMap,
    extra_node_uuids: set[OrgUnitUUID],
) -> OrgUnitNode | None:
    try:
        parent_dep = _get_department_parent(sd_client, unit_uuid)
        if parent_dep is None:
            return None
        parent_uuid = parent_dep.DepartmentParent.DepartmentUUIDIdentifier
    except ValueError:
        return None

    if parent_uuid == sd_institution_uuid_identifier:
        return root_node

    # Try to find the parent in the root_node tree
    parent = find(root_node, lambda node: node.uuid == parent_uuid)
    if parent is not None:
        return parent

    # Cannot find parent in root_node tree, so we have to create it, but first
    # we must find the parents parent
    parents_parent = _get_parent_node(
        sd_client,
        parent_uuid,
        root_node,
        sd_departments_map,
        sd_institution_uuid_identifier,
        mo_org_unit_level_map,
        extra_node_uuids,
    )

    extra_node_uuids.discard(parent_uuid)

    if parents_parent is None:
        return None

    parent_sd_dep = sd_departments_map[parent_uuid]
    parent_node = OrgUnitNode(
        uuid=parent_uuid,
        parent_uuid=parents_parent.uuid,
        parent=parents_parent,
        user_key=parent_sd_dep.DepartmentIdentifier,
        name=parent_sd_dep.DepartmentName,
        org_unit_level_uuid=mo_org_unit_level_map[
            parent_sd_dep.DepartmentLevelIdentifier
        ].uuid,
        validity=get_sd_validity(parent_sd_dep),
    )

    return parent_node


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
        mo_org_unit_level_map: the MO org unit level map
        sd_root_uuid: the SD root UUID

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


def build_extra_tree(
    sd_client: SDClient,
    root_node: OrgUnitNode,
    sd_org: GetOrganizationResponse,
    sd_departments: GetDepartmentResponse,
    mo_org_unit_level_map: MOOrgUnitLevelMap,
) -> OrgUnitNode:
    """
    Add the "extra" units from the GetDepartments response, which are
    not found in the response from GetOrganization, to the root_node tree
    """

    sd_departments_map = _get_sd_departments_map(sd_departments)
    extra_node_uuids = _get_extra_nodes(sd_org, sd_departments)

    logger.debug(
        "Extra nodes",
        # extra_node_uuids={str(uuid) for uuid in extra_node_uuids},
        extra_nodes=len(extra_node_uuids),
    )

    while extra_node_uuids:
        unit_uuid = extra_node_uuids.pop()

        parent_node = _get_parent_node(
            sd_client,
            unit_uuid,
            root_node,
            sd_departments_map,
            sd_org.InstitutionUUIDIdentifier,
            mo_org_unit_level_map,
            extra_node_uuids,
        )
        if parent_node is None:
            continue

        sd_dep = sd_departments_map[unit_uuid]

        OrgUnitNode(
            uuid=unit_uuid,
            parent_uuid=parent_node.uuid,
            parent=parent_node,
            user_key=sd_dep.DepartmentIdentifier,
            name=sd_dep.DepartmentName,
            org_unit_level_uuid=mo_org_unit_level_map[
                sd_dep.DepartmentLevelIdentifier
            ].uuid,
            validity=get_sd_validity(sd_dep),
        )

    return root_node
