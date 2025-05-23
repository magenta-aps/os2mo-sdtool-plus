# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from unittest import TestCase
from unittest.mock import ANY

import pytest
from httpx import AsyncClient
from more_itertools import one
from respx import MockRouter

from sdtoolplus.autogenerated_graphql_client.client import GraphQLClient
from sdtoolplus.autogenerated_graphql_client.get_class import (
    GetClassClassesObjects as Class,
)
from sdtoolplus.autogenerated_graphql_client.get_class import (
    GetClassClassesObjectsCurrent as ClassCurrent,
)
from sdtoolplus.autogenerated_graphql_client.get_class import (
    GetClassClassesObjectsCurrentParent as Parent,
)
from sdtoolplus.autogenerated_graphql_client.input_types import ClassCreateInput
from sdtoolplus.autogenerated_graphql_client.input_types import ClassFilter
from sdtoolplus.autogenerated_graphql_client.input_types import FacetFilter
from sdtoolplus.autogenerated_graphql_client.input_types import ValidityInput


@pytest.mark.integration_test
async def test_sync_job_positions(
    test_client: AsyncClient,
    graphql_client: GraphQLClient,
    respx_mock: MockRouter,
):
    engagement_job_function_uuid = one(
        (await graphql_client.get_facet_uuid("engagement_job_function")).objects
    ).uuid

    foo = await graphql_client.create_class(
        ClassCreateInput(
            facet_uuid=engagement_job_function_uuid,
            user_key="foo",
            name="foo",
            scope="0",
            parent_uuid=None,
            validity=ValidityInput(
                from_="2000-01-01T00:00:00+00:00",
                to=None,
            ),
        )
    )
    bar = await graphql_client.create_class(
        ClassCreateInput(
            facet_uuid=engagement_job_function_uuid,
            user_key="bar",
            name="wrong name",
            scope="1",
            parent_uuid=foo.uuid,  # wrong parent
            validity=ValidityInput(
                from_="2000-01-01T00:00:00+00:00",
                to=None,
            ),
        )
    )

    respx_mock.get(
        "https://service.sd.dk/sdws/GetProfession20080201?InstitutionIdentifier=II"
    ).respond(
        content_type="text/xml;charset=UTF-8",
        content="""<?xml version="1.0" encoding="UTF-8"?>
          <GetProfession20080201 creationTime="2025-03-19T11:10:16">
            <RequestKey>
              <InstitutionIdentifier>II</InstitutionIdentifier>
            </RequestKey>
            <Profession>
              <JobPositionIdentifier>foo</JobPositionIdentifier>
              <JobPositionName>foo</JobPositionName>
              <JobPositionLevelCode>0</JobPositionLevelCode>
              <Profession>
                <JobPositionIdentifier>foofoo</JobPositionIdentifier>
                <JobPositionName>foofoo</JobPositionName>
                <JobPositionLevelCode>2</JobPositionLevelCode>
                <Profession>
                  <JobPositionIdentifier>foofoofoo</JobPositionIdentifier>
                  <JobPositionName>foofoofoo</JobPositionName>
                  <JobPositionLevelCode>1</JobPositionLevelCode>
                </Profession>
                <Profession>
                  <JobPositionIdentifier>foofoobar</JobPositionIdentifier>
                  <JobPositionName>foofoobar</JobPositionName>
                  <JobPositionLevelCode>3</JobPositionLevelCode>
                </Profession>
              </Profession>
            </Profession>
            <Profession>
              <JobPositionIdentifier>bar</JobPositionIdentifier>
              <JobPositionName>bar</JobPositionName>
              <JobPositionLevelCode>1</JobPositionLevelCode>
            </Profession>
          </GetProfession20080201>
        """,
    )

    r = await test_client.post(
        "/job-functions/sync",
        params={"institution_identifier": "II"},
    )
    assert r.status_code == 200

    actual = await graphql_client.get_class(
        ClassFilter(
            facet=FacetFilter(user_keys=["engagement_job_function"]),
            user_keys=["foo", "foofoo", "foofoofoo", "foofoobar", "bar"],
        )
    )
    expected = [
        Class.construct(
            uuid=foo.uuid,
            current=ClassCurrent.construct(
                uuid=foo.uuid,
                user_key="foo",
                name="foo",
                scope="0",
                parent=None,
            ),
        ),
        Class.construct(
            uuid=ANY,
            current=ClassCurrent.construct(
                uuid=ANY,
                user_key="foofoo",
                name="foofoo",
                scope="2",
                parent=Parent.construct(
                    uuid=foo.uuid,
                    user_key="foo",
                ),
            ),
        ),
        Class.construct(
            uuid=ANY,
            current=ClassCurrent.construct(
                uuid=ANY,
                user_key="foofoofoo",
                name="foofoofoo",
                scope="1",
                parent=Parent.construct(
                    uuid=ANY,
                    user_key="foofoo",
                ),
            ),
        ),
        Class.construct(
            uuid=ANY,
            current=ClassCurrent.construct(
                uuid=ANY,
                user_key="foofoobar",
                name="foofoobar",
                scope="3",
                parent=Parent.construct(
                    uuid=ANY,
                    user_key="foofoo",
                ),
            ),
        ),
        Class.construct(
            uuid=bar.uuid,
            current=ClassCurrent.construct(
                uuid=bar.uuid,
                user_key="bar",
                name="bar",
                scope="1",
                parent=None,
            ),
        ),
    ]
    TestCase().assertCountEqual(actual.objects, expected)
