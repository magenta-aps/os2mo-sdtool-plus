# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from datetime import time
from datetime import timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from sdtoolplus.exceptions import NoValueError
from sdtoolplus.models import Active
from sdtoolplus.models import EngagementKey
from sdtoolplus.models import EngagementName
from sdtoolplus.models import EngagementTimeline
from sdtoolplus.models import EngagementType
from sdtoolplus.models import EngagementUnit
from sdtoolplus.models import EngagementUnitId
from sdtoolplus.models import EngType
from sdtoolplus.models import LeaveTimeline
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitId
from sdtoolplus.models import UnitLevel
from sdtoolplus.models import UnitName
from sdtoolplus.models import UnitParent
from sdtoolplus.models import UnitTimeline
from sdtoolplus.models import combine_intervals

TZ = ZoneInfo("Europe/London")
TODAY_START = datetime.combine(datetime.now(), time.min, tzinfo=TZ)
YESTERDAY_START = TODAY_START - timedelta(days=1)
TOMORROW_START = TODAY_START + timedelta(days=1)
DAY_AFTER_TOMORROW_START = TODAY_START + timedelta(days=2)

MINUS_INFINITY = datetime.min.replace(tzinfo=TZ)
INFINITY = datetime.max.replace(tzinfo=TZ)


def test_entity_eq():
    # Arrange
    active1 = Active(start=YESTERDAY_START, end=TODAY_START, value=True)
    active2 = Active(start=TODAY_START, end=TOMORROW_START, value=False)
    active3 = Active(start=TODAY_START, end=TOMORROW_START, value=True)
    active4 = Active(start=TOMORROW_START, end=TOMORROW_START, value=True)
    active5 = Active(start=TOMORROW_START, end=TOMORROW_START, value=True)

    # Act + Assert
    assert active1 == active1
    assert active1 != "Wrong object"
    assert active1 != active2
    assert active2 != active3
    assert active3 != active4
    assert active4 == active5


def test_timeline_eq():
    # Arrange
    active1 = Active(start=YESTERDAY_START, end=TODAY_START, value=True)
    active2 = Active(start=TODAY_START, end=TOMORROW_START, value=False)
    active3 = Active(start=TODAY_START, end=TOMORROW_START, value=True)
    active4 = Active(start=TOMORROW_START, end=DAY_AFTER_TOMORROW_START, value=False)

    timeline1 = Timeline(intervals=(active1, active2))
    timeline2 = Timeline(intervals=(active3, active4))
    timeline3 = Timeline(intervals=(active3, active4))

    # Act + Assert
    assert timeline1 == timeline1
    assert timeline1 != "Wrong object"
    assert timeline1 != timeline2
    assert timeline2 == timeline3


def test_combine_intervals():
    """
    --------------t1---------t2---------t3-------t4-------t5-----t6---------
    Input:        |----v1----|          |---v1---|---v1---|--v1--|---v2-----
    Output:       |----v1----|          |-----------v1-----------|---v2-----
    """
    # Arrange
    t1 = datetime(2001, 1, 1, tzinfo=TZ)
    t2 = datetime(2002, 1, 1, tzinfo=TZ)
    t3 = datetime(2003, 1, 1, tzinfo=TZ)
    t4 = datetime(2004, 1, 1, tzinfo=TZ)
    t5 = datetime(2005, 1, 1, tzinfo=TZ)
    t6 = datetime(2006, 1, 1, tzinfo=TZ)

    # Arrange
    intervals = (
        Active(start=t1, end=t2, value=True),
        Active(start=t3, end=t4, value=True),
        Active(start=t4, end=t5, value=True),
        Active(start=t5, end=t6, value=True),
        Active(start=t6, end=INFINITY, value=False),
    )

    # Act
    condensed = combine_intervals(intervals)

    # Assert
    assert condensed == (
        Active(start=t1, end=t2, value=True),
        Active(start=t3, end=t6, value=True),
        Active(start=t6, end=INFINITY, value=False),
    )


def test_combine_intervals_empty_input():
    # Act
    condensed = combine_intervals(tuple())

    # Assert
    assert condensed == tuple()


def test_combine_intervals_single_input():
    # Arrange
    intervals = (Active(start=MINUS_INFINITY, end=INFINITY, value=True),)

    # Act
    condensed = combine_intervals(intervals)

    # Assert
    assert condensed == intervals


def test_timeline_can_be_instantiated_correctly():
    # Arrange
    active1 = Active(start=YESTERDAY_START, end=TODAY_START, value=True)
    active2 = Active(start=TODAY_START, end=TOMORROW_START, value=False)

    # Act + Assert
    assert Timeline[Active](intervals=(active1, active2))


def test_timeline_entities_must_be_same_type():
    # Arrange
    active = Active(start=YESTERDAY_START, end=TODAY_START, value=True)
    unit_uuid = UnitName(start=TODAY_START, end=TOMORROW_START, value="name")

    # Act + Assert
    with pytest.raises(ValueError):
        Timeline[Active](intervals=(active, unit_uuid))


def test_timeline_entities_must_be_intervals():
    with pytest.raises(ValueError):
        Timeline[str](intervals=("Not interval", "Not interval"))


def test_timeline_elements_must_be_sorted():
    # Arrange
    active1 = Active(start=YESTERDAY_START, end=TODAY_START, value=True)
    active2 = Active(start=TODAY_START, end=TOMORROW_START, value=True)

    # Act + Assert
    with pytest.raises(ValueError):
        Timeline[Active](intervals=(active2, active1))


def test_timeline_intervals_cannot_overlap():
    # Arrange
    active1 = Active(start=YESTERDAY_START, end=TOMORROW_START, value=True)
    active2 = Active(start=TODAY_START, end=DAY_AFTER_TOMORROW_START, value=True)
    active3 = Active(start=TOMORROW_START, end=DAY_AFTER_TOMORROW_START, value=True)

    # Act + Assert
    with pytest.raises(ValueError):
        Timeline[Active](intervals=(active1, active2, active3))


def test_timeline_successively_repeated_interval_values_not_allowed():
    # Arrange
    active1 = Active(start=YESTERDAY_START, end=TODAY_START, value=True)
    active2 = Active(start=TODAY_START, end=TOMORROW_START, value=True)

    # Act + Assert
    with pytest.raises(ValueError):
        Timeline[Active](intervals=(active1, active2))


def test_timeline_successively_repeated_interval_allowed_when_holes_in_timeline():
    # Arrange
    active1 = Active(start=YESTERDAY_START, end=TODAY_START, value=True)
    active2 = Active(start=DAY_AFTER_TOMORROW_START, end=INFINITY, value=True)

    # Act + Assert
    assert Timeline[Active](intervals=(active1, active2))


@pytest.mark.parametrize(
    "timestamp, expected",
    [
        (
            YESTERDAY_START + timedelta(hours=12),
            Active(start=YESTERDAY_START, end=TODAY_START, value=True),
        ),
        (
            TODAY_START + timedelta(hours=12),
            Active(start=TODAY_START, end=TOMORROW_START, value=False),
        ),
    ],
)
def test_timeline_entity_at(timestamp: datetime, expected: Active):
    # Arrange
    active1 = Active(start=YESTERDAY_START, end=TODAY_START, value=True)
    active2 = Active(start=TODAY_START, end=TOMORROW_START, value=False)

    timeline = Timeline[Active](intervals=(active1, active2))

    # Act
    actual = timeline.entity_at(timestamp)

    # Assert
    assert actual == expected


def test_timeline_entity_at_no_value():
    # Arrange
    active1 = Active(start=YESTERDAY_START, end=TODAY_START, value=True)
    active2 = Active(start=TODAY_START, end=TOMORROW_START, value=False)

    timeline = Timeline[Active](intervals=(active1, active2))

    # Act + Assert
    with pytest.raises(NoValueError):
        timeline.entity_at(YESTERDAY_START - timedelta(hours=12))


def test_timeline_get_interval_endpoints():
    # Arrange
    t1 = datetime(2001, 1, 1, tzinfo=TZ)
    t2 = datetime(2002, 1, 1, tzinfo=TZ)
    t3 = datetime(2003, 1, 1, tzinfo=TZ)
    t4 = datetime(2004, 1, 1, tzinfo=TZ)

    # Arrange
    timeline = Timeline[Active](
        intervals=(
            Active(start=t1, end=t2, value=True),
            Active(start=t2, end=t3, value=False),
            Active(start=t3, end=t4, value=True),
        )
    )

    # Act
    endpoints = timeline.get_interval_endpoints()

    # Assert
    assert endpoints == {t1, t2, t3, t4}


def test_timeline_has_holes():
    # Arrange
    active1 = Active(start=YESTERDAY_START, end=TODAY_START, value=True)
    active2 = Active(start=TODAY_START, end=TOMORROW_START, value=False)
    active3 = Active(start=DAY_AFTER_TOMORROW_START, end=INFINITY, value=True)

    timeline_without_holes = Timeline[Active](intervals=(active1, active2))
    timeline_with_holes = Timeline[Active](intervals=(active1, active2, active3))

    # Act + Assert
    assert not timeline_without_holes.has_holes()
    assert timeline_with_holes.has_holes()


def test_unit_timeline_can_be_instantiated_with_empty_values():
    assert UnitTimeline() == UnitTimeline(
        active=Timeline[Active](),
        name=Timeline[UnitName](),
        unit_id=Timeline[UnitId](),
        unit_level=Timeline[UnitLevel](),
        parent=Timeline[UnitParent](),
    )


def test_engagement_timeline_can_be_instantiated_with_empty_values():
    assert EngagementTimeline() == EngagementTimeline(
        eng_active=Timeline[Active](),
        eng_key=Timeline[EngagementKey](),
        eng_name=Timeline[EngagementName](),
        eng_unit=Timeline[EngagementUnit](),
    )


def test_leave_timeline_get_interval_endpoints():
    # Arrange
    active1 = Active(start=YESTERDAY_START, end=TODAY_START, value=True)
    active2 = Active(start=TODAY_START, end=TOMORROW_START, value=False)

    leave_timeline = LeaveTimeline(
        leave_active=Timeline[Active](intervals=(active1, active2))
    )

    # Act
    endpoints = leave_timeline.get_interval_endpoints()

    # Assert
    assert endpoints == {YESTERDAY_START, TODAY_START, TOMORROW_START}


def test_engagement_timeline_get_interval_endpoints_engagement_type():
    # Arrange
    engagement_timeline = EngagementTimeline(
        eng_unit_id=Timeline[EngagementUnitId](
            intervals=(
                EngagementUnitId(
                    start=YESTERDAY_START,
                    end=DAY_AFTER_TOMORROW_START,
                    value="ABCD",
                ),
            )
        ),
        eng_type=Timeline[EngagementType](
            intervals=(
                EngagementType(
                    start=YESTERDAY_START,
                    end=TODAY_START,
                    value=EngType.MONTHLY_FULL_TIME,
                ),
                EngagementType(
                    start=TODAY_START,
                    end=TOMORROW_START,
                    value=EngType.MONTHLY_PART_TIME,
                ),
            )
        ),
    )

    # Act
    endpoints = engagement_timeline.get_interval_endpoints()

    # Assert
    assert endpoints == {
        YESTERDAY_START,
        TODAY_START,
        TOMORROW_START,
        DAY_AFTER_TOMORROW_START,
    }


def test_unit_timeline_get_ou_interval_endpoints():
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
    endpoints = ou_timeline.get_interval_endpoints()

    # Assert
    assert endpoints == {t1, t2, t3, t4, t5, t6, t7}


def test_is_equal_no_parent():
    """Test the comparison 'equal_at' in the case where one timeline is not active and the other has no parent in the same interval
        We are testing this scenario:

    Time  --------t1-------------------t2----------------------------------t3>

    MO (active)   |---------------------|
    MO (parent)   |---------------------|

    SD (active)   |---------------------------------------------------------->
    SD (parent)   |---------------------|

    "Assert"      |--------equal--------|-------- not equal------------------>
    intervals
    """
    # Arrange
    tz = ZoneInfo("Europe/Copenhagen")

    t1 = datetime(1990, 1, 1, tzinfo=tz)
    t2 = datetime(1999, 1, 1, tzinfo=tz)
    t3 = datetime(9999, 1, 1, tzinfo=tz)
    parent = uuid4()
    ou_timeline = UnitTimeline(
        active=Timeline[Active](intervals=(Active(start=t1, end=t3, value=True),)),
        parent=Timeline[UnitParent](
            intervals=(UnitParent(start=t1, end=t2, value=parent),)
        ),
        name=Timeline[UnitName](intervals=(UnitName(start=t1, end=t3, value="name1"),)),
        unit_id=Timeline[UnitId](intervals=(UnitId(start=t1, end=t3, value="id1"),)),
        unit_level=Timeline[UnitLevel](
            intervals=(UnitLevel(start=t1, end=t3, value="level1"),)
        ),
    )
    ou_timeline_2 = UnitTimeline(
        active=Timeline[Active](intervals=(Active(start=t1, end=t2, value=True),)),
        parent=Timeline[UnitParent](
            intervals=(UnitParent(start=t1, end=t2, value=parent),)
        ),
        name=Timeline[UnitName](intervals=(UnitName(start=t1, end=t2, value="name1"),)),
        unit_id=Timeline[UnitId](intervals=(UnitId(start=t1, end=t2, value="id1"),)),
        unit_level=Timeline[UnitLevel](
            intervals=(UnitLevel(start=t1, end=t2, value="level1"),)
        ),
    )
    # Act/Assert
    assert ou_timeline.equal_at(t1, ou_timeline_2)
    assert ou_timeline.equal_at(t2 - timedelta(days=1), ou_timeline_2)
    assert not ou_timeline.equal_at(t2, ou_timeline_2)
    assert not ou_timeline.equal_at(t3 - timedelta(days=1), ou_timeline_2)
    # There are no values in either timeline at t3
    assert ou_timeline.equal_at(t3, ou_timeline_2)
