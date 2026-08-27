# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import uuid4
from zoneinfo import ZoneInfo

from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.depends import GraphQLClient
from sdtoolplus.models import Active
from sdtoolplus.models import EngagementKey
from sdtoolplus.models import EngagementName
from sdtoolplus.models import EngagementSDUnit
from sdtoolplus.models import EngagementTimeline
from sdtoolplus.models import EngagementType
from sdtoolplus.models import EngagementUnit
from sdtoolplus.models import EngagementUnitId
from sdtoolplus.models import EngType
from sdtoolplus.models import LeaveTimeline
from sdtoolplus.models import Timeline
from sdtoolplus.sync.engagement import _sync_eng_intervals


@patch.object(EngagementTimeline, "has_required_mo_values")
@patch("sdtoolplus.sync.engagement.terminate_leave_before_engagement_termination")
@patch("sdtoolplus.sync.engagement.terminate_engagement")
@patch("sdtoolplus.sync.engagement.get_engagement_types")
async def test_sync_eng_intervals_no_terminate_when_mo_not_active(
    mock_get_engagement_types: AsyncMock,
    mock_terminate_engagement: AsyncMock,
    mock_terminate_leave: AsyncMock,
    mock_has_required_mo_values: MagicMock,
    sdtoolplus_settings: SDToolPlusSettings,
) -> None:
    """
    The engagement must only be terminated in MO if it is actually active there.

    The SD 'active' timeline (from EmploymentStatus) and the SD unit timelines (from
    EmploymentDepartment) can have different validity intervals. Here the SD and MO
    'active' timelines are identical ([t1, t2)), but the SD unit timelines extend past
    the active period ([t1, t3)). This creates a trailing interval [t2, t3) where the
    engagement is inactive but has a unit value. The engagement must not be terminated
    in [t2, t3), since it is not active there.

    We are testing this scenario:

    Time  -------------------------t1------t2--------------t3-------->

    MO (active/name/key/unit/type) |---1---|

    SD (active/name/key/type)      |---1---|
    SD (unit)                      |------------dep1-------|
    """
    # Arrange
    tz = ZoneInfo("Europe/Copenhagen")

    t1 = datetime(2020, 1, 1, tzinfo=tz)
    t2 = datetime(2025, 1, 1, tzinfo=tz)
    t3 = datetime(2027, 1, 1, tzinfo=tz)

    dep1_uuid = uuid4()

    mock_gql_client = AsyncMock(spec=GraphQLClient)
    mock_get_engagement_types.return_value = {}

    # The MO engagement is active in [t1, t2)
    mo_eng_timeline = EngagementTimeline(
        eng_active=Timeline[Active](intervals=(Active(start=t1, end=t2, value=True),)),
        eng_key=Timeline[EngagementKey](
            intervals=(EngagementKey(start=t1, end=t2, value="1234"),)
        ),
        eng_name=Timeline[EngagementName](
            intervals=(EngagementName(start=t1, end=t2, value="name1"),)
        ),
        eng_unit=Timeline[EngagementUnit](
            intervals=(EngagementUnit(start=t1, end=t2, value=dep1_uuid),)
        ),
        eng_sd_unit=Timeline[EngagementSDUnit](
            intervals=(EngagementSDUnit(start=t1, end=t2, value=dep1_uuid),)
        ),
        eng_unit_id=Timeline[EngagementUnitId](
            intervals=(EngagementUnitId(start=t1, end=t2, value="dep1"),)
        ),
        eng_type=Timeline[EngagementType](
            intervals=(
                EngagementType(start=t1, end=t2, value=EngType.MONTHLY_FULL_TIME),
            )
        ),
    )

    # The desired (SD) timeline has the same 'active' timeline as MO ([t1, t2)), but
    # the unit timelines extend to t3
    desired_eng_timeline = EngagementTimeline(
        eng_active=Timeline[Active](intervals=(Active(start=t1, end=t2, value=True),)),
        eng_key=Timeline[EngagementKey](
            intervals=(EngagementKey(start=t1, end=t2, value="1234"),)
        ),
        eng_name=Timeline[EngagementName](
            intervals=(EngagementName(start=t1, end=t2, value="name1"),)
        ),
        eng_unit=Timeline[EngagementUnit](
            intervals=(EngagementUnit(start=t1, end=t3, value=dep1_uuid),)
        ),
        eng_sd_unit=Timeline[EngagementSDUnit](
            intervals=(EngagementSDUnit(start=t1, end=t3, value=dep1_uuid),)
        ),
        eng_unit_id=Timeline[EngagementUnitId](
            intervals=(EngagementUnitId(start=t1, end=t3, value="dep1"),)
        ),
        eng_type=Timeline[EngagementType](
            intervals=(
                EngagementType(start=t1, end=t2, value=EngType.MONTHLY_FULL_TIME),
            )
        ),
    )

    # Act
    await _sync_eng_intervals(
        gql_client=mock_gql_client,
        person=uuid4(),
        institution_identifier="II",
        employment_identifier="12345",
        desired_eng_timeline=desired_eng_timeline,
        mo_eng_timeline=mo_eng_timeline,
        mo_leave_timeline=LeaveTimeline(),
        settings=sdtoolplus_settings,
    )

    # Assert
    # The only differing interval, [t2, t3), is one where the engagement is not
    # active in MO, so it must not be terminated
    mock_terminate_engagement.assert_not_awaited()
    mock_terminate_leave.assert_not_awaited()
    # The 'continue' must short-circuit the interval, so we never reach the
    # create/update path
    mock_has_required_mo_values.assert_not_called()
