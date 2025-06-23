# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import date
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from pydantic import parse_obj_as
from respx import MockRouter
from sdclient.client import SDClient
from sdclient.exceptions import SDParentNotFound
from sdclient.responses import DepartmentParentHistoryObj
from sdclient.responses import GetDepartmentResponse
from sdclient.responses import GetEmploymentChangedResponse
from sdclient.responses import WorkingTime

from sdtoolplus.exceptions import DepartmentParentsNotFoundError
from sdtoolplus.exceptions import DepartmentValidityExceedsParentsValiditiesError
from sdtoolplus.exceptions import HolesInDepartmentParentsTimelineError
from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
from sdtoolplus.models import POSITIVE_INFINITY
from sdtoolplus.models import Active
from sdtoolplus.models import EngagementKey
from sdtoolplus.models import EngagementName
from sdtoolplus.models import EngagementSDUnit
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
from sdtoolplus.models import UnitPhoneNumber
from sdtoolplus.models import UnitTimeline
from sdtoolplus.sd.timeline import _sd_employment_type
from sdtoolplus.sd.timeline import get_department
from sdtoolplus.sd.timeline import get_department_timeline
from sdtoolplus.sd.timeline import get_employment_timeline
from sdtoolplus.sd.timeline import get_leave_timeline
from sdtoolplus.sd.timeline import get_phone_number_timeline
from sdtoolplus.sd.tree import ASSUMED_SD_TIMEZONE
from sdtoolplus.timeline import engagement_ou_strategy_elevate_to_ny_level


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
    mock_sd_client.get_department_parent_history.return_value = parse_obj_as(
        list[DepartmentParentHistoryObj], sd_parent_history_resp
    )

    # Act
    department_timeline = await get_department_timeline(
        department=GetDepartmentResponse.parse_obj(sd_dep_resp_dict),
        sd_client=mock_sd_client,
        inst_id="II",
        unit_uuid=dep_uuid,
    )

    # Assert
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

    # Act
    department_timeline = await get_department_timeline(
        department=None, sd_client=mock_sd_client, inst_id="II", unit_uuid=dep_uuid
    )

    # Assert
    assert department_timeline == UnitTimeline()


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
    mock_sd_client.get_department_parent_history.side_effect = SDParentNotFound(
        "Parent history not found!"
    )

    # Act
    department_timeline = await get_department_timeline(
        department=GetDepartmentResponse.parse_obj(sd_dep_resp_dict),
        sd_client=mock_sd_client,
        inst_id="II",
        unit_uuid=dep_uuid,
    )

    # Assert
    assert department_timeline == UnitTimeline(
        active=Timeline[Active](),
        name=Timeline[UnitName](),
        unit_id=Timeline[UnitId](),
        unit_level=Timeline[UnitLevel](),
        parent=Timeline[UnitParent](),
    )


async def test_get_engagement_timeline(mock_sd_employment_response_dict):
    # Act
    engagement_timeline = await get_employment_timeline(
        GetEmploymentChangedResponse.parse_obj(mock_sd_employment_response_dict)
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


async def test_get_leave_timeline(mock_sd_employment_response_dict):
    # Act
    engagement_timeline = await get_leave_timeline(
        GetEmploymentChangedResponse.parse_obj(mock_sd_employment_response_dict)
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


async def test_get_department_empty_department_list():
    # Arrange
    mock_sd_client = MagicMock()
    mock_sd_client.get_department = MagicMock(
        return_value=GetDepartmentResponse(
            RegionIdentifier="RI", InstitutionIdentifier="II", Department=[]
        )
    )

    # Act
    response = await get_department(
        sd_client=mock_sd_client, institution_identifier="II", unit_uuid=uuid4()
    )

    # Assert
    assert response is None


@pytest.mark.parametrize(
    "phone_numbers",
    [
        ["12345678", "23456789"],
        ["12345678"],
    ],
)
def test_get_phone_number_timeline(phone_numbers: list[str]):
    # Arrange
    department = GetDepartmentResponse.parse_obj(
        {
            "RegionIdentifier": "RI",
            "InstitutionIdentifier": "II",
            "Department": [
                {
                    "ActivationDate": "2000-01-01",
                    "DeactivationDate": "2000-12-31",
                    "DepartmentIdentifier": "ABCD",
                    "DepartmentLevelIdentifier": "Afdelings-niveau",
                    "ContactInformation": {"TelephoneNumberIdentifier": phone_numbers},
                }
            ],
        }
    )

    # Act
    timeline = get_phone_number_timeline(department)

    # Assert
    assert timeline == Timeline[UnitPhoneNumber](
        intervals=(
            UnitPhoneNumber(
                start=datetime(2000, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2001, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value="12345678",
            ),
        )
    )


@pytest.mark.parametrize(
    "contact_information",
    [
        None,
        {"TelephoneNumberIdentifier": None},
        {"TelephoneNumberIdentifier": ["00000000", "23456789"]},
    ],
)
def test_get_phone_number_should_return_empty_timeline(
    contact_information: dict[str, Any] | None,
):
    # Arrange
    department = GetDepartmentResponse.parse_obj(
        {
            "RegionIdentifier": "RI",
            "InstitutionIdentifier": "II",
            "Department": [
                {
                    "ActivationDate": "2000-01-01",
                    "DeactivationDate": "2000-12-31",
                    "DepartmentIdentifier": "ABCD",
                    "DepartmentLevelIdentifier": "Afdelings-niveau",
                    "ContactInformation": contact_information,
                }
            ],
        }
    )

    # Act
    timeline = get_phone_number_timeline(department)

    # Assert
    assert timeline == Timeline[UnitPhoneNumber]()


async def test_engagement_ou_strategy_elevate_to_ny_level(respx_mock: MockRouter):
    """
    We are testing this scenario:

    Time       ------t1--t2--t3----t4-------t5-t6-t7------t8--------------------t9-t10-

    SD emp unit:         |---------afd1-----------|-----------afd2--------------|

    Parent (afd1):   |------N1-----|---N2---|------N3-----------------------------------
    Parent (afd2):           |-------N4--------|-----N5---|----------N6------------|-N7-

    Desired eng unit:    |----N1---|---N2---|-N3--|---N5--|----------N6---------|

    """
    # Arrange
    tz = ZoneInfo("Europe/Copenhagen")

    t2 = datetime(2002, 1, 1, tzinfo=tz)
    t4 = datetime(2004, 1, 1, tzinfo=tz)
    t5 = datetime(2005, 1, 1, tzinfo=tz)
    t7 = datetime(2007, 1, 1, tzinfo=tz)
    t8 = datetime(2008, 1, 1, tzinfo=tz)
    t9 = datetime(2009, 1, 1, tzinfo=tz)

    adf1 = UUID("afd10000-0000-0000-0000-000000000000")
    adf2 = UUID("afd20000-0000-0000-0000-000000000000")

    # Prepare the SD engagement timeline
    eng_active_timeline = Timeline[Active](
        intervals=(Active(start=t2, end=t9, value=True),)
    )
    eng_key_timeline = Timeline[EngagementKey](
        intervals=(EngagementKey(start=t2, end=t9, value="key"),)
    )
    eng_name_timeline = Timeline[EngagementName](
        intervals=(EngagementName(start=t2, end=t9, value="name"),)
    )
    eng_unit_timeline = Timeline[EngagementUnit](
        intervals=(
            EngagementUnit(start=t2, end=t7, value=adf1),
            EngagementUnit(start=t7, end=t9, value=adf2),
        )
    )
    eng_sd_unit_timeline = Timeline[EngagementSDUnit](
        intervals=(
            EngagementSDUnit(start=t2, end=t7, value=adf1),
            EngagementSDUnit(start=t7, end=t9, value=adf2),
        )
    )
    eng_unit_id_timeline = Timeline[EngagementUnitId](
        intervals=(
            EngagementUnitId(start=t2, end=t7, value="afd1"),
            EngagementUnitId(start=t7, end=t9, value="afd2"),
        )
    )
    eng_type_timeline = Timeline[EngagementType](
        intervals=(EngagementType(start=t2, end=t9, value=EngType.MONTHLY_FULL_TIME),)
    )

    sd_eng_timeline = EngagementTimeline(
        eng_active=eng_active_timeline,
        eng_key=eng_key_timeline,
        eng_name=eng_name_timeline,
        eng_unit=eng_unit_timeline,
        eng_sd_unit=eng_sd_unit_timeline,
        eng_unit_id=eng_unit_id_timeline,
        eng_type=eng_type_timeline,
    )

    # Prepare the get-department-parent-history responses
    n1 = UUID("10000000-0000-0000-0000-000000000000")
    n2 = UUID("20000000-0000-0000-0000-000000000000")
    n3 = UUID("30000000-0000-0000-0000-000000000000")
    n4 = UUID("40000000-0000-0000-0000-000000000000")
    n5 = UUID("50000000-0000-0000-0000-000000000000")
    n6 = UUID("60000000-0000-0000-0000-000000000000")
    n7 = UUID("60000000-0000-0000-0000-000000000000")

    respx_mock.get(
        f"https://service.sd.dk/api-gateway/organization/public/api/v1/organizations/uuids/{str(adf1)}/department-parent-history"
    ).respond(
        json=[
            {
                "startDate": "2001-01-01",
                "endDate": "2003-12-31",
                "parentUuid": str(n1),
            },
            {
                "startDate": "2004-01-01",
                "endDate": "2004-12-31",
                "parentUuid": str(n2),
            },
            {
                "startDate": "2005-01-01",
                "endDate": "9999-12-31",
                "parentUuid": str(n3),
            },
        ],
    )

    respx_mock.get(
        f"https://service.sd.dk/api-gateway/organization/public/api/v1/organizations/uuids/{str(adf2)}/department-parent-history"
    ).respond(
        json=[
            {
                "startDate": "2003-01-01",
                "endDate": "2005-12-31",
                "parentUuid": str(n4),
            },
            {
                "startDate": "2006-01-01",
                "endDate": "2007-12-31",
                "parentUuid": str(n5),
            },
            {
                "startDate": "2008-01-01",
                "endDate": "2009-12-31",
                "parentUuid": str(n6),
            },
            {
                "startDate": "2010-01-01",
                "endDate": "9999-12-31",
                "parentUuid": str(n7),
            },
        ],
    )

    sd_client = SDClient(sd_username="user", sd_password="secret")

    # Act
    desired_eng_timeline = await engagement_ou_strategy_elevate_to_ny_level(
        sd_client=sd_client, sd_eng_timeline=sd_eng_timeline
    )

    # Assert
    assert desired_eng_timeline == EngagementTimeline(
        eng_active=eng_active_timeline,
        eng_key=eng_key_timeline,
        eng_name=eng_name_timeline,
        eng_unit=Timeline[EngagementUnit](
            intervals=(
                EngagementUnit(start=t2, end=t4, value=n1),
                EngagementUnit(start=t4, end=t5, value=n2),
                EngagementUnit(start=t5, end=t7, value=n3),
                EngagementUnit(start=t7, end=t8, value=n5),
                EngagementUnit(start=t8, end=t9, value=n6),
            )
        ),
        eng_sd_unit=eng_sd_unit_timeline,
        eng_unit_id=eng_unit_id_timeline,
        eng_type=eng_type_timeline,
    )


async def test_engagement_ou_strategy_elevate_to_ny_level_raise_exception_for_holes():
    """
    We are testing this scenario:

    Time       ------t1--t2--------t3-------t4----t5------------------------------------

    SD emp unit:         |---------afd1-----------|
    Parent (afd1):   |------N1-----|        |------N2-----------------------------------
                                     (hole!)

    """
    # Arrange
    tz = ZoneInfo("Europe/Copenhagen")

    t1 = datetime(2001, 1, 1, tzinfo=tz)
    t2 = datetime(2002, 1, 1, tzinfo=tz)
    t3 = datetime(2003, 1, 1, tzinfo=tz)
    t4 = datetime(2004, 1, 1, tzinfo=tz)
    t5 = datetime(2005, 1, 1, tzinfo=tz)

    adf1 = UUID("afd10000-0000-0000-0000-000000000000")

    # Prepare the SD engagement timeline
    eng_unit_timeline = Timeline[EngagementUnit](
        intervals=(EngagementUnit(start=t2, end=t5, value=adf1),)
    )

    sd_eng_timeline = EngagementTimeline(eng_unit=eng_unit_timeline)

    mock_sd_client = MagicMock(spec=SDClient)
    mock_sd_client.get_department_parent_history.return_value = [
        DepartmentParentHistoryObj(
            startDate=t1.date(),
            endDate=t3.date() - timedelta(days=1),
            parentUuid=uuid4(),
        ),
        # Hole in the parent timeline here!
        DepartmentParentHistoryObj(
            startDate=t4.date(),
            endDate=date.max,
            parentUuid=uuid4(),
        ),
    ]

    # Act + Assert
    with pytest.raises(HolesInDepartmentParentsTimelineError):
        await engagement_ou_strategy_elevate_to_ny_level(
            sd_client=mock_sd_client, sd_eng_timeline=sd_eng_timeline
        )


async def test_engagement_ou_strategy_elevate_to_ny_level_parents_not_found():
    """
    We are testing this scenario:

    Time       ----------t1-----------------------t2------------------------------------

    SD emp unit:         |---------afd1-----------|
    Parent (afd1):               (not found)

    """
    # Arrange
    tz = ZoneInfo("Europe/Copenhagen")

    t1 = datetime(2001, 1, 1, tzinfo=tz)
    t2 = datetime(2002, 1, 1, tzinfo=tz)

    adf1 = UUID("afd10000-0000-0000-0000-000000000000")

    # Prepare the SD engagement timeline
    eng_unit_timeline = Timeline[EngagementUnit](
        intervals=(EngagementUnit(start=t1, end=t2, value=adf1),)
    )

    sd_eng_timeline = EngagementTimeline(eng_unit=eng_unit_timeline)

    mock_sd_client = MagicMock(spec=SDClient)
    mock_sd_client.get_department_parent_history.side_effect = SDParentNotFound()

    # Act + Assert
    with pytest.raises(DepartmentParentsNotFoundError):
        await engagement_ou_strategy_elevate_to_ny_level(
            sd_client=mock_sd_client, sd_eng_timeline=sd_eng_timeline
        )


async def test_engagement_ou_strategy_elevate_to_ny_level_department_exceeds_parents():
    """
    We are testing this scenario:

    Time       ----------t1---t2------------t3----t4----------------------------------

    SD emp unit:         |---------afd1-----------|
    Parent (afd1):            |------N1-----|

    """
    # Arrange
    tz = ZoneInfo("Europe/Copenhagen")

    t1 = datetime(2001, 1, 1, tzinfo=tz)
    t2 = datetime(2002, 1, 1, tzinfo=tz)
    t3 = datetime(2003, 1, 1, tzinfo=tz)
    t4 = datetime(2004, 1, 1, tzinfo=tz)

    adf1 = UUID("afd10000-0000-0000-0000-000000000000")

    # Prepare the SD engagement timeline
    eng_unit_timeline = Timeline[EngagementUnit](
        intervals=(EngagementUnit(start=t1, end=t4, value=adf1),)
    )

    sd_eng_timeline = EngagementTimeline(eng_unit=eng_unit_timeline)

    mock_sd_client = MagicMock(spec=SDClient)
    mock_sd_client.get_department_parent_history.return_value = [
        DepartmentParentHistoryObj(
            startDate=t2.date(),
            endDate=t3.date() - timedelta(days=1),
            parentUuid=uuid4(),
        ),
    ]

    # Act + Assert
    with pytest.raises(DepartmentValidityExceedsParentsValiditiesError):
        await engagement_ou_strategy_elevate_to_ny_level(
            sd_client=mock_sd_client, sd_eng_timeline=sd_eng_timeline
        )
