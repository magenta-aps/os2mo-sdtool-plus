# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import structlog
from more_itertools import only
from sdclient.responses import GetEmploymentChangedResponse
from sdclient.responses import WorkingTime

from sdtoolplus.exceptions import MoreThanOneEngagementError
from sdtoolplus.exceptions import MoreThanOnePersonError
from sdtoolplus.models import Active
from sdtoolplus.models import AssociationTimeline
from sdtoolplus.models import EngagementKey
from sdtoolplus.models import EngagementName
from sdtoolplus.models import EngagementSDUnit
from sdtoolplus.models import EngagementTimeline
from sdtoolplus.models import EngagementType
from sdtoolplus.models import EngagementUnit
from sdtoolplus.models import EngagementUnitId
from sdtoolplus.models import EngType
from sdtoolplus.models import LeaveTimeline
from sdtoolplus.models import Timeline
from sdtoolplus.models import combine_intervals
from sdtoolplus.sd.employment import EmploymentStatusCode
from sdtoolplus.sd.timelines.common import sd_end_to_timeline_end
from sdtoolplus.sd.timelines.common import sd_start_to_timeline_start

logger = structlog.stdlib.get_logger()


def _sd_employment_type(worktime: WorkingTime) -> EngType:
    if not worktime.SalariedIndicator:
        return EngType.HOURLY
    if worktime.FullTimeIndicator:
        return EngType.MONTHLY_FULL_TIME
    return EngType.MONTHLY_PART_TIME


def get_employment_timeline(
    sd_get_employment_changed_resp: GetEmploymentChangedResponse,
) -> EngagementTimeline:
    logger.info("Get SD employment timeline")

    person = only(
        sd_get_employment_changed_resp.Person, too_long=MoreThanOnePersonError
    )
    if not person:
        return EngagementTimeline()
    employment = only(person.Employment, too_long=MoreThanOneEngagementError)
    if not employment:
        return EngagementTimeline()

    active_intervals = (
        tuple(
            Active(
                start=sd_start_to_timeline_start(status.ActivationDate),
                end=sd_end_to_timeline_end(status.DeactivationDate),
                value=True,
            )
            for status in employment.EmploymentStatus
            if EmploymentStatusCode(status.EmploymentStatusCode).is_active()
        )
        if employment.EmploymentStatus
        else tuple()
    )

    eng_key_intervals = (
        tuple(
            EngagementKey(
                start=sd_start_to_timeline_start(prof.ActivationDate),
                end=sd_end_to_timeline_end(prof.DeactivationDate),
                value=prof.JobPositionIdentifier,
            )
            for prof in employment.Profession
        )
        if employment.Profession
        else tuple()
    )

    eng_name_intervals = (
        tuple(
            EngagementName(
                start=sd_start_to_timeline_start(prof.ActivationDate),
                end=sd_end_to_timeline_end(prof.DeactivationDate),
                value=prof.EmploymentName,
            )
            for prof in employment.Profession
        )
        if employment.Profession
        else tuple()
    )

    eng_unit_intervals = (
        tuple(
            EngagementUnit(
                start=sd_start_to_timeline_start(dep.ActivationDate),
                end=sd_end_to_timeline_end(dep.DeactivationDate),
                value=dep.DepartmentUUIDIdentifier,
            )
            for dep in employment.EmploymentDepartment
        )
        if employment.EmploymentDepartment
        else tuple()
    )

    eng_sd_unit_intervals = (
        tuple(
            EngagementSDUnit(
                start=sd_start_to_timeline_start(dep.ActivationDate),
                end=sd_end_to_timeline_end(dep.DeactivationDate),
                value=dep.DepartmentUUIDIdentifier,
            )
            for dep in employment.EmploymentDepartment
        )
        if employment.EmploymentDepartment
        else tuple()
    )

    eng_unit_id_intervals = (
        tuple(
            EngagementUnitId(
                start=sd_start_to_timeline_start(dep.ActivationDate),
                end=sd_end_to_timeline_end(dep.DeactivationDate),
                value=dep.DepartmentIdentifier,
            )
            for dep in employment.EmploymentDepartment
        )
        if employment.EmploymentDepartment
        else tuple()
    )

    eng_type_intervals = (
        tuple(
            EngagementType(
                start=sd_start_to_timeline_start(working_time.ActivationDate),
                end=sd_end_to_timeline_end(working_time.DeactivationDate),
                value=_sd_employment_type(working_time),
            )
            for working_time in employment.WorkingTime
        )
        if employment.WorkingTime
        else tuple()
    )

    timeline = EngagementTimeline(
        eng_active=Timeline[Active](intervals=combine_intervals(active_intervals)),
        eng_key=Timeline[EngagementKey](intervals=combine_intervals(eng_key_intervals)),
        eng_name=Timeline[EngagementName](
            intervals=combine_intervals(eng_name_intervals)
        ),
        eng_unit=Timeline[EngagementUnit](
            intervals=combine_intervals(eng_unit_intervals)
        ),
        eng_sd_unit=Timeline[EngagementSDUnit](
            intervals=combine_intervals(eng_sd_unit_intervals)
        ),
        eng_unit_id=Timeline[EngagementUnitId](
            intervals=combine_intervals(eng_unit_id_intervals)
        ),
        eng_type=Timeline[EngagementType](
            intervals=combine_intervals(eng_type_intervals)
        ),
    )
    logger.info("SD engagement timeline", timeline=timeline.dict())

    return timeline


def get_leave_timeline(
    sd_get_employment_changed_resp: GetEmploymentChangedResponse,
) -> LeaveTimeline:
    logger.info("Get SD leave timeline")

    person = only(
        sd_get_employment_changed_resp.Person, too_long=MoreThanOnePersonError
    )
    if not person:
        return LeaveTimeline()
    employment = only(person.Employment, too_long=MoreThanOneEngagementError)
    if not employment:
        return LeaveTimeline()

    active_intervals = (
        tuple(
            Active(
                start=sd_start_to_timeline_start(status.ActivationDate),
                end=sd_end_to_timeline_end(status.DeactivationDate),
                value=True,
            )
            for status in employment.EmploymentStatus
            if EmploymentStatusCode(status.EmploymentStatusCode).is_leave()
        )
        if employment.EmploymentStatus
        else tuple()
    )

    timeline = LeaveTimeline(
        leave_active=Timeline[Active](intervals=combine_intervals(active_intervals)),
    )
    logger.info("SD leave timeline", timeline=timeline.dict())

    return timeline


def get_association_timeline(
    desired_eng_timeline: EngagementTimeline,
) -> AssociationTimeline:
    timeline = AssociationTimeline(
        association_active=desired_eng_timeline.eng_active,
        association_unit=desired_eng_timeline.eng_sd_unit,
    )
    logger.info("SD association timeline", timeline=timeline.dict())

    return timeline
