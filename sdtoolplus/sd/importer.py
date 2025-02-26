# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import date
from uuid import UUID

import structlog
from sdclient.client import SDClient
from sdclient.requests import GetDepartmentRequest
from sdclient.requests import GetOrganizationRequest
from sdclient.responses import GetDepartmentResponse
from sdclient.responses import GetOrganizationResponse
from tenacity import retry
from tenacity import stop_after_attempt
from tenacity import wait_fixed

from sdtoolplus.config import SD_RETRY_ATTEMPTS
from sdtoolplus.config import SD_RETRY_WAIT_TIME
from sdtoolplus.mo_class import MOOrgUnitLevelMap
from sdtoolplus.mo_org_unit_importer import OrgUnitNode
from sdtoolplus.sd.addresses import get_addresses
from sdtoolplus.sd.tree import build_extra_tree
from sdtoolplus.sd.tree import build_tree
from sdtoolplus.sd.tree import get_sd_validity

logger = structlog.stdlib.get_logger()


@retry(
    wait=wait_fixed(SD_RETRY_WAIT_TIME),
    stop=stop_after_attempt(SD_RETRY_ATTEMPTS),
    reraise=True,
)
def get_sd_organization(
    sd_client: SDClient,
    institution_identifier: str,
    activation_date: date,
    deactivation_date: date,
) -> GetOrganizationResponse:
    # TODO: add docstring
    req = GetOrganizationRequest(
        InstitutionIdentifier=institution_identifier,
        ActivationDate=activation_date,
        DeactivationDate=deactivation_date,
        UUIDIndicator=True,
    )

    return sd_client.get_organization(req)


@retry(
    wait=wait_fixed(SD_RETRY_WAIT_TIME),
    stop=stop_after_attempt(SD_RETRY_ATTEMPTS),
    reraise=True,
)
def get_sd_departments(
    sd_client: SDClient,
    institution_identifier: str,
    activation_date: date,
    deactivation_date: date,
    fetch_postal_addr: bool = False,
    fetch_pnumber: bool = False,
) -> GetDepartmentResponse:
    # TODO: add docstring
    req = GetDepartmentRequest(
        InstitutionIdentifier=institution_identifier,
        ActivationDate=activation_date,
        DeactivationDate=deactivation_date,
        DepartmentNameIndicator=True,
        PostalAddressIndicator=fetch_postal_addr,
        ProductionUnitIndicator=fetch_pnumber,
        UUIDIndicator=True,
    )

    return sd_client.get_department(req)


def get_sd_tree(
    sd_client: SDClient,
    institution_identifier: str,
    mo_org_unit_level_map: MOOrgUnitLevelMap,
    sd_root_uuid: UUID | None = None,
    build_full_tree: bool = False,
) -> OrgUnitNode:
    # TODO: add docstring
    today = date.today()

    logger.debug("Get SD organization...")
    sd_org = get_sd_organization(sd_client, institution_identifier, today, today)
    # print(sd_org)

    logger.debug("Get SD departments...")
    sd_departments = get_sd_departments(sd_client, institution_identifier, today, today)
    # print(sd_departments)

    logger.debug("Build SD tree...")
    root_node = build_tree(sd_org, sd_departments, mo_org_unit_level_map, sd_root_uuid)

    if build_full_tree:
        # Add "extra" units i.e. the units from GetDepartment which
        # are not found in GetOrganization
        build_extra_tree(
            sd_client,
            root_node,
            sd_org,
            sd_departments,
            mo_org_unit_level_map,
        )

    return root_node


def get_sd_units(
    sd_client: SDClient,
    institution_identifier: str,
) -> list[OrgUnitNode]:
    # TODO: add docstring
    today = date.today()

    sd_departments = get_sd_departments(
        sd_client, institution_identifier, today, today, True, True
    )

    return [
        OrgUnitNode(
            uuid=sd_dep.DepartmentUUIDIdentifier,
            user_key=sd_dep.DepartmentIdentifier,
            name=sd_dep.DepartmentName,
            addresses=get_addresses(sd_dep),
            validity=get_sd_validity(sd_dep),
        )
        for sd_dep in sd_departments.Department
    ]
