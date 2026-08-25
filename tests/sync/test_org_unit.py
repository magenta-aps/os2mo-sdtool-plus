# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from unittest.mock import AsyncMock
from unittest.mock import patch
from uuid import uuid4
from zoneinfo import ZoneInfo

from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.depends import GraphQLClient
from sdtoolplus.models import Active
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitId
from sdtoolplus.models import UnitLevel
from sdtoolplus.models import UnitName
from sdtoolplus.models import UnitParent
from sdtoolplus.models import UnitTimeline
from sdtoolplus.sync.org_unit import sync_ou_intervals


@patch("sdtoolplus.sync.org_unit.terminate_ou")
async def test_sync_ou_intervals_no_terminate_when_mo_not_active(
    mock_terminate_ou: AsyncMock,
    sdtoolplus_settings: SDToolPlusSettings,
) -> None:
    """
    An org unit must only be terminated in MO if it is actually active there.

    The SD 'active'/name/id/level timelines and the SD 'parent' timeline can have
    different validity intervals. Here the SD and MO 'active' timelines are identical
    ([t1, t2)), but the SD 'parent' timeline extends past the active period
    ([t1, t3)). This creates a trailing interval [t2, t3) where the unit is inactive
    but has a parent value. The unit must not be terminated in [t2, t3), since it is
    not active there.

    We are testing this scenario:

    Time  ---------------------------t1----t2--------------t3-------->

    MO (active/name/id/level/parent) |--1--|

    SD (active/name/id/level)        |--1--|
    SD (parent)                      |----------parent-----|
    """
    # Arrange
    tz = ZoneInfo("Europe/Copenhagen")

    t1 = datetime(2020, 1, 1, tzinfo=tz)
    t2 = datetime(2025, 1, 1, tzinfo=tz)
    t3 = datetime(2027, 1, 1, tzinfo=tz)

    org_unit = uuid4()
    parent_uuid = uuid4()

    mock_gql_client = AsyncMock(spec=GraphQLClient)

    # The MO unit is active in [t1, t2)
    mo_unit_timeline = UnitTimeline(
        active=Timeline[Active](intervals=(Active(start=t1, end=t2, value=True),)),
        name=Timeline[UnitName](intervals=(UnitName(start=t1, end=t2, value="name1"),)),
        unit_id=Timeline[UnitId](intervals=(UnitId(start=t1, end=t2, value="dep1"),)),
        unit_level=Timeline[UnitLevel](
            intervals=(UnitLevel(start=t1, end=t2, value="NY0-niveau"),)
        ),
        parent=Timeline[UnitParent](
            intervals=(UnitParent(start=t1, end=t2, value=parent_uuid),)
        ),
    )

    # The desired (SD) timeline has the same 'active' timeline as MO ([t1, t2)), but
    # the parent timeline extends to t3
    desired_unit_timeline = UnitTimeline(
        active=Timeline[Active](intervals=(Active(start=t1, end=t2, value=True),)),
        name=Timeline[UnitName](intervals=(UnitName(start=t1, end=t2, value="name1"),)),
        unit_id=Timeline[UnitId](intervals=(UnitId(start=t1, end=t2, value="dep1"),)),
        unit_level=Timeline[UnitLevel](
            intervals=(UnitLevel(start=t1, end=t2, value="NY0-niveau"),)
        ),
        parent=Timeline[UnitParent](
            intervals=(UnitParent(start=t1, end=t3, value=parent_uuid),)
        ),
    )

    # Act
    await sync_ou_intervals(
        gql_client=mock_gql_client,
        settings=sdtoolplus_settings,
        org_unit=org_unit,
        desired_unit_timeline=desired_unit_timeline,
        mo_unit_timeline=mo_unit_timeline,
        institution_identifier="II",
        priority=9000,
    )

    # Assert
    # The only differing interval, [t2, t3), is one where the unit is not active in
    # MO, so it must not be terminated
    mock_terminate_ou.assert_not_awaited()
