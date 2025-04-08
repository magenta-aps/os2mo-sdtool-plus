# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime
from uuid import UUID
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from httpx import AsyncClient
from more_itertools import one
from respx import MockRouter

from sdtoolplus.autogenerated_graphql_client import ClassFilter
from sdtoolplus.autogenerated_graphql_client import EmployeeCreateInput
from sdtoolplus.autogenerated_graphql_client import EngagementCreateInput
from sdtoolplus.autogenerated_graphql_client import LeaveCreateInput
from sdtoolplus.autogenerated_graphql_client import LeaveFilter
from sdtoolplus.autogenerated_graphql_client import RAValidityInput
from sdtoolplus.autogenerated_graphql_client import TestingCreateOrgUnitOrgUnitCreate
from sdtoolplus.depends import GraphQLClient
from sdtoolplus.mo.timeline import _mo_end_to_timeline_end
from sdtoolplus.mo.timeline import get_engagement_types
from sdtoolplus.models import EngType


@pytest.mark.integration_test
async def test_leave_timeline(
    test_client: AsyncClient,
    graphql_client: GraphQLClient,
    base_tree_builder: TestingCreateOrgUnitOrgUnitCreate,
    job_function_1234: UUID,
    respx_mock: MockRouter,
):
    """
    We are testing this scenario:

    Time  --------t1--------t2---------t3-------------t5-----t6--------------------->

    MO (leave)                         |--------leave--------|
    SD (status)   |----3----|-------------1-----------|--4---|-----------1-----------

    "Assert"      |----1----|                         |--2---|
    intervals

    In SD: status 1 is working (with pay), status 3 and 4 is leave
    """
    # Arrange
    tz = ZoneInfo("Europe/Copenhagen")

    t1 = datetime(2001, 1, 1, tzinfo=tz)
    t2 = datetime(2002, 1, 1, tzinfo=tz)
    t3 = datetime(2003, 1, 1, tzinfo=tz)
    t5 = datetime(2005, 1, 1, tzinfo=tz)
    t6 = datetime(2006, 1, 1, tzinfo=tz)

    # Units
    dep1_uuid = UUID("10000000-0000-0000-0000-000000000000")

    # Engagement types
    eng_types = await get_engagement_types(graphql_client)

    # Leave type
    r_leave_type = await graphql_client.get_class(ClassFilter(user_keys=["Orlov"]))
    leave_type = one(r_leave_type.objects).uuid

    # Create person
    person_uuid = uuid4()
    cpr = "0101011234"
    emp_id = "12345"
    user_key = f"II-{emp_id}"

    await graphql_client.create_person(
        EmployeeCreateInput(
            uuid=person_uuid,
            cpr_number=cpr,
            given_name="Chuck",
            surname="Norris",
        )
    )

    # Create engagement (arrange intervals 1-5)
    eng_uuid = (
        await graphql_client.create_engagement(
            EngagementCreateInput(
                user_key=user_key,
                validity=RAValidityInput(from_=t1, to=None),
                extension_1="name1",
                extension_2="dep1",
                person=person_uuid,
                org_unit=dep1_uuid,
                engagement_type=eng_types[EngType.MONTHLY_FULL_TIME],
                job_function=job_function_1234,
            )
        )
    ).uuid

    leave_uuid = (
        await graphql_client.create_leave(
            LeaveCreateInput(
                user_key=user_key,
                person=person_uuid,
                engagement=eng_uuid,
                leave_type=leave_type,
                validity=RAValidityInput(from_=t3, to=t6),
            )
        )
    ).uuid

    print("LEAVE UUID", leave_uuid)

    # await asyncio.sleep(300)

    sd_resp = f"""<?xml version="1.0" encoding="UTF-8"?>
        <GetEmploymentChanged20111201 creationDateTime="2025-03-10T13:50:06">
          <RequestStructure>
            <InstitutionIdentifier>II</InstitutionIdentifier>
            <PersonCivilRegistrationIdentifier>0101011234</PersonCivilRegistrationIdentifier>
            <ActivationDate>2001-01-01</ActivationDate>
            <DeactivationDate>2006-12-31</DeactivationDate>
            <DepartmentIndicator>true</DepartmentIndicator>
            <EmploymentStatusIndicator>true</EmploymentStatusIndicator>
            <ProfessionIndicator>true</ProfessionIndicator>
            <SalaryAgreementIndicator>false</SalaryAgreementIndicator>
            <SalaryCodeGroupIndicator>false</SalaryCodeGroupIndicator>
            <WorkingTimeIndicator>false</WorkingTimeIndicator>
            <UUIDIndicator>true</UUIDIndicator>
          </RequestStructure>
          <Person>
            <PersonCivilRegistrationIdentifier>0101011234</PersonCivilRegistrationIdentifier>
            <Employment>
              <EmploymentIdentifier>{emp_id}</EmploymentIdentifier>
              <EmploymentDate>2001-01-01</EmploymentDate>
              <AnniversaryDate>2001-01-01</AnniversaryDate>
              <EmploymentDepartment>
                <ActivationDate>2001-01-01</ActivationDate>
                <DeactivationDate>9999-12-31</DeactivationDate>
                <DepartmentIdentifier>dep1</DepartmentIdentifier>
                <DepartmentUUIDIdentifier>{str(dep1_uuid)}</DepartmentUUIDIdentifier>
              </EmploymentDepartment>
              <Profession>
                <ActivationDate>2001-01-01</ActivationDate>
                <DeactivationDate>9999-12-31</DeactivationDate>
                <JobPositionIdentifier>1234</JobPositionIdentifier>
                <EmploymentName>name1</EmploymentName>
                <AppointmentCode>0</AppointmentCode>
              </Profession>
              <EmploymentStatus>
                <ActivationDate>2001-01-01</ActivationDate>
                <DeactivationDate>2001-12-31</DeactivationDate>
                <EmploymentStatusCode>3</EmploymentStatusCode>
              </EmploymentStatus>
              <EmploymentStatus>
                <ActivationDate>2002-01-01</ActivationDate>
                <DeactivationDate>2004-12-31</DeactivationDate>
                <EmploymentStatusCode>1</EmploymentStatusCode>
              </EmploymentStatus>
              <EmploymentStatus>
                <ActivationDate>2005-01-01</ActivationDate>
                <DeactivationDate>2005-12-31</DeactivationDate>
                <EmploymentStatusCode>4</EmploymentStatusCode>
              </EmploymentStatus>
              <EmploymentStatus>
                <ActivationDate>2006-01-01</ActivationDate>
                <DeactivationDate>9999-12-31</DeactivationDate>
                <EmploymentStatusCode>1</EmploymentStatusCode>
              </EmploymentStatus>
              <WorkingTime>
                <ActivationDate>2001-01-01</ActivationDate>
                <DeactivationDate>9999-12-31</DeactivationDate>
                <OccupationRate>1.0000</OccupationRate>
                <SalaryRate>1.0000</SalaryRate>
                <SalariedIndicator>true</SalariedIndicator>
                <FullTimeIndicator>false</FullTimeIndicator>
              </WorkingTime>
            </Employment>
          </Person>
        </GetEmploymentChanged20111201>
    """

    respx_mock.get(
        "https://service.sd.dk/sdws/GetEmploymentChanged20111201?InstitutionIdentifier=II&PersonCivilRegistrationIdentifier=0101011234&EmploymentIdentifier=12345&ActivationDate=01.01.1&DeactivationDate=31.12.9999&DepartmentIndicator=True&EmploymentStatusIndicator=True&ProfessionIndicator=True&SalaryAgreementIndicator=False&SalaryCodeGroupIndicator=False&WorkingTimeIndicator=True&UUIDIndicator=True"
    ).respond(
        content_type="text/xml;charset=UTF-8",
        content=sd_resp,
    )

    # Act
    r = await test_client.post(
        "/timeline/sync/engagement",
        json={
            "institution_identifier": "II",
            "cpr": cpr,
            "employment_identifier": emp_id,
            "org_unit_uuid": str(uuid4()),
            "start": "2001-01-01",
            "end": "9999-12-31",
        },
    )

    # Assert
    assert r.status_code == 200

    updated_leave = await graphql_client.get_leave(
        LeaveFilter(uuids=[leave_uuid], from_date=None, to_date=None)
    )
    validities = one(updated_leave.objects).validities

    interval_1 = validities[0]
    assert interval_1.validity.from_ == t1
    assert _mo_end_to_timeline_end(interval_1.validity.to) == t2
    assert interval_1.user_key == user_key
    assert one(interval_1.person).uuid == person_uuid
    assert interval_1.leave_type.uuid == leave_type

    interval_2 = validities[1]
    assert interval_2.validity.from_ == t5
    assert _mo_end_to_timeline_end(interval_2.validity.to) == t6
    assert interval_2.user_key == user_key
    assert one(interval_2.person).uuid == person_uuid
    assert interval_2.leave_type.uuid == leave_type

    assert len(validities) == 2
