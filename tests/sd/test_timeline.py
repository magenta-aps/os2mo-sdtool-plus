# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import date
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import UUID
from uuid import uuid4

import pytest
from more_itertools import one
from pydantic import parse_obj_as
from sdclient.exceptions import SDParentNotFound
from sdclient.exceptions import SDRootElementNotFound
from sdclient.responses import DepartmentParentHistoryObj
from sdclient.responses import GetDepartmentResponse
from sdclient.responses import GetEmploymentChangedResponse
from sdclient.responses import WorkingTime

from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
from sdtoolplus.models import POSITIVE_INFINITY
from sdtoolplus.models import Active
from sdtoolplus.models import EngagementKey
from sdtoolplus.models import EngagementName
from sdtoolplus.models import EngagementTimeline
from sdtoolplus.models import EngagementType
from sdtoolplus.models import EngagementUnit
from sdtoolplus.models import EngagementUnitId
from sdtoolplus.models import EngType
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitId
from sdtoolplus.models import UnitLevel
from sdtoolplus.models import UnitName
from sdtoolplus.models import UnitParent
from sdtoolplus.models import UnitTimeline
from sdtoolplus.sd.timeline import _sd_employment_type
from sdtoolplus.sd.timeline import get_department_timeline
from sdtoolplus.sd.timeline import get_employment_timeline
from sdtoolplus.sd.timeline import get_leave_timeline
from sdtoolplus.sd.tree import ASSUMED_SD_TIMEZONE


async def test_get_department_timeline():
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

    sd_parent_history_resp = [
        {
            "startDate": "2001-01-01",
            "endDate": "2002-12-31",
            "parentUuid": "8d3018f1-62ef-48cf-8e54-819b4408c23f",
        },
        {
            "startDate": "2004-01-01",
            "endDate": "9999-12-31",
            "parentUuid": "d567f959-ab77-4849-9cd0-c14e9120433c",
        },
    ]

    mock_sd_client = MagicMock()
    mock_sd_client.get_department.return_value = GetDepartmentResponse.parse_obj(
        sd_dep_resp_dict
    )
    mock_sd_client.get_department_parent_history.return_value = parse_obj_as(
        list[DepartmentParentHistoryObj], sd_parent_history_resp
    )

    # Act
    department_timeline = await get_department_timeline(
        sd_client=mock_sd_client, inst_id="II", unit_uuid=dep_uuid
    )

    # Assert
    query_params = one(one(mock_sd_client.get_department.call_args_list).args)
    assert query_params.InstitutionIdentifier == "II"
    assert query_params.DepartmentUUIDIdentifier == dep_uuid
    assert query_params.ActivationDate == date.min
    assert query_params.DeactivationDate == date.max
    assert query_params.DepartmentNameIndicator is True
    assert query_params.UUIDIndicator is True

    mock_sd_client.get_department_parent_history.assert_called_once_with(dep_uuid)

    assert department_timeline.active == Timeline[Active](
        intervals=(
            Active(
                start=datetime(2001, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2003, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value=True,
            ),
            Active(
                start=datetime(2004, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=POSITIVE_INFINITY,
                value=True,
            ),
        )
    )

    assert department_timeline.unit_id == Timeline[UnitId](
        intervals=(
            UnitId(
                start=datetime(2001, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2002, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value="DEP1",
            ),
            UnitId(
                start=datetime(2002, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2003, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value="DEP2",
            ),
            UnitId(
                start=datetime(2004, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=POSITIVE_INFINITY,
                value="DEP1",
            ),
        )
    )

    assert department_timeline.unit_level == Timeline[UnitLevel](
        intervals=(
            UnitLevel(
                start=datetime(2001, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2003, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value="NY0-niveau",
            ),
            UnitLevel(
                start=datetime(2004, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=POSITIVE_INFINITY,
                value="NY0-niveau",
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
                end=POSITIVE_INFINITY,
                value="name4",
            ),
        )
    )

    assert department_timeline.parent == Timeline[UnitParent](
        intervals=(
            UnitParent(
                start=datetime(2001, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2003, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value=OrgUnitUUID("8d3018f1-62ef-48cf-8e54-819b4408c23f"),
            ),
            UnitParent(
                start=datetime(2004, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=POSITIVE_INFINITY,
                value=OrgUnitUUID("d567f959-ab77-4849-9cd0-c14e9120433c"),
            ),
        )
    )


async def test_get_department_timeline_department_not_found():
    # Arrange
    dep_uuid = uuid4()

    mock_sd_client = MagicMock()
    mock_sd_client.get_department.side_effect = SDRootElementNotFound(
        "Could not find XML root element"
    )

    # Act
    department_timeline = await get_department_timeline(
        sd_client=mock_sd_client, inst_id="II", unit_uuid=dep_uuid
    )

    # Assert
    assert department_timeline == UnitTimeline(
        active=Timeline[Active](),
        name=Timeline[UnitName](),
        unit_id=Timeline[UnitId](),
        unit_level=Timeline[UnitLevel](),
        parent=Timeline[UnitParent](),
    )


async def test_get_department_timeline_parent_not_found():
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
        ],
    }

    mock_sd_client = MagicMock()
    mock_sd_client.get_department.return_value = GetDepartmentResponse.parse_obj(
        sd_dep_resp_dict
    )
    mock_sd_client.get_department_parent_history.side_effect = SDParentNotFound(
        "Parent history not found!"
    )

    # Act
    department_timeline = await get_department_timeline(
        sd_client=mock_sd_client, inst_id="II", unit_uuid=dep_uuid
    )

    # Assert
    assert department_timeline == UnitTimeline(
        active=Timeline[Active](),
        name=Timeline[UnitName](),
        unit_id=Timeline[UnitId](),
        unit_level=Timeline[UnitLevel](),
        parent=Timeline[UnitParent](),
    )


async def test_get_engagement_timeline(mock_sd_emp_resp_dict):
    # Act
    engagement_timeline = await get_employment_timeline(
        GetEmploymentChangedResponse.parse_obj(mock_sd_emp_resp_dict)
    )

    # Assert
    assert engagement_timeline.eng_active == Timeline[Active](
        intervals=(
            Active(
                start=datetime(2000, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2003, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value=True,
            ),
        )
    )

    assert engagement_timeline.eng_key == Timeline[EngagementKey](
        intervals=(
            EngagementKey(
                start=datetime(2000, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2022, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value=2,
            ),
            EngagementKey(
                start=datetime(2022, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=POSITIVE_INFINITY,
                value=4,
            ),
        )
    )

    assert engagement_timeline.eng_name == Timeline[EngagementName](
        intervals=(
            EngagementName(
                start=datetime(2000, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2022, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value="Ninja",
            ),
            EngagementName(
                start=datetime(2022, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=POSITIVE_INFINITY,
                value="Kung Fu Master",
            ),
        )
    )

    assert engagement_timeline.eng_unit == Timeline[EngagementUnit](
        intervals=(
            EngagementUnit(
                start=datetime(2000, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=POSITIVE_INFINITY,
                value=UUID("fa4a3454-54e6-43b8-92c4-9979bf41a386"),
            ),
        )
    )

    assert engagement_timeline.eng_unit_id == Timeline[EngagementUnitId](
        intervals=(
            EngagementUnitId(
                start=datetime(2000, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=POSITIVE_INFINITY,
                value="ABCD",
            ),
        )
    )

    assert engagement_timeline.eng_type == Timeline[EngagementType](
        intervals=(
            EngagementType(
                start=datetime(2000, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2022, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value=EngType.HOURLY,
            ),
            EngagementType(
                start=datetime(2022, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=POSITIVE_INFINITY,
                value=EngType.MONTHLY_FULL_TIME,
            ),
        )
    )


async def test_get_engagement_timeline_no_person_found():
    # Act
    engagement_timeline = await get_employment_timeline(
        GetEmploymentChangedResponse.parse_obj({"Person": []})
    )

    # Assert
    assert engagement_timeline == EngagementTimeline(
        eng_active=Timeline[Active](),
        eng_key=Timeline[EngagementKey](),
        eng_name=Timeline[EngagementName](),
        eng_unit=Timeline[EngagementUnit](),
    )


async def test_get_engagement_timeline_no_employment_found():
    # Arrange
    sd_resp = GetEmploymentChangedResponse.parse_obj(
        {
            "Person": [
                {
                    "PersonCivilRegistrationIdentifier": "0101011234",
                    "Employment": [],
                }
            ]
        }
    )

    # Act
    engagement_timeline = await get_employment_timeline(sd_resp)

    # Assert
    assert engagement_timeline == EngagementTimeline(
        eng_active=Timeline[Active](),
        eng_key=Timeline[EngagementKey](),
        eng_name=Timeline[EngagementName](),
        eng_unit=Timeline[EngagementUnit](),
    )


async def test_get_leave_timeline(mock_sd_emp_resp_dict):
    # Act
    engagement_timeline = await get_leave_timeline(
        GetEmploymentChangedResponse.parse_obj(mock_sd_emp_resp_dict)
    )

    # Assert
    assert engagement_timeline.leave_active == Timeline[Active](
        intervals=(
            Active(
                start=datetime(2002, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2003, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value=True,
            ),
        )
    )


@pytest.mark.parametrize(
    "salaried_indicator, full_time_indicator, expected_eng_type",
    [
        (False, None, EngType.HOURLY),
        (True, None, EngType.MONTHLY_PART_TIME),
        (True, False, EngType.MONTHLY_PART_TIME),
        (True, True, EngType.MONTHLY_FULL_TIME),
    ],
)
def test__sd_employment_type(
    salaried_indicator: bool,
    full_time_indicator: bool | None,
    expected_eng_type: EngType,
):
    # Arrange
    worktime = WorkingTime(
        ActivationDate=date.today(),
        DeactivationDate=date.today(),
        OccupationRate=Decimal("1.0000"),
        SalaryRate=Decimal("1.0000"),
        SalariedIndicator=salaried_indicator,
        FullTimeIndicator=full_time_indicator,
    )

    # Act
    eng_type = _sd_employment_type(worktime)

    # Assert
    assert eng_type == expected_eng_type
