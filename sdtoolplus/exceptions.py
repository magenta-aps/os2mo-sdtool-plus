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
