# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import uuid4
from zoneinfo import ZoneInfo

from sdtoolplus.depends import GraphQLClient
from sdtoolplus.models import Active
from sdtoolplus.models import AssociationTimeline
from sdtoolplus.models import EngagementSDUnit
from sdtoolplus.models import EngagementTimeline
from sdtoolplus.models import Timeline
from sdtoolplus.sync.association import _sync_association_intervals


@patch.object(AssociationTimeline, "has_required_mo_values")
@patch("sdtoolplus.sync.association.terminate_association")
@patch("sdtoolplus.sync.association.get_mo_association_timeline")
@patch("sdtoolplus.sync.association.get_class")
async def test_sync_association_intervals_no_terminate_when_mo_not_active(
    mock_get_class: AsyncMock,
    mock_get_mo_association_timeline: AsyncMock,
    mock_terminate_association: AsyncMock,
    mock_has_required_mo_values: MagicMock,
) -> None:
    """
    The association must only be terminated in MO if it is actually active there.

    The SD association timeline is derived from the engagement timeline, where
    'association_active' comes from the SD 'active' timeline and 'association_unit'
    from the SD unit timeline. These can have different validity intervals. Here the SD
    and MO 'active' timelines are identical ([t1, t2)), but the SD unit timeline extends
    past the active period ([t1, t3)). This creates a trailing interval [t2, t3) where
    the association is inactive but has a unit value. The association must not be
    terminated in [t2, t3), since it is not active there.

    We are testing this scenario:

    Time  -------------------------t1------t2--------------t3-------->

    MO (active/unit)               |---1---|

    SD (active)                    |---1---|
    SD (unit)                      |------------dep1-------|
    """
    # Arrange
    tz = ZoneInfo("Europe/Copenhagen")

    t1 = datetime(2020, 1, 1, tzinfo=tz)
    t2 = datetime(2025, 1, 1, tzinfo=tz)
    t3 = datetime(2027, 1, 1, tzinfo=tz)

    dep1_uuid = uuid4()

    mock_gql_client = AsyncMock(spec=GraphQLClient)
    mock_get_class.return_value = uuid4()

    # The desired (SD) association is derived from the engagement timeline: the
    # 'active' timeline ends at t2, but the unit timeline extends to t3
    desired_eng_timeline = EngagementTimeline(
        eng_active=Timeline[Active](intervals=(Active(start=t1, end=t2, value=True),)),
        eng_sd_unit=Timeline[EngagementSDUnit](
            intervals=(EngagementSDUnit(start=t1, end=t3, value=dep1_uuid),)
        ),
    )

    # The MO association is active in [t1, t2), matching the SD 'active' timeline
    mock_get_mo_association_timeline.return_value = AssociationTimeline(
        association_active=Timeline[Active](
            intervals=(Active(start=t1, end=t2, value=True),)
        ),
        association_unit=Timeline[EngagementSDUnit](
            intervals=(EngagementSDUnit(start=t1, end=t2, value=dep1_uuid),)
        ),
    )

    # Act
    await _sync_association_intervals(
        gql_client=mock_gql_client,
        person=uuid4(),
        user_key="12345",
        desired_eng_timeline=desired_eng_timeline,
    )

    # Assert
    # The only differing interval, [t2, t3), is one where the association is not
    # active in MO, so it must not be terminated
    mock_terminate_association.assert_not_awaited()
    # The 'continue' must short-circuit the interval, so we never reach the
    # create/update path
    mock_has_required_mo_values.assert_not_called()
