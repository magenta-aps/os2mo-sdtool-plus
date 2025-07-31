# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.models import Active
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitParent
from sdtoolplus.models import UnitTimeline
from sdtoolplus.timeline import patch_missing_parents
from tests.integration.conftest import UNKNOWN_UNIT

SOME_UNIT_UUID = uuid4()


@pytest.fixture()
def settings(sdtoolplus_settings: SDToolPlusSettings) -> SDToolPlusSettings:
    settings = sdtoolplus_settings.dict()
    settings.update(
        {
            "mode": "region",
            "unknown_unit": str(UNKNOWN_UNIT),
            "apply_ny_logic": False,
            "mo_subtree_paths_for_root": {
                "II": [SOME_UNIT_UUID],
            },
        }
    )
    return SDToolPlusSettings.parse_obj(settings)


def test_patch_missing_parents_does_nothing_when_all_parents_exist(
    settings: SDToolPlusSettings,
):
    # Arrange
    tz = ZoneInfo("Europe/Copenhagen")

    t1 = datetime(2001, 1, 1, tzinfo=tz)
    t2 = datetime(2002, 1, 1, tzinfo=tz)
    t3 = datetime(2003, 1, 1, tzinfo=tz)
    t4 = datetime(2004, 1, 1, tzinfo=tz)

    parent_uuid1 = uuid4()
    parent_uuid2 = uuid4()
    parent_uuid3 = uuid4()

    desired_unit_timeline = UnitTimeline(
        active=Timeline[Active](intervals=(Active(start=t1, end=t4, value=True),)),
        parent=Timeline[UnitParent](
            intervals=(
                UnitParent(start=t1, end=t2, value=parent_uuid1),
                UnitParent(start=t2, end=t3, value=parent_uuid2),
                UnitParent(start=t3, end=t4, value=parent_uuid3),
            )
        ),
    )

    # Act
    patched_timeline = patch_missing_parents(
        settings=SDToolPlusSettings.parse_obj(settings),
        desired_unit_timeline=desired_unit_timeline,
    )

    # Assert
    assert patched_timeline == desired_unit_timeline


def test_patch_missing_parents_handles_missing_parent(
    settings: SDToolPlusSettings,
):
    # Arrange
    tz = ZoneInfo("Europe/Copenhagen")

    t1 = datetime(2001, 1, 1, tzinfo=tz)
    t2 = datetime(2002, 1, 1, tzinfo=tz)
    t3 = datetime(2003, 1, 1, tzinfo=tz)
    t4 = datetime(2004, 1, 1, tzinfo=tz)

    parent_uuid1 = uuid4()
    parent_uuid2 = uuid4()

    desired_unit_timeline = UnitTimeline(
        active=Timeline[Active](intervals=(Active(start=t1, end=t4, value=True),)),
        parent=Timeline[UnitParent](
            intervals=(
                UnitParent(start=t1, end=t2, value=parent_uuid1),
                # PARENT MISSING BETWEEN t2 and t3
                UnitParent(start=t3, end=t4, value=parent_uuid2),
            )
        ),
    )

    # Act
    patched_timeline = patch_missing_parents(
        settings=SDToolPlusSettings.parse_obj(settings),
        desired_unit_timeline=desired_unit_timeline,
    )

    # Assert
    assert patched_timeline.parent == Timeline[UnitParent](
        intervals=(
            UnitParent(start=t1, end=t2, value=parent_uuid1),
            UnitParent(start=t2, end=t3, value=UNKNOWN_UNIT),
            UnitParent(start=t3, end=t4, value=parent_uuid2),
        )
    )


def test_patch_missing_parents_handles_holes_in_timeline(
    settings: SDToolPlusSettings,
):
    """
    We test this scenario:

    Time          ----t1-------t2-------t3----------t4-----------t5----->

    SD (active)       |--------|        |------------------------|
    SD (parent)       |---p1---|                    |-----p2-----|

    Desired (active)  |--------|        |------------------------|
    Desired (parent)  |---p1---|        |--unknown--|-----p2-----|
    """

    # Arrange
    tz = ZoneInfo("Europe/Copenhagen")

    t1 = datetime(2001, 1, 1, tzinfo=tz)
    t2 = datetime(2002, 1, 1, tzinfo=tz)
    t3 = datetime(2003, 1, 1, tzinfo=tz)
    t4 = datetime(2004, 1, 1, tzinfo=tz)
    t5 = datetime(2005, 1, 1, tzinfo=tz)

    parent_uuid1 = uuid4()
    parent_uuid2 = uuid4()

    desired_unit_timeline = UnitTimeline(
        active=Timeline[Active](
            intervals=(
                Active(start=t1, end=t2, value=True),
                Active(start=t3, end=t5, value=True),
            )
        ),
        parent=Timeline[UnitParent](
            intervals=(
                UnitParent(start=t1, end=t2, value=parent_uuid1),
                # HOLE BETWEEN t2 AND t3
                # PARENT MISSING BETWEEN t3 AND t4
                UnitParent(start=t4, end=t5, value=parent_uuid2),
            )
        ),
    )

    # Act
    patched_timeline = patch_missing_parents(
        settings=SDToolPlusSettings.parse_obj(settings),
        desired_unit_timeline=desired_unit_timeline,
    )

    # Assert
    assert patched_timeline.parent == Timeline[UnitParent](
        intervals=(
            UnitParent(start=t1, end=t2, value=parent_uuid1),
            UnitParent(start=t3, end=t4, value=UNKNOWN_UNIT),
            UnitParent(start=t4, end=t5, value=parent_uuid2),
        )
    )
