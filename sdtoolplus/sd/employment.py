# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from enum import Enum


class EmploymentStatusCode(Enum):
    # See docs at
    # https://www.silkeborgdata.dk/start/support/vejledning/9392-getemployment20111201
    EMPLOYED_NO_PAY = "0"
    EMPLOYED_WITH_PAY = "1"
    LEAVE = "3"
    MIGRATED_OR_DEAD = "7"
    RESIGNED = "8"
    RETIRED = "9"
    DELETED = "S"

    def is_active(self) -> bool:
        return self in (
            EmploymentStatusCode.EMPLOYED_NO_PAY,
            EmploymentStatusCode.EMPLOYED_WITH_PAY,
            EmploymentStatusCode.LEAVE,
        )
