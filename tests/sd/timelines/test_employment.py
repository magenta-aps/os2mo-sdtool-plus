# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import date
from datetime import datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sdclient.responses import GetEmploymentChangedResponse
from sdclient.responses import WorkingTime

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
from sdtoolplus.sd.timelines.employment import _sd_employment_type_monthly_hourly
from sdtoolplus.sd.timelines.employment import get_employment_timeline
from sdtoolplus.sd.timelines.employment import get_leave_timeline
from sdtoolplus.sd.tree import ASSUMED_SD_TIMEZONE


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
    eng_type = _sd_employment_type_monthly_hourly(worktime)

    # Assert
    assert eng_type == expected_eng_type


async def test_get_engagement_timeline(mock_sd_employment_response_dict):
    # Act
    engagement_timeline = get_employment_timeline(
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
    engagement_timeline = get_employment_timeline(
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
    engagement_timeline = get_employment_timeline(sd_resp)

    # Assert
    assert engagement_timeline == EngagementTimeline(
        eng_active=Timeline[Active](),
        eng_key=Timeline[EngagementKey](),
        eng_name=Timeline[EngagementName](),
        eng_unit=Timeline[EngagementUnit](),
    )


async def test_get_leave_timeline(mock_sd_employment_response_dict):
    # Act
    engagement_timeline = get_leave_timeline(
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
