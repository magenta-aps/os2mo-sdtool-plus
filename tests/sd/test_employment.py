# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from sdtoolplus.sd.employment import EmploymentStatusCode


def test_employment_status_code():
    assert EmploymentStatusCode.EMPLOYED_NO_PAY.is_active()
    assert EmploymentStatusCode.EMPLOYED_WITH_PAY.is_active()
    assert EmploymentStatusCode.LEAVE.is_active()
    assert not EmploymentStatusCode.MIGRATED_OR_DEAD.is_active()
    assert not EmploymentStatusCode.RESIGNED.is_active()
    assert not EmploymentStatusCode.RETIRED.is_active()
    assert not EmploymentStatusCode.DELETED.is_active()
