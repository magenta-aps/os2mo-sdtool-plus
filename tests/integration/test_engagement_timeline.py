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

from sdtoolplus.autogenerated_graphql_client import EmployeeCreateInput
from sdtoolplus.autogenerated_graphql_client import EngagementCreateInput
from sdtoolplus.autogenerated_graphql_client import EngagementUpdateInput
from sdtoolplus.autogenerated_graphql_client import RAValidityInput
from sdtoolplus.autogenerated_graphql_client import TestingCreateOrgUnitOrgUnitCreate
from sdtoolplus.depends import GraphQLClient
from sdtoolplus.mo.timeline import _mo_end_to_timeline_end
from sdtoolplus.mo.timeline import get_engagement_types
from sdtoolplus.models import POSITIVE_INFINITY
from sdtoolplus.models import EngType


@pytest.mark.integration_test
@pytest.mark.envvar({"MUNICIPALITY_MODE": "false"})
async def test_eng_timeline_http_triggered_sync(
    test_client: AsyncClient,
    graphql_client: GraphQLClient,
    base_tree_builder: TestingCreateOrgUnitOrgUnitCreate,
    job_function_1234: UUID,
    job_function_5678: UUID,
    job_function_9000: UUID,
    respx_mock: MockRouter,
):
    """
    We are testing this scenario:

    Time  --------t1--------t2---------t3------t4-----t5-----t6------------t7------->

    MO (name)               |------name4-------|---------------name5-----------------
    MO (key)                |------------- 1234 -------------|-------- 5678 ---------
    MO (unit)               |---dep3---|-------------------dep4----------------------
    MO (unit ID)            |---dep3---|-------------------dep4----------------------
    MO (ext_7)              |----v1----|--v2---|--v3--|--v4--|--------v5-------------
    MO (active)             |--------------------------------------------------------
    MO (eng_type)           |---full---|-----------------part------------------------

    "Arrange" intervals     |-----1----|---2---|---3--|---4--|---------5-------------

    SD (name)     |-------name1--------|----name2-----|-------name3------------------
    SD (key)      |------------------------ 9000 ------------------------------------
    SD (unit)     |---dep1--|-------------------dep2---------------------------------
    SD (unit ID)  |---dep1--|-------------------dep2---------------------------------
    SD (active)   |---------1----------|-------3------|---8--|-------1-----|----8----
    SD (eng_type) |--------part--------|-------------------full----------------------

    "Assert"      |----1----|-----2----|---3---|--4---|      |-----5-------|
    intervals

    In SD: name = EmploymentName, key = JobPositionIdentifier
           active = EmploymentStatusCode
    In MO: name = extension_1, key = user_key
    """
    # Arrange
    tz = ZoneInfo("Europe/Copenhagen")

    t1 = datetime(2001, 1, 1, tzinfo=tz)
    t2 = datetime(2002, 1, 1, tzinfo=tz)
    t3 = datetime(2003, 1, 1, tzinfo=tz)
    t4 = datetime(2004, 1, 1, tzinfo=tz)
    t5 = datetime(2005, 1, 1, tzinfo=tz)
    t6 = datetime(2006, 1, 1, tzinfo=tz)
    t7 = datetime(2007, 1, 1, tzinfo=tz)

    # Units
    dep1_uuid = UUID("10000000-0000-0000-0000-000000000000")
    dep2_uuid = UUID("20000000-0000-0000-0000-000000000000")
    dep3_uuid = UUID("30000000-0000-0000-0000-000000000000")
    dep4_uuid = UUID("40000000-0000-0000-0000-000000000000")

    eng_types = await get_engagement_types(graphql_client)

    # Create person
    person_uuid = uuid4()
    cpr = "0101011234"
    emp_id = "12345"

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
                user_key=f"II-{emp_id}",
                validity=RAValidityInput(from_=t2, to=None),
                extension_1="name4",
                extension_2="dep3",
                extension_7="v1",
                person=person_uuid,
                org_unit=dep3_uuid,
                engagement_type=eng_types[EngType.MONTHLY_FULL_TIME],
                job_function=job_function_1234,
            )
        )
    ).uuid

    # Update engagement (arrange interval 2)
    await graphql_client.update_engagement(
        EngagementUpdateInput(
            uuid=eng_uuid,
            user_key=f"II-{emp_id}",
            validity=RAValidityInput(from_=t3, to=t4),
            extension_1="name4",
            extension_2="dep4",
            extension_7="v2",
            person=person_uuid,
            org_unit=dep4_uuid,
            engagement_type=eng_types[EngType.MONTHLY_PART_TIME],
            job_function=job_function_1234,
        )
    )

    # Update engagement (arrange interval 3)
    await graphql_client.update_engagement(
        EngagementUpdateInput(
            uuid=eng_uuid,
            user_key=f"II-{emp_id}",
            validity=RAValidityInput(from_=t4, to=t5),
            extension_1="name5",
            extension_2="dep4",
            extension_7="v3",
            person=person_uuid,
            org_unit=dep4_uuid,
            engagement_type=eng_types[EngType.MONTHLY_PART_TIME],
            job_function=job_function_1234,
        )
    )

    # Update engagement (arrange interval 4)
    await graphql_client.update_engagement(
        EngagementUpdateInput(
            uuid=eng_uuid,
            user_key=f"II-{emp_id}",
            validity=RAValidityInput(from_=t5, to=t6),
            extension_1="name5",
            extension_2="dep4",
            extension_7="v4",
            person=person_uuid,
            org_unit=dep4_uuid,
            engagement_type=eng_types[EngType.MONTHLY_PART_TIME],
            job_function=job_function_1234,
        )
    )

    # Update engagement (arrange interval 5)
    await graphql_client.update_engagement(
        EngagementUpdateInput(
            uuid=eng_uuid,
            user_key=f"II-{emp_id}",
            validity=RAValidityInput(from_=t6, to=None),
            extension_1="name5",
            extension_2="dep4",
            extension_7="v5",
            person=person_uuid,
            org_unit=dep4_uuid,
            engagement_type=eng_types[EngType.MONTHLY_PART_TIME],
            job_function=job_function_5678,
        )
    )

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
                <DeactivationDate>2001-12-31</DeactivationDate>
                <DepartmentIdentifier>dep1</DepartmentIdentifier>
                <DepartmentUUIDIdentifier>{str(dep1_uuid)}</DepartmentUUIDIdentifier>
              </EmploymentDepartment>
              <EmploymentDepartment>
                <ActivationDate>2002-01-01</ActivationDate>
                <DeactivationDate>9999-12-31</DeactivationDate>
                <DepartmentIdentifier>dep2</DepartmentIdentifier>
                <DepartmentUUIDIdentifier>{str(dep2_uuid)}</DepartmentUUIDIdentifier>
              </EmploymentDepartment>
              <Profession>
                <ActivationDate>2001-01-01</ActivationDate>
                <DeactivationDate>2002-12-31</DeactivationDate>
                <JobPositionIdentifier>9000</JobPositionIdentifier>
                <EmploymentName>name1</EmploymentName>
                <AppointmentCode>0</AppointmentCode>
              </Profession>
              <Profession>
                <ActivationDate>2003-01-01</ActivationDate>
                <DeactivationDate>2004-12-31</DeactivationDate>
                <JobPositionIdentifier>9000</JobPositionIdentifier>
                <EmploymentName>name2</EmploymentName>
                <AppointmentCode>0</AppointmentCode>
              </Profession>
              <Profession>
                <ActivationDate>2005-01-01</ActivationDate>
                <DeactivationDate>9999-12-31</DeactivationDate>
                <JobPositionIdentifier>9000</JobPositionIdentifier>
                <EmploymentName>name3</EmploymentName>
                <AppointmentCode>0</AppointmentCode>
              </Profession>
              <EmploymentStatus>
                <ActivationDate>2001-01-01</ActivationDate>
                <DeactivationDate>2002-12-31</DeactivationDate>
                <EmploymentStatusCode>1</EmploymentStatusCode>
              </EmploymentStatus>
              <EmploymentStatus>
                <ActivationDate>2003-01-01</ActivationDate>
                <DeactivationDate>2004-12-31</DeactivationDate>
                <EmploymentStatusCode>3</EmploymentStatusCode>
              </EmploymentStatus>
              <EmploymentStatus>
                <ActivationDate>2005-01-01</ActivationDate>
                <DeactivationDate>2005-12-31</DeactivationDate>
                <EmploymentStatusCode>8</EmploymentStatusCode>
              </EmploymentStatus>
              <EmploymentStatus>
                <ActivationDate>2006-01-01</ActivationDate>
                <DeactivationDate>2006-12-31</DeactivationDate>
                <EmploymentStatusCode>1</EmploymentStatusCode>
              </EmploymentStatus>
              <EmploymentStatus>
                <ActivationDate>2007-01-01</ActivationDate>
                <DeactivationDate>9999-12-31</DeactivationDate>
                <EmploymentStatusCode>8</EmploymentStatusCode>
              </EmploymentStatus>
              <WorkingTime>
                <ActivationDate>2001-01-01</ActivationDate>
                <DeactivationDate>2002-12-31</DeactivationDate>
                <OccupationRate>1.0000</OccupationRate>
                <SalaryRate>1.0000</SalaryRate>
                <SalariedIndicator>true</SalariedIndicator>
                <FullTimeIndicator>false</FullTimeIndicator>
              </WorkingTime>
              <WorkingTime>
                <ActivationDate>2003-01-01</ActivationDate>
                <DeactivationDate>9999-12-31</DeactivationDate>
                <OccupationRate>1.0000</OccupationRate>
                <SalaryRate>1.0000</SalaryRate>
                <SalariedIndicator>true</SalariedIndicator>
                <FullTimeIndicator>true</FullTimeIndicator>
              </WorkingTime>
            </Employment>
          </Person>
        </GetEmploymentChanged20111201>
    """

    respx_mock.get(
        "https://service.sd.dk/sdws/GetEmploymentChanged20111201?InstitutionIdentifier=II&PersonCivilRegistrationIdentifier=0101011234&EmploymentIdentifier=12345&ActivationDate=01.01.0001&DeactivationDate=31.12.9999&DepartmentIndicator=True&EmploymentStatusIndicator=True&ProfessionIndicator=True&SalaryAgreementIndicator=False&SalaryCodeGroupIndicator=False&WorkingTimeIndicator=True&UUIDIndicator=True"
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
        },
    )

    # Assert
    assert r.status_code == 200

    updated_eng = await graphql_client.get_engagement_timeline(
        person=person_uuid, user_key=f"II-{emp_id}", from_date=None, to_date=None
    )
    validities = one(updated_eng.objects).validities

    assert len(validities) == 5

    interval_1 = validities[0]
    assert interval_1.validity.from_ == t1
    assert _mo_end_to_timeline_end(interval_1.validity.to) == t2
    assert interval_1.extension_1 == "name1"
    assert interval_1.extension_2 == "dep1"
    assert interval_1.user_key == f"II-{emp_id}"
    assert interval_1.job_function.uuid == job_function_9000
    assert interval_1.extension_7 is None
    assert one(interval_1.org_unit).uuid == dep1_uuid
    assert interval_1.engagement_type.uuid == eng_types[EngType.MONTHLY_PART_TIME]

    interval_2 = validities[1]
    assert interval_2.validity.from_ == t2
    assert _mo_end_to_timeline_end(interval_2.validity.to) == t3
    assert interval_2.extension_1 == "name1"
    assert interval_2.extension_2 == "dep2"
    assert interval_2.user_key == f"II-{emp_id}"
    assert interval_2.job_function.uuid == job_function_9000
    assert one(interval_2.org_unit).uuid == dep2_uuid
    assert interval_2.extension_7 == "v1"
    assert interval_2.engagement_type.uuid == eng_types[EngType.MONTHLY_PART_TIME]

    interval_3 = validities[2]
    assert interval_3.validity.from_ == t3
    assert _mo_end_to_timeline_end(interval_3.validity.to) == t4
    assert interval_3.extension_1 == "name2"
    assert interval_3.extension_2 == "dep2"
    assert interval_3.user_key == f"II-{emp_id}"
    assert interval_3.job_function.uuid == job_function_9000
    assert one(interval_3.org_unit).uuid == dep2_uuid
    assert interval_3.extension_7 == "v2"
    assert interval_3.engagement_type.uuid == eng_types[EngType.MONTHLY_FULL_TIME]

    interval_4 = validities[3]
    assert interval_4.validity.from_ == t4
    assert _mo_end_to_timeline_end(interval_4.validity.to) == t5
    assert interval_4.extension_1 == "name2"
    assert interval_4.extension_2 == "dep2"
    assert interval_4.user_key == f"II-{emp_id}"
    assert interval_4.job_function.uuid == job_function_9000
    assert one(interval_4.org_unit).uuid == dep2_uuid
    assert interval_4.extension_7 == "v3"
    assert interval_4.engagement_type.uuid == eng_types[EngType.MONTHLY_FULL_TIME]

    interval_5 = validities[4]
    assert interval_5.validity.from_ == t6
    assert _mo_end_to_timeline_end(interval_5.validity.to) == t7
    assert interval_5.extension_1 == "name3"
    assert interval_5.extension_2 == "dep2"
    assert interval_5.user_key == f"II-{emp_id}"
    assert interval_5.job_function.uuid == job_function_9000
    assert one(interval_5.org_unit).uuid == dep2_uuid
    assert interval_5.extension_7 == "v5"
    assert interval_5.engagement_type.uuid == eng_types[EngType.MONTHLY_FULL_TIME]


@pytest.mark.integration_test
@pytest.mark.envvar({"MUNICIPALITY_MODE": "false"})
async def test_eng_timeline_where_patch_interval_is_longer_than_update_interval(
    test_client: AsyncClient,
    graphql_client: GraphQLClient,
    base_tree_builder: TestingCreateOrgUnitOrgUnitCreate,
    job_function_1234: UUID,
    job_function_5678: UUID,
    job_function_9000: UUID,
    respx_mock: MockRouter,
):
    """
    We are testing this scenario:

    Time  --------t1--------t2---------t3-------------t5-----t6------------t7------->

    MO (name)               |----------------------name4-----------------------------
    MO (key)                |-----------------------1234-----------------------------
    MO (unit)               |-----------------------dep3-----------------------------
    MO (unit ID)            |-----------------------dep3-----------------------------
    MO (ext_7)              |------------------------v1------------------------------
    MO (active)             |--------------------------------------------------------
    MO (eng_type)           |-----------------------full-----------------------------

    "Arrange" intervals     |-------------------------1------------------------------

    SD (name)     |-------name1--------|----name2-----|-------name3------------------
    SD (key)      |------------------------ 9000 ------------------------------------
    SD (unit)     |---dep1--|-------------------dep2---------------------------------
    SD (unit ID)  |---dep1--|-------------------dep2---------------------------------
    SD (active)   |---------1----------|-------3------|---8--|-------1-----|----8----
    SD (eng_type) |--------part--------|-------------------full----------------------

    "Assert"      |----1----|-----2----|-------3------|      |------4------|
    intervals

    In SD: name = EmploymentName, key = JobPositionIdentifier
           active = EmploymentStatusCode
    In MO: name = extension_1, key = user_key
    """
    # Arrange
    tz = ZoneInfo("Europe/Copenhagen")

    t1 = datetime(2001, 1, 1, tzinfo=tz)
    t2 = datetime(2002, 1, 1, tzinfo=tz)
    t3 = datetime(2003, 1, 1, tzinfo=tz)
    t5 = datetime(2005, 1, 1, tzinfo=tz)
    t6 = datetime(2006, 1, 1, tzinfo=tz)
    t7 = datetime(2007, 1, 1, tzinfo=tz)

    # Units
    dep1_uuid = UUID("10000000-0000-0000-0000-000000000000")
    dep2_uuid = UUID("20000000-0000-0000-0000-000000000000")
    dep3_uuid = UUID("30000000-0000-0000-0000-000000000000")

    eng_types = await get_engagement_types(graphql_client)

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

    # Create engagement (arrange interval 1)
    await graphql_client.create_engagement(
        EngagementCreateInput(
            user_key=user_key,
            validity=RAValidityInput(from_=t2, to=None),
            extension_1="name4",
            extension_2="dep3",
            extension_7="v1",
            person=person_uuid,
            org_unit=dep3_uuid,
            engagement_type=eng_types[EngType.MONTHLY_FULL_TIME],
            job_function=job_function_1234,
        )
    )

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
                <DeactivationDate>2001-12-31</DeactivationDate>
                <DepartmentIdentifier>dep1</DepartmentIdentifier>
                <DepartmentUUIDIdentifier>{str(dep1_uuid)}</DepartmentUUIDIdentifier>
              </EmploymentDepartment>
              <EmploymentDepartment>
                <ActivationDate>2002-01-01</ActivationDate>
                <DeactivationDate>9999-12-31</DeactivationDate>
                <DepartmentIdentifier>dep2</DepartmentIdentifier>
                <DepartmentUUIDIdentifier>{str(dep2_uuid)}</DepartmentUUIDIdentifier>
              </EmploymentDepartment>
              <Profession>
                <ActivationDate>2001-01-01</ActivationDate>
                <DeactivationDate>2002-12-31</DeactivationDate>
                <JobPositionIdentifier>9000</JobPositionIdentifier>
                <EmploymentName>name1</EmploymentName>
                <AppointmentCode>0</AppointmentCode>
              </Profession>
              <Profession>
                <ActivationDate>2003-01-01</ActivationDate>
                <DeactivationDate>2004-12-31</DeactivationDate>
                <JobPositionIdentifier>9000</JobPositionIdentifier>
                <EmploymentName>name2</EmploymentName>
                <AppointmentCode>0</AppointmentCode>
              </Profession>
              <Profession>
                <ActivationDate>2005-01-01</ActivationDate>
                <DeactivationDate>9999-12-31</DeactivationDate>
                <JobPositionIdentifier>9000</JobPositionIdentifier>
                <EmploymentName>name3</EmploymentName>
                <AppointmentCode>0</AppointmentCode>
              </Profession>
              <EmploymentStatus>
                <ActivationDate>2001-01-01</ActivationDate>
                <DeactivationDate>2002-12-31</DeactivationDate>
                <EmploymentStatusCode>1</EmploymentStatusCode>
              </EmploymentStatus>
              <EmploymentStatus>
                <ActivationDate>2003-01-01</ActivationDate>
                <DeactivationDate>2004-12-31</DeactivationDate>
                <EmploymentStatusCode>3</EmploymentStatusCode>
              </EmploymentStatus>
              <EmploymentStatus>
                <ActivationDate>2005-01-01</ActivationDate>
                <DeactivationDate>2005-12-31</DeactivationDate>
                <EmploymentStatusCode>8</EmploymentStatusCode>
              </EmploymentStatus>
              <EmploymentStatus>
                <ActivationDate>2006-01-01</ActivationDate>
                <DeactivationDate>2006-12-31</DeactivationDate>
                <EmploymentStatusCode>1</EmploymentStatusCode>
              </EmploymentStatus>
              <EmploymentStatus>
                <ActivationDate>2007-01-01</ActivationDate>
                <DeactivationDate>9999-12-31</DeactivationDate>
                <EmploymentStatusCode>8</EmploymentStatusCode>
              </EmploymentStatus>
              <WorkingTime>
                <ActivationDate>2001-01-01</ActivationDate>
                <DeactivationDate>2002-12-31</DeactivationDate>
                <OccupationRate>1.0000</OccupationRate>
                <SalaryRate>1.0000</SalaryRate>
                <SalariedIndicator>true</SalariedIndicator>
                <FullTimeIndicator>false</FullTimeIndicator>
              </WorkingTime>
              <WorkingTime>
                <ActivationDate>2003-01-01</ActivationDate>
                <DeactivationDate>9999-12-31</DeactivationDate>
                <OccupationRate>1.0000</OccupationRate>
                <SalaryRate>1.0000</SalaryRate>
                <SalariedIndicator>true</SalariedIndicator>
                <FullTimeIndicator>true</FullTimeIndicator>
              </WorkingTime>
            </Employment>
          </Person>
        </GetEmploymentChanged20111201>
    """

    respx_mock.get(
        "https://service.sd.dk/sdws/GetEmploymentChanged20111201?InstitutionIdentifier=II&PersonCivilRegistrationIdentifier=0101011234&EmploymentIdentifier=12345&ActivationDate=01.01.0001&DeactivationDate=31.12.9999&DepartmentIndicator=True&EmploymentStatusIndicator=True&ProfessionIndicator=True&SalaryAgreementIndicator=False&SalaryCodeGroupIndicator=False&WorkingTimeIndicator=True&UUIDIndicator=True"
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
        },
    )

    # Assert
    assert r.status_code == 200

    updated_eng = await graphql_client.get_engagement_timeline(
        person=person_uuid, user_key=f"II-{emp_id}", from_date=None, to_date=None
    )
    validities = one(updated_eng.objects).validities

    interval_1 = validities[0]
    assert interval_1.validity.from_ == t1
    assert _mo_end_to_timeline_end(interval_1.validity.to) == t2
    assert interval_1.extension_1 == "name1"
    assert interval_1.extension_2 == "dep1"
    assert interval_1.user_key == user_key
    assert interval_1.job_function.uuid == job_function_9000
    assert interval_1.extension_7 is None
    assert one(interval_1.org_unit).uuid == dep1_uuid
    assert interval_1.engagement_type.uuid == eng_types[EngType.MONTHLY_PART_TIME]

    interval_2 = validities[1]
    assert interval_2.validity.from_ == t2
    assert _mo_end_to_timeline_end(interval_2.validity.to) == t3
    assert interval_2.extension_1 == "name1"
    assert interval_2.extension_2 == "dep2"
    assert interval_2.user_key == user_key
    assert interval_2.job_function.uuid == job_function_9000
    assert one(interval_2.org_unit).uuid == dep2_uuid
    assert interval_2.extension_7 == "v1"
    assert interval_2.engagement_type.uuid == eng_types[EngType.MONTHLY_PART_TIME]

    interval_3 = validities[2]
    assert interval_3.validity.from_ == t3
    assert _mo_end_to_timeline_end(interval_3.validity.to) == t5
    assert interval_3.extension_1 == "name2"
    assert interval_3.extension_2 == "dep2"
    assert interval_3.user_key == user_key
    assert interval_3.job_function.uuid == job_function_9000
    assert one(interval_3.org_unit).uuid == dep2_uuid
    assert interval_3.extension_7 == "v1"
    assert interval_3.engagement_type.uuid == eng_types[EngType.MONTHLY_FULL_TIME]

    interval_4 = validities[3]
    assert interval_4.validity.from_ == t6
    assert _mo_end_to_timeline_end(interval_4.validity.to) == t7
    assert interval_4.extension_1 == "name3"
    assert interval_4.extension_2 == "dep2"
    assert interval_4.user_key == user_key
    assert interval_4.job_function.uuid == job_function_9000
    assert one(interval_4.org_unit).uuid == dep2_uuid
    assert interval_4.extension_7 == "v1"
    assert interval_4.engagement_type.uuid == eng_types[EngType.MONTHLY_FULL_TIME]

    assert len(validities) == 4


@pytest.mark.integration_test
@pytest.mark.envvar({"MUNICIPALITY_MODE": "false"})
async def test_eng_timeline_create_new_engagement(
    test_client: AsyncClient,
    graphql_client: GraphQLClient,
    base_tree_builder: TestingCreateOrgUnitOrgUnitCreate,
    job_function_1234: UUID,
    job_function_5678: UUID,
    job_function_9000: UUID,
    respx_mock: MockRouter,
):
    """
    We are testing this scenario:

    Time  --------t1--------t2---------t3-------------t5-----t6--------------------->

    MO (engagement does not exist)

    SD (name)     |-------name1--------|----name2-----|-------name3------------------
    SD (key)      |------------------------ 9000 ------------------------------------
    SD (unit)     |---dep1--|-------------------dep2---------------------------------
    SD (unit ID)  |---dep1--|-------------------dep2---------------------------------
    SD (active)   |---------1----------|-------3------|---8--|-----------1-----------
    SD (eng_type) |--------part--------|-------------------full----------------------

    "Assert"      |----1----|-----2----|------3-------|      |------------4----------
    intervals

    In SD: name = EmploymentName, key = JobPositionIdentifier
           active = EmploymentStatusCode
    In MO: name = extension_1, key = user_key
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
    dep2_uuid = UUID("20000000-0000-0000-0000-000000000000")

    eng_types = await get_engagement_types(graphql_client)

    # Create person
    person_uuid = uuid4()
    cpr = "0101011234"
    emp_id = "12345"

    await graphql_client.create_person(
        EmployeeCreateInput(
            uuid=person_uuid,
            cpr_number=cpr,
            given_name="Chuck",
            surname="Norris",
        )
    )

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
                <DeactivationDate>2001-12-31</DeactivationDate>
                <DepartmentIdentifier>dep1</DepartmentIdentifier>
                <DepartmentUUIDIdentifier>{str(dep1_uuid)}</DepartmentUUIDIdentifier>
              </EmploymentDepartment>
              <EmploymentDepartment>
                <ActivationDate>2002-01-01</ActivationDate>
                <DeactivationDate>9999-12-31</DeactivationDate>
                <DepartmentIdentifier>dep2</DepartmentIdentifier>
                <DepartmentUUIDIdentifier>{str(dep2_uuid)}</DepartmentUUIDIdentifier>
              </EmploymentDepartment>
              <Profession>
                <ActivationDate>2001-01-01</ActivationDate>
                <DeactivationDate>2002-12-31</DeactivationDate>
                <JobPositionIdentifier>9000</JobPositionIdentifier>
                <EmploymentName>name1</EmploymentName>
                <AppointmentCode>0</AppointmentCode>
              </Profession>
              <Profession>
                <ActivationDate>2003-01-01</ActivationDate>
                <DeactivationDate>2004-12-31</DeactivationDate>
                <JobPositionIdentifier>9000</JobPositionIdentifier>
                <EmploymentName>name2</EmploymentName>
                <AppointmentCode>0</AppointmentCode>
              </Profession>
              <Profession>
                <ActivationDate>2005-01-01</ActivationDate>
                <DeactivationDate>9999-12-31</DeactivationDate>
                <JobPositionIdentifier>9000</JobPositionIdentifier>
                <EmploymentName>name3</EmploymentName>
                <AppointmentCode>0</AppointmentCode>
              </Profession>
              <EmploymentStatus>
                <ActivationDate>2001-01-01</ActivationDate>
                <DeactivationDate>2002-12-31</DeactivationDate>
                <EmploymentStatusCode>1</EmploymentStatusCode>
              </EmploymentStatus>
              <EmploymentStatus>
                <ActivationDate>2003-01-01</ActivationDate>
                <DeactivationDate>2004-12-31</DeactivationDate>
                <EmploymentStatusCode>3</EmploymentStatusCode>
              </EmploymentStatus>
              <EmploymentStatus>
                <ActivationDate>2005-01-01</ActivationDate>
                <DeactivationDate>2005-12-31</DeactivationDate>
                <EmploymentStatusCode>8</EmploymentStatusCode>
              </EmploymentStatus>
              <EmploymentStatus>
                <ActivationDate>2006-01-01</ActivationDate>
                <DeactivationDate>9999-12-31</DeactivationDate>
                <EmploymentStatusCode>1</EmploymentStatusCode>
              </EmploymentStatus>
              <WorkingTime>
                <ActivationDate>2001-01-01</ActivationDate>
                <DeactivationDate>2002-12-31</DeactivationDate>
                <OccupationRate>1.0000</OccupationRate>
                <SalaryRate>1.0000</SalaryRate>
                <SalariedIndicator>true</SalariedIndicator>
                <FullTimeIndicator>false</FullTimeIndicator>
              </WorkingTime>
              <WorkingTime>
                <ActivationDate>2003-01-01</ActivationDate>
                <DeactivationDate>9999-12-31</DeactivationDate>
                <OccupationRate>1.0000</OccupationRate>
                <SalaryRate>1.0000</SalaryRate>
                <SalariedIndicator>true</SalariedIndicator>
                <FullTimeIndicator>true</FullTimeIndicator>
              </WorkingTime>
            </Employment>
          </Person>
        </GetEmploymentChanged20111201>
    """

    respx_mock.get(
        "https://service.sd.dk/sdws/GetEmploymentChanged20111201?InstitutionIdentifier=II&PersonCivilRegistrationIdentifier=0101011234&EmploymentIdentifier=12345&ActivationDate=01.01.0001&DeactivationDate=31.12.9999&DepartmentIndicator=True&EmploymentStatusIndicator=True&ProfessionIndicator=True&SalaryAgreementIndicator=False&SalaryCodeGroupIndicator=False&WorkingTimeIndicator=True&UUIDIndicator=True"
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
        },
    )

    # Assert
    assert r.status_code == 200

    updated_eng = await graphql_client.get_engagement_timeline(
        person=person_uuid, user_key=f"II-{emp_id}", from_date=None, to_date=None
    )
    validities = one(updated_eng.objects).validities

    assert len(validities) == 4

    interval_1 = validities[0]
    assert interval_1.validity.from_ == t1
    assert _mo_end_to_timeline_end(interval_1.validity.to) == t2
    assert interval_1.extension_1 == "name1"
    assert interval_1.extension_2 == "dep1"
    assert interval_1.user_key == f"II-{emp_id}"
    assert interval_1.job_function.uuid == job_function_9000
    assert one(interval_1.org_unit).uuid == dep1_uuid
    assert interval_1.engagement_type.uuid == eng_types[EngType.MONTHLY_PART_TIME]

    interval_2 = validities[1]
    assert interval_2.validity.from_ == t2
    assert _mo_end_to_timeline_end(interval_2.validity.to) == t3
    assert interval_2.extension_1 == "name1"
    assert interval_2.extension_2 == "dep2"
    assert interval_2.user_key == f"II-{emp_id}"
    assert interval_2.job_function.uuid == job_function_9000
    assert one(interval_2.org_unit).uuid == dep2_uuid
    assert interval_2.engagement_type.uuid == eng_types[EngType.MONTHLY_PART_TIME]

    interval_3 = validities[2]
    assert interval_3.validity.from_ == t3
    assert _mo_end_to_timeline_end(interval_3.validity.to) == t5
    assert interval_3.extension_1 == "name2"
    assert interval_3.extension_2 == "dep2"
    assert interval_3.user_key == f"II-{emp_id}"
    assert interval_3.job_function.uuid == job_function_9000
    assert one(interval_3.org_unit).uuid == dep2_uuid
    assert interval_3.engagement_type.uuid == eng_types[EngType.MONTHLY_FULL_TIME]

    interval_4 = validities[3]
    assert interval_4.validity.from_ == t6
    assert _mo_end_to_timeline_end(interval_4.validity.to) == POSITIVE_INFINITY
    assert interval_4.extension_1 == "name3"
    assert interval_4.extension_2 == "dep2"
    assert interval_4.user_key == f"II-{emp_id}"
    assert interval_4.job_function.uuid == job_function_9000
    assert one(interval_4.org_unit).uuid == dep2_uuid
    assert interval_4.engagement_type.uuid == eng_types[EngType.MONTHLY_FULL_TIME]
