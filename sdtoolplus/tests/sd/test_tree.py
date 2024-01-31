# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import date
from uuid import UUID
from uuid import uuid4

from ramodels.mo import Validity
from sdclient.responses import Department
from sdclient.responses import GetDepartmentResponse
from sdclient.responses import GetOrganizationResponse

from sdtoolplus.mo_class import MOOrgUnitLevelMap
from sdtoolplus.mo_org_unit_importer import Address
from sdtoolplus.mo_org_unit_importer import AddressType
from sdtoolplus.mo_org_unit_importer import OrgUnitNode
from sdtoolplus.sd.tree import _get_sd_validity
from sdtoolplus.sd.tree import build_tree
from sdtoolplus.tests.conftest import SharedIdentifier


def test_build_tree(
    mock_sd_get_organization_response: GetOrganizationResponse,
    mock_sd_get_department_response: GetDepartmentResponse,
    mock_mo_org_unit_level_map: MOOrgUnitLevelMap,
    sd_expected_validity: Validity,
):
    # Arrange
    expected_tree = OrgUnitNode(
        uuid=SharedIdentifier.root_org_uuid,
        parent_uuid=None,
        user_key="root",
        name="<root>",
        org_unit_level_uuid=None,
        validity=None,
    )
    dep1 = OrgUnitNode(
        uuid=SharedIdentifier.child_org_unit_uuid,
        parent_uuid=SharedIdentifier.root_org_uuid,
        user_key="dep1",
        parent=expected_tree,
        name="Department 1",
        org_unit_level_uuid=mock_mo_org_unit_level_map["NY1-niveau"].uuid,
        addresses=[
            Address(
                name="Hovedgaden 1, 1000 Andeby",
                address_type=AddressType(user_key="AddressMailUnit"),
            ),
            Address(name="123456789", address_type=AddressType(user_key="Pnummer")),
        ],
        validity=sd_expected_validity,
    )
    dep2 = OrgUnitNode(
        uuid=SharedIdentifier.grandchild_org_unit_uuid,
        parent_uuid=SharedIdentifier.child_org_unit_uuid,
        user_key="dep2",
        parent=dep1,
        name="Department 2",
        org_unit_level_uuid=mock_mo_org_unit_level_map["NY0-niveau"].uuid,
        validity=sd_expected_validity,
    )
    dep3 = OrgUnitNode(
        uuid=UUID("30000000-0000-0000-0000-000000000000"),
        parent_uuid=SharedIdentifier.grandchild_org_unit_uuid,
        user_key="dep3",
        parent=dep2,
        name="Department 3",
        org_unit_level_uuid=mock_mo_org_unit_level_map["Afdelings-niveau"].uuid,
        validity=sd_expected_validity,
    )
    dep4 = OrgUnitNode(
        uuid=UUID("40000000-0000-0000-0000-000000000000"),
        parent_uuid=SharedIdentifier.grandchild_org_unit_uuid,
        user_key="dep4",
        parent=dep2,
        name="Department 4",
        org_unit_level_uuid=mock_mo_org_unit_level_map["Afdelings-niveau"].uuid,
        validity=sd_expected_validity,
    )
    dep5 = OrgUnitNode(
        uuid=UUID("50000000-0000-0000-0000-000000000000"),
        parent_uuid=SharedIdentifier.child_org_unit_uuid,
        user_key="dep5",
        parent=dep1,
        name="Department 5",
        org_unit_level_uuid=mock_mo_org_unit_level_map["NY0-niveau"].uuid,
        validity=sd_expected_validity,
    )
    dep6 = OrgUnitNode(
        uuid=UUID("60000000-0000-0000-0000-000000000000"),
        parent_uuid=UUID("50000000-0000-0000-0000-000000000000"),
        user_key="dep6",
        parent=dep5,
        name="Department 6",
        org_unit_level_uuid=mock_mo_org_unit_level_map["Afdelings-niveau"].uuid,
        validity=sd_expected_validity,
    )

    # Act
    actual_tree = build_tree(
        mock_sd_get_organization_response,
        mock_sd_get_department_response,
        mock_mo_org_unit_level_map,
    )

    # Assert
    def assert_equal(node_a: OrgUnitNode, node_b: OrgUnitNode, depth: int = 0):
        assert node_a == node_b
        assert node_a.uuid == node_b.uuid
        assert node_a.parent_uuid == node_b.parent_uuid
        assert node_a.user_key == node_b.user_key
        assert node_a.name == node_b.name
        assert node_a.org_unit_level_uuid == node_b.org_unit_level_uuid
        assert node_a.validity == node_b.validity
        assert node_a.addresses == node_b.addresses
        # Only displayed in case test fails
        print("\t" * depth, node_a, node_b)
        # Visit child nodes pair-wise
        for child_a, child_b in zip(node_a.children, node_b.children):
            assert_equal(child_a, child_b, depth=depth + 1)

    assert_equal(actual_tree, expected_tree)


def test_override_sd_root_uuid(
    mock_sd_get_organization_response: GetOrganizationResponse,
    mock_sd_get_department_response: GetDepartmentResponse,
    mock_mo_org_unit_level_map: MOOrgUnitLevelMap,
):
    # Arrange
    sd_root_uuid = uuid4()

    # Act
    actual_tree = build_tree(
        mock_sd_get_organization_response,
        mock_sd_get_department_response,
        mock_mo_org_unit_level_map,
        sd_root_uuid,
    )

    # Assert
    assert actual_tree.uuid == sd_root_uuid


def test_get_sd_validity(
    mock_sd_get_department_response: GetDepartmentResponse,
    sd_expected_validity: Validity,
) -> None:
    # 1. Test that the "normal" `ActivationDate`/`DeactivationDate` values are converted
    # to the expected SD validity.
    sd_dep: Department = mock_sd_get_department_response.Department[0]
    sd_actual_validity: Validity = _get_sd_validity(sd_dep)
    assert sd_actual_validity == sd_expected_validity

    # 2. Test that a "special" `DeactivationDate` of "9999-12-31" is converted to None,
    # representing an open validity period.
    sd_dep.DeactivationDate = date(9999, 12, 31)
    sd_actual_validity = _get_sd_validity(sd_dep)
    assert sd_actual_validity.to_date is None
