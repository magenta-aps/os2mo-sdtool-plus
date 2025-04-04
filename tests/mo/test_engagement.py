# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime

import pytest

from sdtoolplus.mo.engagement import _is_active_in_entire_interval
from sdtoolplus.models import POSITIVE_INFINITY
from sdtoolplus.models import Active
from sdtoolplus.models import Timeline
from tests.test_models import DAY_AFTER_TOMORROW_START
from tests.test_models import MINUS_INFINITY
from tests.test_models import TODAY_START
from tests.test_models import TOMORROW_START
from tests.test_models import YESTERDAY_START


def test__is_active_in_entire_interval_returns_false_for_empty_timeline():
    assert not _is_active_in_entire_interval(
        Timeline[Active](), TODAY_START, TOMORROW_START
    )


@pytest.mark.parametrize(
    "start, end, expected",
    [
        (MINUS_INFINITY, TOMORROW_START, False),
        (TODAY_START, POSITIVE_INFINITY, False),
        (TODAY_START, TOMORROW_START, True),
    ],
)
def test__is_active_in_entire_interval_returns_false_when_intervals_too_long(
    start: datetime, end: datetime, expected: bool
):
    # Arrange
    timeline = Timeline[Active](
        intervals=(
            Active(start=YESTERDAY_START, end=DAY_AFTER_TOMORROW_START, value=True),
        )
    )

    # Act + Assert
    assert _is_active_in_entire_interval(timeline, start, end) == expected


def test__is_active_in_entire_interval_returns_false_for_multiple_active_intervals():
    # Arrange
    timeline = Timeline[Active](
        intervals=(
            Active(start=YESTERDAY_START, end=TODAY_START, value=True),
            Active(start=TOMORROW_START, end=POSITIVE_INFINITY, value=True),
        )
    )

    # Act + Assert
    assert (
        _is_active_in_entire_interval(
            timeline, TOMORROW_START, DAY_AFTER_TOMORROW_START
        )
        is False
    )
