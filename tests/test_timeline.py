# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitParent
from sdtoolplus.models import UnitTimeline
from sdtoolplus.timeline import patch_missing_parents


def test_patch_missing_parents_does_nothing_when_all_parents_exist(
    sdtoolplus_settings: SDToolPlusSettings,
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

    settings = sdtoolplus_settings.dict()
    settings.update(
        {
            "mode": "region",
            "unknown_unit": str(uuid4()),
            "apply_ny_logic": False,
            "mo_subtree_paths_for_root": {
                "II": [str(uuid4()), str(uuid4())],
            },
        }
    )

    desired_unit_timeline = UnitTimeline(
        parent=Timeline[UnitParent](
            intervals=(
                UnitParent(start=t1, end=t2, value=parent_uuid1),
                UnitParent(start=t2, end=t3, value=parent_uuid2),
                UnitParent(start=t3, end=t4, value=parent_uuid3),
            )
        )
    )

    # Act
    patched_timeline = patch_missing_parents(
        settings=SDToolPlusSettings.parse_obj(settings),
        desired_unit_timeline=desired_unit_timeline,
    )

    # Assert
    assert patched_timeline == desired_unit_timeline


def test_patch_missing_parents_handles_missing_parent(
    sdtoolplus_settings: SDToolPlusSettings,
):
    # Arrange
    tz = ZoneInfo("Europe/Copenhagen")

    t1 = datetime(2001, 1, 1, tzinfo=tz)
    t2 = datetime(2002, 1, 1, tzinfo=tz)
    t3 = datetime(2003, 1, 1, tzinfo=tz)
    t4 = datetime(2004, 1, 1, tzinfo=tz)

    parent_uuid1 = uuid4()
    parent_uuid2 = uuid4()
    unknown_unit = uuid4()

    settings = sdtoolplus_settings.dict()
    settings.update(
        {
            "mode": "region",
            "unknown_unit": str(unknown_unit),
            "apply_ny_logic": False,
            "mo_subtree_paths_for_root": {
                "II": [str(uuid4()), str(uuid4())],
            },
        }
    )

    desired_unit_timeline = UnitTimeline(
        parent=Timeline[UnitParent](
            intervals=(
                UnitParent(start=t1, end=t2, value=parent_uuid1),
                # PARENT MISSING BETWEEN t2 and t3
                UnitParent(start=t3, end=t4, value=parent_uuid2),
            )
        )
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
            UnitParent(start=t2, end=t3, value=unknown_unit),
            UnitParent(start=t3, end=t4, value=parent_uuid2),
        )
    )
