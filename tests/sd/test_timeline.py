# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import date
from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

from more_itertools import one
from pydantic import parse_obj_as
from sdclient.responses import DepartmentParentHistoryObj
from sdclient.responses import GetDepartmentResponse

from sdtoolplus.models import POSITIVE_INFINITY
from sdtoolplus.mo_org_unit_importer import OrgUnitUUID
from sdtoolplus.models import Active
from sdtoolplus.models import Timeline
from sdtoolplus.models import UnitId
from sdtoolplus.models import UnitLevel
from sdtoolplus.models import UnitName
from sdtoolplus.models import UnitParent
from sdtoolplus.sd.timeline import get_department_timeline
from sdtoolplus.sd.tree import ASSUMED_SD_TIMEZONE


def test_get_department_timeline():
    # Arrange
    dep_uuid = uuid4()

    sd_dep_resp_dict = {
        "RegionIdentifier": "RI",
        "RegionUUIDIdentifier": uuid4(),
        "InstitutionIdentifier": "II",
        "InstitutionUUIDIdentifier": uuid4(),
        "Department": [
            {
                "ActivationDate": "2001-01-01",
                "DeactivationDate": "2001-12-31",
                "DepartmentIdentifier": "DEP1",
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentName": "name1",
                "DepartmentUUIDIdentifier": dep_uuid,
            },
            {
                "ActivationDate": "2002-01-01",
                "DeactivationDate": "2002-12-31",
                "DepartmentIdentifier": "DEP2",  # Changed
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentName": "name1",  # Not changed
                "DepartmentUUIDIdentifier": dep_uuid,
            },
            # Hole in SD timeline here
            {
                "ActivationDate": "2004-01-01",
                "DeactivationDate": "2004-12-31",
                "DepartmentIdentifier": "DEP1",
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentName": "name3",
                "DepartmentUUIDIdentifier": dep_uuid,
            },
            {
                "ActivationDate": "2005-01-01",
                "DeactivationDate": "9999-12-31",
                "DepartmentIdentifier": "DEP1",
                "DepartmentLevelIdentifier": "NY0-niveau",
                "DepartmentName": "name4",
                "DepartmentUUIDIdentifier": dep_uuid,
            },
        ],
    }

    sd_parent_history_resp = [
        {
            "startDate": "2001-01-01",
            "endDate": "2002-12-31",
            "parentUuid": "8d3018f1-62ef-48cf-8e54-819b4408c23f",
        },
        {
            "startDate": "2004-01-01",
            "endDate": "9999-12-31",
            "parentUuid": "d567f959-ab77-4849-9cd0-c14e9120433c",
        },
    ]

    mock_sd_client = MagicMock()
    mock_sd_client.get_department.return_value = GetDepartmentResponse.parse_obj(
        sd_dep_resp_dict
    )
    mock_sd_client.get_department_parent_history.return_value = parse_obj_as(
        list[DepartmentParentHistoryObj], sd_parent_history_resp
    )

    # Act
    department_timeline = get_department_timeline(
        sd_client=mock_sd_client, inst_id="II", unit_uuid=dep_uuid
    )

    # Assert
    query_params = one(one(mock_sd_client.get_department.call_args_list).args)
    assert query_params.InstitutionIdentifier == "II"
    assert query_params.DepartmentUUIDIdentifier == dep_uuid
    assert query_params.ActivationDate == date.min
    assert query_params.DeactivationDate == date.max
    assert query_params.DepartmentNameIndicator is True
    assert query_params.UUIDIndicator is True

    mock_sd_client.get_department_parent_history.assert_called_once_with(dep_uuid)

    assert department_timeline.active == Timeline[Active](
        intervals=(
            Active(
                start=datetime(2001, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2003, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value=True,
            ),
            Active(
                start=datetime(2004, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=POSITIVE_INFINITY,
                value=True,
            ),
        )
    )

    assert department_timeline.unit_id == Timeline[UnitId](
        intervals=(
            UnitId(
                start=datetime(2001, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2002, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value="DEP1",
            ),
            UnitId(
                start=datetime(2002, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2003, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value="DEP2",
            ),
            UnitId(
                start=datetime(2004, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=POSITIVE_INFINITY,
                value="DEP1",
            ),
        )
    )

    assert department_timeline.unit_level == Timeline[UnitLevel](
        intervals=(
            UnitLevel(
                start=datetime(2001, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2003, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value="NY0-niveau",
            ),
            UnitLevel(
                start=datetime(2004, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=POSITIVE_INFINITY,
                value="NY0-niveau",
            ),
        )
    )

    assert department_timeline.name == Timeline[UnitName](
        intervals=(
            UnitName(
                start=datetime(2001, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2003, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value="name1",
            ),
            UnitName(
                start=datetime(2004, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2005, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value="name3",
            ),
            UnitName(
                start=datetime(2005, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=POSITIVE_INFINITY,
                value="name4",
            ),
        )
    )

    assert department_timeline.parent == Timeline[UnitParent](
        intervals=(
            UnitParent(
                start=datetime(2001, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime(2003, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                value=OrgUnitUUID("8d3018f1-62ef-48cf-8e54-819b4408c23f"),
            ),
            UnitParent(
                start=datetime(2004, 1, 1, tzinfo=ASSUMED_SD_TIMEZONE),
                end=datetime.max.replace(tzinfo=ASSUMED_SD_TIMEZONE),
                value=OrgUnitUUID("d567f959-ab77-4849-9cd0-c14e9120433c"),
            ),
        )
    )


# TODO: test empty case
