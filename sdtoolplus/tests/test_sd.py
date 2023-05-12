from uuid import UUID

from anytree import RenderTree

from sdclient.responses import GetOrganizationResponse, GetDepartmentResponse

from sdtoolplus.mo_org_unit_importer import OrgUnit
from sdtoolplus.sd.tree import build_tree


def test_build_tree():
    # Arrange
    sd_org_json = {
        "RegionIdentifier": "RI",
        "InstitutionIdentifier": "II",
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
    tree = build_tree(
        sd_org,
        sd_departments,
        UUID("00000000-0000-0000-0000-000000000000")
    )

    # Assert
    root = OrgUnit(
        uuid=UUID("00000000-0000-0000-0000-000000000000"),
        parent_uuid=None,
        name="<root>"
    )
    dep1 = OrgUnit(
        uuid=UUID("10000000-0000-0000-0000-000000000000"),
        parent_uuid=UUID("00000000-0000-0000-0000-000000000000"),
        parent=root,
        name="Department 1"
    )
    dep2 = OrgUnit(
        uuid=UUID("20000000-0000-0000-0000-000000000000"),
        parent_uuid=UUID("10000000-0000-0000-0000-000000000000"),
        parent=dep1,
        name="Department 2"
    )
    dep3 = OrgUnit(
        uuid=UUID("30000000-0000-0000-0000-000000000000"),
        parent_uuid=UUID("20000000-0000-0000-0000-000000000000"),
        parent=dep2,
        name="Department 3"
    )
    dep4 = OrgUnit(
        uuid=UUID("40000000-0000-0000-0000-000000000000"),
        parent_uuid=UUID("20000000-0000-0000-0000-000000000000"),
        parent=dep2,
        name="Department 4"
    )
    dep5 = OrgUnit(
        uuid=UUID("50000000-0000-0000-0000-000000000000"),
        parent_uuid=UUID("10000000-0000-0000-0000-000000000000"),
        parent=dep1,
        name="Department 5"
    )
    dep6 = OrgUnit(
        uuid=UUID("60000000-0000-0000-0000-000000000000"),
        parent_uuid=UUID("50000000-0000-0000-0000-000000000000"),
        parent=dep5,
        name="Department 6"
    )

    # Nice for debugging
    # print(RenderTree(tree).by_attr("uuid"))

    assert root == tree
