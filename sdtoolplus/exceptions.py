# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from fastapi import HTTPException
from starlette.status import HTTP_404_NOT_FOUND
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from sdtoolplus.mo_org_unit_importer import OrgUnitUUID


class NoValueError(Exception):
    pass


class UnknownNYLevel(Exception):
    pass


class CannotProcessOrgUnitError(Exception):
    pass


class ClassNotFoundError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Class not found in MO!"
        )


class MoreThanOneClassError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="More than one class found in MO!",
        )


class EngagementNotFoundError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            detail="Engagement not found for the provided person and user key (EmploymentIdentifier)",
        )


class MoreThanOneEngagementError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="More than one engagement found for the provided person and user key (EmploymentIdentifier)",
        )


class EngagementNotActiveError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The engagement is not active in the entire move interval",
        )


class PersonNotFoundError(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=HTTP_404_NOT_FOUND, detail="Could not find person")


class MoreThanOnePersonError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="More than one person found in MO",
        )


class DepartmentTimelineNotFoundError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Empty department timeline for employment found in SD",
        )


class EngagementSyncTemporarilyDisabled(HTTPException):
    """
    Only raised when RECALC_MO_UNIT_WHEN_SD_EMPLOYMENT_MOVED is set to False
    (see comment about this setting in config.py)
    """

    def __init__(self) -> None:
        super().__init__(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Engagement sync temporarily disabled!",
        )


class OrgUnitNotFoundError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=HTTP_404_NOT_FOUND, detail="Org unit not found in MO!"
        )


class MoreThanOneOrgUnitError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="More than one org unit found in MO!",
        )


class MoreThanOnePNumberError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="More than one P-number found for unit in MO!",
        )


class MoreThanOnePostalAddressError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="More than one postal address found in MO!",
        )


class MoreThanOnePhoneNumberError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="More than one phone number found in MO!",
        )


class MoreThanOneLeaveError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="More than one leave found in MO",
        )


class MoreThanOneAssociationError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="More than one association found in MO",
        )


class DepartmentParentsNotFoundError(HTTPException):
    def __init__(self, org_unit: OrgUnitUUID) -> None:
        super().__init__(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Department parent(s) not found in SD for unit {str(org_unit)}",
        )


class HolesInDepartmentParentsTimelineError(HTTPException):
    def __init__(self, org_unit: OrgUnitUUID) -> None:
        super().__init__(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"There are holes in the department parent history timeline for the SD unit {str(org_unit)}",
        )


class DepartmentValidityExceedsParentsValiditiesError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
            detail="SD department validity exceeds parents validities",
        )
