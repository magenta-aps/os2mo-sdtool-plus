# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta

import structlog

from sdtoolplus.models import POSITIVE_INFINITY
from sdtoolplus.sd.tree import ASSUMED_SD_TIMEZONE

logger = structlog.stdlib.get_logger()


def sd_start_to_timeline_start(d: date) -> datetime:
    return datetime.combine(d, time.min, ASSUMED_SD_TIMEZONE)


def sd_end_to_timeline_end(d: date) -> datetime:
    if d == date.max:
        return POSITIVE_INFINITY
    # We have to add one day to the SD end date when converting to a timeline end
    # datetime, since we are working with a continuous timeline. E.g. the SD end date
    # 1999-12-31 states that the effective end datetime is 1999-12-31T23:59:59.999999,
    # which (due to the continuous timeline) translates into the end datetime
    # t_end = 2000-01-01T00:00:00.000000 in the half-open interval [t_start, t_end)
    return datetime.combine(d, time.min, ASSUMED_SD_TIMEZONE) + timedelta(days=1)
