# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from fastapi import HTTPException
from starlette.status import HTTP_404_NOT_FOUND
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR


class NoValueError(Exception):
    pass


class ClassNotFoundError(HTTPException):
    pass


class MoreThanOneClassError(HTTPException):
    pass


class EngagementNotFoundError(HTTPException):
    pass


class MoreThanOneEngagementError(HTTPException):
    pass


class EngagementNotActiveError(HTTPException):
    pass


class PersonNotFoundError(HTTPException):
    pass


class MoreThanOnePersonError(HTTPException):
    pass


class DepartmentTimelineNotFound(HTTPException):
    pass


class EngagementSyncTemporarilyDisabled(HTTPException):
    """
    Only raised when RECALC_MO_UNIT_WHEN_SD_EMPLOYMENT_MOVED is set to False
    (see comment about this setting in config.py)
    """

    pass


class OrgUnitNotFoundError(HTTPException):
    pass


class MoreThanOneOrgUnitError(HTTPException):
    pass


class MoreThanOnePNumberError(HTTPException):
    pass


class MoreThanOnePostalAddressError(HTTPException):
    pass


class MoreThanOneLeaveError(HTTPException):
    pass


class_not_found_error = ClassNotFoundError(
    status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Class not found in MO!"
)

more_than_one_class_error = MoreThanOneClassError(
    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
    detail="More than one class found in MO!",
)

engagement_not_found_error = EngagementNotFoundError(
    status_code=HTTP_404_NOT_FOUND,
    detail="Engagement not found for the provided person and user key (EmploymentIdentifier)",
)

more_than_one_engagement_error = MoreThanOneEngagementError(
    status_code=HTTP_422_UNPROCESSABLE_ENTITY,
    detail="More than one engagement found for the provided person and user key (EmploymentIdentifier)",
)

engagement_not_active_error = EngagementNotActiveError(
    status_code=HTTP_422_UNPROCESSABLE_ENTITY,
    detail="The engagement is not active in the entire move interval",
)

person_not_found_error = PersonNotFoundError(
    status_code=HTTP_404_NOT_FOUND, detail="Could not find person in MO"
)

more_than_one_person_error = MoreThanOneEngagementError(
    status_code=HTTP_422_UNPROCESSABLE_ENTITY,
    detail="More than one person found in MO",
)

department_timeline_not_found = DepartmentTimelineNotFound(
    status_code=HTTP_422_UNPROCESSABLE_ENTITY,
    detail="Empty department timeline for employment found in SD",
)

engagement_sync_temporarily_disabled = EngagementSyncTemporarilyDisabled(
    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
    detail="Engagement sync temporarily disabled!",
)

org_unit_not_found_error = OrgUnitNotFoundError(
    status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Org unit not found in MO!"
)

more_than_one_org_unit_error = MoreThanOneOrgUnitError(
    status_code=HTTP_422_UNPROCESSABLE_ENTITY,
    detail="More than one org unit found in MO!",
)

more_than_one_pnumber_error = MoreThanOnePNumberError(
    status_code=HTTP_422_UNPROCESSABLE_ENTITY,
    detail="More than one P-number found for unit in MO!",
)

more_than_one_postal_address_error = MoreThanOnePostalAddressError(
    status_code=HTTP_422_UNPROCESSABLE_ENTITY,
    detail="More than one postal address found in MO!",
)

more_than_one_leave_error = MoreThanOneLeaveError(
    status_code=HTTP_422_UNPROCESSABLE_ENTITY, detail="More than one leave found in MO"
)
