# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

from sdclient.responses import GetDepartmentResponse
from sdclient.responses import GetEmploymentChangedResponse

from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
from sdtoolplus.models import Active
from sdtoolplus.models import EngId
from sdtoolplus.models import EngName
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitName
from sdtoolplus.models import UnitUUID
from sdtoolplus.sd.timeline import get_department_timeline
from sdtoolplus.sd.timeline import get_engagement_timeline
from sdtoolplus.sd.tree import ASSUMED_SD_TIMEZONE


def test_get_department_timeline():
    # Arrange
    dep_uuid = uuid4()

    sd_dep_resp_dict = {
        "RegionIdentifier": "RI",
        "RegionUUIDIdentifier": uuid4(),
        "InstitutionIdentifier": "II",
        "InstitutionUUIDIdentifier": uuid4(),
        "Department": [
            {
                "ActivationDate": "2001-01-01",
                "DeactivationDate": "2001-12-31",
                "DepartmentIdentifier": "DEP1",
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentName": "name1",
                "DepartmentUUIDIdentifier": dep_uuid,
            },
            {
                "ActivationDate": "2002-01-01",
                "DeactivationDate": "2002-12-31",
                "DepartmentIdentifier": "DEP2",  # Changed
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentName": "name1",  # Not changed
                "DepartmentUUIDIdentifier": dep_uuid,
            },
            # Hole in SD timeline here
            {
                "ActivationDate": "2004-01-01",
                "DeactivationDate": "2004-12-31",
                "DepartmentIdentifier": "DEP1",
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentName": "name3",
                "DepartmentUUIDIdentifier": dep_uuid,
            },
            {
                "ActivationDate": "2005-01-01",
                "DeactivationDate": "9999-12-31",
                "DepartmentIdentifier": "DEP1",
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentName": "name4",
                "DepartmentUUIDIdentifier": dep_uuid,
            },
        ],
    }

    mock_sd_client = MagicMock()
    mock_sd_client.get_department.return_value = GetDepartmentResponse.parse_obj(
        sd_dep_resp_dict
    )

    # Act
    department_timeline = get_department_timeline(mock_sd_client, "II", dep_uuid)

    # Assert
    assert department_timeline.active == Timeline[Active](
        intervals=(
            Active(
                start=datetime(2001, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2003, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value=True,
            ),
            Active(
                start=datetime(2004, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime.max.replace(tzinfo=ASSUMED_SD_TIMEZONE),
                value=True,
            ),
        )
    )

    assert department_timeline.name == Timeline[UnitName](
        intervals=(
            UnitName(
                start=datetime(2001, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2003, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value="name1",
            ),
            UnitName(
                start=datetime(2004, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2005, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value="name3",
            ),
            UnitName(
                start=datetime(2005, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime.max.replace(tzinfo=ASSUMED_SD_TIMEZONE),
                value="name4",
            ),
        )
    )


# TODO: test empty case


def test_get_engagement_timeline():
    # Arrange
    dep_uuid1 = uuid4()
    dep_uuid2 = uuid4()

    sd_emp_resp_dict = {
        "Person": [
            {
                "PersonCivilRegistrationIdentifier": "0101011234",
                "Employment": [
                    {
                        "EmploymentIdentifier": "12345",
                        "EmploymentDate": "2000-01-01",
                        "AnniversaryDate": "2000-01-01",
                        "EmploymentStatus": [
                            {
                                "ActivationDate": "2001-01-01",
                                "DeactivationDate": "2001-12-31",
                                "EmploymentStatusCode": "0",
                            },
                            {
                                "ActivationDate": "2002-01-01",
                                "DeactivationDate": "2002-12-31",
                                "EmploymentStatusCode": "3",
                            },
                            {
                                "ActivationDate": "2003-01-01",
                                "DeactivationDate": "2003-12-31",
                                "EmploymentStatusCode": "1",
                            },
                        ],
                        "Profession": [
                            {
                                "ActivationDate": "2001-01-01",
                                "DeactivationDate": "2001-06-30",
                                "JobPositionIdentifier": "1234",
                                "EmploymentName": "Ninja",
                                "AppointmentCode": "0",
                            },
                            {
                                "ActivationDate": "2001-07-01",
                                "DeactivationDate": "2001-12-31",
                                "JobPositionIdentifier": "4321",
                                "EmploymentName": "Kung Fu Master",
                                "AppointmentCode": "0",
                            },
                        ],
                        "EmploymentDepartment": [
                            {
                                "ActivationDate": "2001-01-01",
                                "DeactivationDate": "2001-12-31",
                                "DepartmentIdentifier": "ABCD",
                                "DepartmentUUIDIdentifier": dep_uuid1,
                            },
                            # Let's put in a hole here just for fun
                            {
                                "ActivationDate": "2003-01-01",
                                "DeactivationDate": "9999-12-31",
                                "DepartmentIdentifier": "EFGH",
                                "DepartmentUUIDIdentifier": dep_uuid2,
                            },
                        ],
                    }
                ],
            }
        ]
    }

    mock_sd_client = MagicMock()
    mock_sd_client.get_employment_changed.return_value = (
        GetEmploymentChangedResponse.parse_obj(sd_emp_resp_dict)
    )

    # Act
    engagement_timeline = get_engagement_timeline(
        mock_sd_client, "II", "0101011234", "12345"
    )

    # Assert
    assert engagement_timeline.active == Timeline[Active](
        intervals=(
            Active(
                start=datetime(2001, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2004, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value=True,
            ),
        )
    )

    assert engagement_timeline.eng_name == Timeline[EngName](
        intervals=(
            EngName(
                start=datetime(2001, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2001, 7, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value="Ninja",
            ),
            EngName(
                start=datetime(2001, 7, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2002, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value="Kung Fu Master",
            ),
        )
    )

    assert engagement_timeline.eng_id == Timeline[EngId](
        intervals=(
            EngId(
                start=datetime(2001, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2001, 7, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value=1234,
            ),
            EngId(
                start=datetime(2001, 7, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2002, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value=4321,
            ),
        )
    )

    assert engagement_timeline.unit_uuid == Timeline[UnitUUID](
        intervals=(
            UnitUUID(
                start=datetime(2001, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2002, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value=dep_uuid1,
            ),
            UnitUUID(
                start=datetime(2003, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime.max.replace(tzinfo=ASSUMED_SD_TIMEZONE),
                value=dep_uuid2,
            ),
        )
    )
