# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from uuid import UUID

from ramodels.mo import Validity
from sdclient.responses import GetDepartmentResponse
from sdclient.responses import GetOrganizationResponse

from ..mo_class import MOOrgUnitLevelMap
from ..mo_org_unit_importer import OrgUnitNode
from ..sd.tree import build_tree
from .conftest import SharedIdentifier


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
        name="<root>",
        org_unit_level_uuid=None,
        validity=None,
    )
    dep1 = OrgUnitNode(
        uuid=SharedIdentifier.child_org_unit_uuid,
        parent_uuid=SharedIdentifier.root_org_uuid,
        parent=expected_tree,
        name="Department 1",
        org_unit_level_uuid=mock_mo_org_unit_level_map["NY1-niveau"].uuid,
        validity=sd_expected_validity,
    )
    dep2 = OrgUnitNode(
        uuid=SharedIdentifier.grandchild_org_unit_uuid,
        parent_uuid=SharedIdentifier.child_org_unit_uuid,
        parent=dep1,
        name="Department 2",
        org_unit_level_uuid=mock_mo_org_unit_level_map["NY0-niveau"].uuid,
        validity=sd_expected_validity,
    )
    dep3 = OrgUnitNode(
        uuid=UUID("30000000-0000-0000-0000-000000000000"),
        parent_uuid=SharedIdentifier.grandchild_org_unit_uuid,
        parent=dep2,
        name="Department 3",
        org_unit_level_uuid=mock_mo_org_unit_level_map["Afdelings-niveau"].uuid,
        validity=sd_expected_validity,
    )
    dep4 = OrgUnitNode(
        uuid=UUID("40000000-0000-0000-0000-000000000000"),
        parent_uuid=SharedIdentifier.grandchild_org_unit_uuid,
        parent=dep2,
        name="Department 4",
        org_unit_level_uuid=mock_mo_org_unit_level_map["Afdelings-niveau"].uuid,
        validity=sd_expected_validity,
    )
    dep5 = OrgUnitNode(
        uuid=UUID("50000000-0000-0000-0000-000000000000"),
        parent_uuid=SharedIdentifier.child_org_unit_uuid,
        parent=dep1,
        name="Department 5",
        org_unit_level_uuid=mock_mo_org_unit_level_map["NY0-niveau"].uuid,
        validity=sd_expected_validity,
    )
    dep6 = OrgUnitNode(
        uuid=UUID("60000000-0000-0000-0000-000000000000"),
        parent_uuid=UUID("50000000-0000-0000-0000-000000000000"),
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
        assert node_a.name == node_b.name
        assert node_a.org_unit_level_uuid == node_b.org_unit_level_uuid
        assert node_a.validity == node_b.validity
        # Only displayed in case test fails
        print("\t" * depth, node_a, node_b)
        # Visit child nodes pair-wise
        for child_a, child_b in zip(node_a.children, node_b.children):
            assert_equal(child_a, child_b, depth=depth + 1)

    assert_equal(actual_tree, expected_tree)
