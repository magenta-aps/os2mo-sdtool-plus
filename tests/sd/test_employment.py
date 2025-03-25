# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from sdtoolplus.sd.employment import EmploymentStatusCode


def test_employment_status_code_is_active():
    assert EmploymentStatusCode.EMPLOYED_NO_PAY.is_active()
    assert EmploymentStatusCode.EMPLOYED_WITH_PAY.is_active()
    assert EmploymentStatusCode.LEAVE.is_active()
    assert EmploymentStatusCode.LEAVE_.is_active()
    assert not EmploymentStatusCode.MIGRATED_OR_DEAD.is_active()
    assert not EmploymentStatusCode.RESIGNED.is_active()
    assert not EmploymentStatusCode.RETIRED.is_active()
    assert not EmploymentStatusCode.DELETED.is_active()


def test_employment_status_code_is_leave():
    assert not EmploymentStatusCode.EMPLOYED_NO_PAY.is_leave()
    assert not EmploymentStatusCode.EMPLOYED_WITH_PAY.is_leave()
    assert EmploymentStatusCode.LEAVE.is_leave()
    assert EmploymentStatusCode.LEAVE_.is_leave()
    assert not EmploymentStatusCode.MIGRATED_OR_DEAD.is_leave()
    assert not EmploymentStatusCode.RESIGNED.is_leave()
    assert not EmploymentStatusCode.RETIRED.is_leave()
    assert not EmploymentStatusCode.DELETED.is_leave()
