# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import date

from sdclient.client import SDClient
from sdclient.requests import GetOrganizationRequest, GetDepartmentRequest
from sdclient.responses import GetOrganizationResponse, GetDepartmentResponse

from sdtoolplus.mo_org_unit_importer import OrgUnit
from sdtoolplus.sd.tree import build_tree


def get_sd_organization(
        sd_client: SDClient,
        institution_identifier: str,
        activation_date: date,
        deactivation_date: date
) -> GetOrganizationResponse:
    # TODO: add docstring
    req = GetOrganizationRequest(
        InstitutionIdentifier=institution_identifier,
        ActivationDate=activation_date,
        DeactivationDate=deactivation_date,
        UUIDIndicator=True
    )

    return sd_client.get_organization(req)


def get_sd_departments(
        sd_client: SDClient,
        institution_identifier: str,
        activation_date: date,
        deactivation_date: date
) -> GetDepartmentResponse:
    # TODO: add docstring
    req = GetDepartmentRequest(
        InstitutionIdentifier=institution_identifier,
        ActivationDate=activation_date,
        DeactivationDate=deactivation_date,
        DepartmentNameIndicator=True,
        UUIDIndicator=True
    )

    return sd_client.get_department(req)


def get_sd_tree(sd_client: SDClient, institution_identifier: str) -> OrgUnit:
    # TODO: add docstring
    today = date.today()

    sd_org = get_sd_organization(sd_client, institution_identifier, today, today)
    # print(sd_org)
    sd_departments = get_sd_departments(sd_client, institution_identifier, today, today)
    # print(sd_departments)

    return build_tree(sd_org, sd_departments)
