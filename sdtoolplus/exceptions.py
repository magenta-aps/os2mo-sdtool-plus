# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from fastapi import HTTPException
from starlette.status import HTTP_404_NOT_FOUND
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY


class NoValueError(Exception):
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


class EngagementSyncTemporarilyDisabled(Exception):
    """
    Only raised when RECALC_MO_UNIT_WHEN_SD_EMPLOYMENT_MOVED is set to False
    (see comment about this setting in config.py)
    """

    pass


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
