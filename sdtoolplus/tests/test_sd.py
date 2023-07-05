from uuid import UUID

from sdclient.responses import GetOrganizationResponse, GetDepartmentResponse

from sdtoolplus.mo_org_unit_importer import OrgUnitNode
from sdtoolplus.sd.tree import build_tree


def test_build_tree():
    # Arrange
    sd_org_json = {
        "RegionIdentifier": "RI",
        "InstitutionIdentifier": "II",
        "InstitutionUUIDIdentifier": "00000000-0000-0000-0000-000000000000",
        "DepartmentStructureName": "Dep structure name",
        "OrganizationStructure": {
            "DepartmentLevelIdentifier": "Afdelings-niveau",
            "DepartmentLevelReference": {
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentLevelReference": {
                    "DepartmentLevelIdentifier": "NY1-niveau"
                }
            }
        },
        "Organization": [
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "2000-01-01",
                "DepartmentReference": [
                    {
                        "DepartmentIdentifier": "Afd",
                        "DepartmentUUIDIdentifier": "30000000-0000-0000-0000-000000000000",
                        "DepartmentLevelIdentifier": "Afdelings-niveau",
                        "DepartmentReference": [
                            {
                                "DepartmentIdentifier": "NY0",
                                "DepartmentUUIDIdentifier": "20000000-0000-0000-0000-000000000000",
                                "DepartmentLevelIdentifier": "NY0-niveau",
                                "DepartmentReference": [
                                    {
                                        "DepartmentIdentifier": "NY1",
                                        "DepartmentUUIDIdentifier": "10000000-0000-0000-0000-000000000000",
                                        "DepartmentLevelIdentifier": "NY1-niveau",
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "DepartmentIdentifier": "Afd",
                        "DepartmentUUIDIdentifier": "40000000-0000-0000-0000-000000000000",
                        "DepartmentLevelIdentifier": "Afdelings-niveau",
                        "DepartmentReference": [
                            {
                                "DepartmentIdentifier": "NY0",
                                "DepartmentUUIDIdentifier": "20000000-0000-0000-0000-000000000000",
                                "DepartmentLevelIdentifier": "NY0-niveau",
                                "DepartmentReference": [
                                    {
                                        "DepartmentIdentifier": "NY1",
                                        "DepartmentUUIDIdentifier": "10000000-0000-0000-0000-000000000000",
                                        "DepartmentLevelIdentifier": "NY1-niveau",
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "DepartmentIdentifier": "Afd",
                        "DepartmentUUIDIdentifier": "60000000-0000-0000-0000-000000000000",
                        "DepartmentLevelIdentifier": "Afdelings-niveau",
                        "DepartmentReference": [
                            {
                                "DepartmentIdentifier": "NY0",
                                "DepartmentUUIDIdentifier": "50000000-0000-0000-0000-000000000000",
                                "DepartmentLevelIdentifier": "NY0-niveau",
                                "DepartmentReference": [
                                    {
                                        "DepartmentIdentifier": "NY1",
                                        "DepartmentUUIDIdentifier": "10000000-0000-0000-0000-000000000000",
                                        "DepartmentLevelIdentifier": "NY1-niveau",
                                    }
                                ]
                            }
                        ]
                    },
                ]
            }
        ]
    }

    sd_departments_json = {
        "RegionIdentifier": "RI",
        "InstitutionIdentifier": "II",
        "Department": [
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "2000-01-01",
                "DepartmentIdentifier": "NY1",
                "DepartmentLevelIdentifier": "NY1-niveau",
                "DepartmentName": "Department 1",
                "DepartmentUUIDIdentifier": "10000000-0000-0000-0000-000000000000"
            },
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "2000-01-01",
                "DepartmentIdentifier": "NY0",
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentName": "Department 2",
                "DepartmentUUIDIdentifier": "20000000-0000-0000-0000-000000000000"
            },
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "2000-01-01",
                "DepartmentIdentifier": "Afd",
                "DepartmentLevelIdentifier": "Afdelings-niveau",
                "DepartmentName": "Department 3",
                "DepartmentUUIDIdentifier": "30000000-0000-0000-0000-000000000000"
            },
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "2000-01-01",
                "DepartmentIdentifier": "Afd",
                "DepartmentLevelIdentifier": "Afdelings-niveau",
                "DepartmentName": "Department 4",
                "DepartmentUUIDIdentifier": "40000000-0000-0000-0000-000000000000"
            },
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "2000-01-01",
                "DepartmentIdentifier": "NY0",
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentName": "Department 5",
                "DepartmentUUIDIdentifier": "50000000-0000-0000-0000-000000000000"
            },
            {
                "ActivationDate": "1999-01-01",
                "DeactivationDate": "2000-01-01",
                "DepartmentIdentifier": "Afd",
                "DepartmentLevelIdentifier": "Afdelings-niveau",
                "DepartmentName": "Department 6",
                "DepartmentUUIDIdentifier": "60000000-0000-0000-0000-000000000000"
            },
        ]
    }

    sd_departments = GetDepartmentResponse.parse_obj(sd_departments_json)
    sd_org = GetOrganizationResponse.parse_obj(sd_org_json)

    # Act
    actual_tree = build_tree(
        sd_org,
        sd_departments,
    )

    # Assert
    expected_tree = OrgUnitNode(
        uuid=UUID("00000000-0000-0000-0000-000000000000"),
        parent_uuid=None,
        name="<root>"
    )
    dep1 = OrgUnitNode(
        uuid=UUID("10000000-0000-0000-0000-000000000000"),
        parent_uuid=UUID("00000000-0000-0000-0000-000000000000"),
        parent=expected_tree,
        name="Department 1"
    )
    dep2 = OrgUnitNode(
        uuid=UUID("20000000-0000-0000-0000-000000000000"),
        parent_uuid=UUID("10000000-0000-0000-0000-000000000000"),
        parent=dep1,
        name="Department 2"
    )
    dep3 = OrgUnitNode(
        uuid=UUID("30000000-0000-0000-0000-000000000000"),
        parent_uuid=UUID("20000000-0000-0000-0000-000000000000"),
        parent=dep2,
        name="Department 3"
    )
    dep4 = OrgUnitNode(
        uuid=UUID("40000000-0000-0000-0000-000000000000"),
        parent_uuid=UUID("20000000-0000-0000-0000-000000000000"),
        parent=dep2,
        name="Department 4"
    )
    dep5 = OrgUnitNode(
        uuid=UUID("50000000-0000-0000-0000-000000000000"),
        parent_uuid=UUID("10000000-0000-0000-0000-000000000000"),
        parent=dep1,
        name="Department 5"
    )
    dep6 = OrgUnitNode(
        uuid=UUID("60000000-0000-0000-0000-000000000000"),
        parent_uuid=UUID("50000000-0000-0000-0000-000000000000"),
        parent=dep5,
        name="Department 6"
    )

    def assert_equal(node_a: OrgUnitNode, node_b: OrgUnitNode, depth: int = 0):
        assert node_a == node_b
        assert node_a.uuid == node_b.uuid
        assert node_a.parent_uuid == node_b.parent_uuid
        assert node_a.name == node_b.name
        # Only displayed in case test fails
        print("\t" * depth, node_a, node_b)
        # Visit child nodes pair-wise
        for child_a, child_b in zip(node_a.children, node_b.children):
            assert_equal(child_a, child_b, depth=depth + 1)

    assert_equal(actual_tree, expected_tree)
