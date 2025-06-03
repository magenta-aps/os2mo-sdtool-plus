# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0


class NoValueError(Exception):
    pass


class EngagementNotFoundError(Exception):
    pass


class EngagementNotActiveError(Exception):
    pass


class PersonNotFoundError(Exception):
    pass


class DepartmentTimelineNotFound(Exception):
    pass


class EngagementSyncTemporarilyDisabled(Exception):
    """
    Only raised when RECALC_MO_UNIT_WHEN_SD_EMPLOYMENT_MOVED is set to False
    (see comment about this setting in config.py)
    """

    pass
