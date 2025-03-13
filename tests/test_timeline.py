# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from sdtoolplus.models import Active
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitId
from sdtoolplus.models import UnitLevel
from sdtoolplus.models import UnitName
from sdtoolplus.models import UnitParent
from sdtoolplus.models import UnitTimeline
from sdtoolplus.timeline import _get_ou_interval_endpoints


def test__get_ou_interval_endpoints():
    # Arrange
    tz = ZoneInfo("Europe/Copenhagen")

    t1 = datetime(1990, 1, 1, tzinfo=tz)
    t2 = datetime(1999, 1, 1, tzinfo=tz)
    t3 = datetime(2003, 1, 1, tzinfo=tz)
    t4 = datetime(2004, 1, 1, tzinfo=tz)
    t5 = datetime(2005, 1, 1, tzinfo=tz)
    t6 = datetime(2006, 1, 1, tzinfo=tz)
    t7 = datetime(2007, 1, 1, tzinfo=tz)

    ou_timeline = UnitTimeline(
        active=Timeline[Active](
            intervals=(
                Active(start=t1, end=t2, value=True),
                Active(start=t2, end=t3, value=False),
            )
        ),
        name=Timeline[UnitName](
            intervals=(
                UnitName(start=t1, end=t3, value="name1"),
                UnitName(start=t3, end=t4, value="name2"),
            )
        ),
        unit_id=Timeline[UnitId](
            intervals=(
                UnitId(start=t5, end=t6, value="id1"),
                UnitId(start=t6, end=t7, value="id2"),
            )
        ),
        unit_level=Timeline[UnitLevel](
            intervals=(
                UnitLevel(start=t5, end=t6, value="level1"),
                UnitLevel(start=t6, end=t7, value="level2"),
            )
        ),
        parent=Timeline[UnitParent](
            intervals=(
                UnitParent(start=t5, end=t6, value=uuid4()),
                UnitParent(start=t6, end=t7, value=uuid4()),
            )
        ),
    )

    # Act
    endpoints = _get_ou_interval_endpoints(ou_timeline)

    # Assert
    assert endpoints == {t1, t2, t3, t4, t5, t6, t7}
