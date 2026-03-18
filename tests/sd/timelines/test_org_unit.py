# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from typing import Any
from typing import cast
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import parse_obj_as
from sdclient.exceptions import SDParentNotFound
from sdclient.responses import DepartmentParentHistoryObj
from sdclient.responses import GetDepartmentResponse

from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
from sdtoolplus.models import POSITIVE_INFINITY
from sdtoolplus.models import Active
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitId
from sdtoolplus.models import UnitLevel
from sdtoolplus.models import UnitName
from sdtoolplus.models import UnitParent
from sdtoolplus.models import UnitPhoneNumber
from sdtoolplus.models import UnitTimeline
from sdtoolplus.sd.timelines.org_unit import condense_multiple_parents_to_unknown_unit
from sdtoolplus.sd.timelines.org_unit import get_department
from sdtoolplus.sd.timelines.org_unit import get_department_timeline
from sdtoolplus.sd.timelines.org_unit import get_phone_number_timeline
from sdtoolplus.sd.tree import ASSUMED_SD_TIMEZONE


def test_condense_multiple_parents_to_unknown_unit_case_with_no_overlaps() -> None:
    """
    Ensure that the function condense_multiple_parents_to_unknown_unit does change
    anything when there are no SD department parent overlaps.
    """
    # Arrange
    t1 = datetime(2001, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE)
    t2 = datetime(2002, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE)
    t3 = datetime(2003, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE)
    t4 = datetime(2004, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE)

    parent1 = cast(OrgUnitUUID, uuid4())
    parent2 = cast(OrgUnitUUID, uuid4())
    parent3 = cast(OrgUnitUUID, uuid4())
    unknown_unit = cast(OrgUnitUUID, uuid4())

    # No overlaps in this one
    parent_intervals = (
        UnitParent(start=t1, end=t2, value=parent1),
        UnitParent(start=t2, end=t3, value=parent2),
        UnitParent(start=t3, end=t4, value=parent3),
    )

    # Act
    condensed_parent_intervals = condense_multiple_parents_to_unknown_unit(
        parent_intervals=parent_intervals,
        unknown_unit=unknown_unit,
    )

    # Assert
    assert condensed_parent_intervals == parent_intervals


def test_condense_multiple_parents_to_unknown_unit_case_with_overlaps() -> None:
    """
    Ensure the function condense_multiple_parents_to_unknown_unit replaces the multiple
    parents with the "unknown" unit in the intervals where the SD parents are
    overlapping.

    The test uses the complicated SD get-department-history-response below.
    p1, p2, p3 etc. indicates parent1, parent2, parent3 and so on.
    U indicates the unknown unit.

    Time  ----t1-----t2-----t3-----t4-----t5-----t6-----t7-----t8-----t9----->
              |------p1-----|------p2-----|      |------p3-----|--p4--|
                     |------p5-----|                    |------p6-----|

    Which should result in:
              |--p1--|------U------|--p2--|      |--p3--|------U------|
    """
    # Arrange
    t1 = datetime(2001, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE)
    t2 = datetime(2002, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE)
    t3 = datetime(2003, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE)
    t4 = datetime(2004, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE)
    t5 = datetime(2005, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE)
    t6 = datetime(2006, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE)
    t7 = datetime(2007, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE)
    t8 = datetime(2008, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE)
    t9 = datetime(2009, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE)

    parent1 = OrgUnitUUID(int=1)
    parent2 = OrgUnitUUID(int=2)
    parent3 = OrgUnitUUID(int=3)
    parent4 = OrgUnitUUID(int=4)
    parent5 = OrgUnitUUID(int=5)
    parent6 = OrgUnitUUID(int=6)
    unknown_unit = OrgUnitUUID(int=0)

    # Lots of overlaps in this one
    parent_intervals = (
        UnitParent(start=t1, end=t3, value=parent1),
        UnitParent(start=t3, end=t5, value=parent2),
        UnitParent(start=t6, end=t8, value=parent3),
        UnitParent(start=t8, end=t9, value=parent4),
        UnitParent(start=t2, end=t4, value=parent5),
        UnitParent(start=t7, end=t9, value=parent6),
    )

    # Act
    condensed_parent_intervals = condense_multiple_parents_to_unknown_unit(
        parent_intervals=parent_intervals,
        unknown_unit=unknown_unit,
    )

    # Assert
    assert condensed_parent_intervals == (
        UnitParent(start=t1, end=t2, value=parent1),
        UnitParent(start=t2, end=t4, value=unknown_unit),
        UnitParent(start=t4, end=t5, value=parent2),
        UnitParent(start=t6, end=t7, value=parent3),
        UnitParent(start=t7, end=t9, value=unknown_unit),
    )


async def test_get_department_timeline(sdtoolplus_settings):
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
        settings=sdtoolplus_settings,
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


async def test_get_department_timeline_department_not_found(sdtoolplus_settings):
    # Arrange
    dep_uuid = uuid4()

    mock_sd_client = MagicMock()

    # Act
    department_timeline = await get_department_timeline(
        department=None,
        sd_client=mock_sd_client,
        inst_id="II",
        unit_uuid=dep_uuid,
        settings=sdtoolplus_settings,
    )

    # Assert
    assert department_timeline == UnitTimeline()


async def test_get_department_timeline_parent_not_found(sdtoolplus_settings):
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
        settings=sdtoolplus_settings,
    )

    # Assert
    assert department_timeline == UnitTimeline(
        active=Timeline[Active](),
        name=Timeline[UnitName](),
        unit_id=Timeline[UnitId](),
        unit_level=Timeline[UnitLevel](),
        parent=Timeline[UnitParent](),
    )


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


def test_get_pnumber_timeline_when_pnumber_is_zero():
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
                    "ProductionUnitIdentifier": 0,
                }
            ],
        }
    )

    # Act
    timeline = get_phone_number_timeline(department)

    # Assert
    assert timeline == Timeline[UnitPhoneNumber]()
