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
from sdtoolplus.models import LeaveTimeline
from sdtoolplus.models import Timeline
from sdtoolplus.sync.leave import _sync_leave_intervals


@patch("sdtoolplus.sync.leave.terminate_leave")
async def test_sync_leave_intervals_no_terminate_when_mo_not_active(
    mock_terminate_leave: AsyncMock,
    sdtoolplus_settings: SDToolPlusSettings,
) -> None:
    """
    A leave must only be terminated in MO if it is actually active there.

    LeaveTimeline only has the single field 'leave_active', so - unlike the
    engagement, association and org unit cases - a realistic SD/MO leave timeline
    (which only carries "active" intervals) can never reach the terminate branch with
    an inactive MO leave. The 'and mo_is_active' guard is therefore defensive. We
    exercise it directly by giving MO a leave timeline that is explicitly inactive in
    [t1, t2) while SD has no leave there. The leave must not be terminated, since it
    is not active in MO.

    We are testing this scenario:

    Time  -------------------------t1------t2-------->

    MO (active=False)              |---0---|

    SD (no leave)
    """
    # Arrange
    tz = ZoneInfo("Europe/Copenhagen")

    t1 = datetime(2020, 1, 1, tzinfo=tz)
    t2 = datetime(2025, 1, 1, tzinfo=tz)

    mock_gql_client = AsyncMock(spec=GraphQLClient)

    # The leave type lookup and the corresponding engagement lookup both happen
    # before the sync loop
    leave_type = MagicMock()
    leave_type.uuid = uuid4()
    mock_gql_client.get_class.return_value.objects = [leave_type]

    eng = MagicMock()
    eng.uuid = uuid4()
    mock_gql_client.get_engagement_timeline.return_value.objects = [eng]

    # MO reports the leave as inactive in [t1, t2); SD has no leave at all
    mo_leave_timeline = LeaveTimeline(
        leave_active=Timeline[Active](
            intervals=(Active(start=t1, end=t2, value=False),)
        ),
    )
    sd_leave_timeline = LeaveTimeline()

    # Act
    await _sync_leave_intervals(
        gql_client=mock_gql_client,
        person=uuid4(),
        institution_identifier="II",
        employment_identifier="12345",
        sd_leave_timeline=sd_leave_timeline,
        mo_leave_timeline=mo_leave_timeline,
        settings=sdtoolplus_settings,
    )

    # Assert
    # The differing interval [t1, t2) is one where the leave is not active in MO, so
    # it must not be terminated
    mock_terminate_leave.assert_not_awaited()
