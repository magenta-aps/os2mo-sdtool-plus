# Generated by ariadne-codegen on 2025-03-10 11:37
# Source: queries.graphql

from datetime import datetime
from typing import Any
from typing import Optional
from typing import Union
from uuid import UUID

from ._testing__create_employee import TestingCreateEmployee
from ._testing__create_employee import TestingCreateEmployeeEmployeeCreate
from ._testing__create_engagement import TestingCreateEngagement
from ._testing__create_engagement import TestingCreateEngagementEngagementCreate
from ._testing__create_org_unit import TestingCreateOrgUnit
from ._testing__create_org_unit import TestingCreateOrgUnitOrgUnitCreate
from ._testing__create_person import TestingCreatePerson
from ._testing__create_person import TestingCreatePersonEmployeeCreate
from ._testing__get_org_unit import TestingGetOrgUnit
from ._testing__get_org_unit import TestingGetOrgUnitOrgUnits
from ._testing__get_org_unit_address import TestingGetOrgUnitAddress
from ._testing__get_org_unit_address import TestingGetOrgUnitAddressOrgUnits
from .address_types import AddressTypes
from .address_types import AddressTypesFacets
from .async_base_client import AsyncBaseClient
from .base_model import UNSET
from .base_model import UnsetType
from .create_address import CreateAddress
from .create_address import CreateAddressAddressCreate
from .create_engagement import CreateEngagement
from .create_engagement import CreateEngagementEngagementCreate
from .create_org_unit import CreateOrgUnit
from .create_org_unit import CreateOrgUnitOrgUnitCreate
from .get_engagement_timeline import GetEngagementTimeline
from .get_engagement_timeline import GetEngagementTimelineEngagements
from .get_facet_class import GetFacetClass
from .get_facet_class import GetFacetClassClasses
from .get_org_unit_timeline import GetOrgUnitTimeline
from .get_org_unit_timeline import GetOrgUnitTimelineOrgUnits
from .get_organization import GetOrganization
from .get_organization import GetOrganizationOrg
from .get_person import GetPerson
from .get_person import GetPersonEmployees
from .input_types import AddressCreateInput
from .input_types import AddressUpdateInput
from .input_types import EmployeeCreateInput
from .input_types import EngagementCreateInput
from .input_types import EngagementTerminateInput
from .input_types import EngagementUpdateInput
from .input_types import OrganisationUnitCreateInput
from .input_types import OrganisationUnitTerminateInput
from .input_types import OrganisationUnitUpdateInput
from .terminate_engagement import TerminateEngagement
from .terminate_engagement import TerminateEngagementEngagementTerminate
from .terminate_org_unit import TerminateOrgUnit
from .terminate_org_unit import TerminateOrgUnitOrgUnitTerminate
from .update_address import UpdateAddress
from .update_address import UpdateAddressAddressUpdate
from .update_engagement import UpdateEngagement
from .update_engagement import UpdateEngagementEngagementUpdate
from .update_org_unit import UpdateOrgUnit
from .update_org_unit import UpdateOrgUnitOrgUnitUpdate


def gql(q: str) -> str:
    return q


class GraphQLClient(AsyncBaseClient):
    async def get_organization(self) -> GetOrganizationOrg:
        query = gql(
            """
            query GetOrganization {
              org {
                uuid
              }
            }
            """
        )
        variables: dict[str, object] = {}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return GetOrganization.parse_obj(data).org

    async def address_types(self) -> AddressTypesFacets:
        query = gql(
            """
            query AddressTypes {
              facets(filter: {user_keys: "org_unit_address_type"}) {
                objects {
                  current {
                    user_key
                    uuid
                    classes {
                      uuid
                      user_key
                      name
                    }
                  }
                }
              }
            }
            """
        )
        variables: dict[str, object] = {}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return AddressTypes.parse_obj(data).facets

    async def create_address(
        self, input: AddressCreateInput
    ) -> CreateAddressAddressCreate:
        query = gql(
            """
            mutation CreateAddress($input: AddressCreateInput!) {
              address_create(input: $input) {
                current {
                  validity {
                    from
                    to
                  }
                  uuid
                  name
                  address_type {
                    user_key
                  }
                }
              }
            }
            """
        )
        variables: dict[str, object] = {"input": input}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return CreateAddress.parse_obj(data).address_create

    async def update_address(
        self, input: AddressUpdateInput
    ) -> UpdateAddressAddressUpdate:
        query = gql(
            """
            mutation UpdateAddress($input: AddressUpdateInput!) {
              address_update(input: $input) {
                current {
                  validity {
                    from
                    to
                  }
                  uuid
                  name
                  address_type {
                    user_key
                  }
                }
              }
            }
            """
        )
        variables: dict[str, object] = {"input": input}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return UpdateAddress.parse_obj(data).address_update

    async def get_facet_class(
        self, facet_user_key: str, class_user_key: str
    ) -> GetFacetClassClasses:
        query = gql(
            """
            query GetFacetClass($facet_user_key: String!, $class_user_key: String!) {
              classes(
                filter: {user_keys: [$class_user_key], facet: {user_keys: [$facet_user_key]}}
              ) {
                objects {
                  current {
                    uuid
                    user_key
                    name
                    scope
                  }
                }
              }
            }
            """
        )
        variables: dict[str, object] = {
            "facet_user_key": facet_user_key,
            "class_user_key": class_user_key,
        }
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return GetFacetClass.parse_obj(data).classes

    async def get_org_unit_timeline(
        self,
        unit_uuid: UUID,
        from_date: Union[Optional[datetime], UnsetType] = UNSET,
        to_date: Union[Optional[datetime], UnsetType] = UNSET,
    ) -> GetOrgUnitTimelineOrgUnits:
        query = gql(
            """
            query GetOrgUnitTimeline($unit_uuid: UUID!, $from_date: DateTime, $to_date: DateTime) {
              org_units(
                filter: {uuids: [$unit_uuid], from_date: $from_date, to_date: $to_date}
              ) {
                objects {
                  validities {
                    validity {
                      from
                      to
                    }
                    uuid
                    user_key
                    name
                    org_unit_level {
                      name
                    }
                    unit_type {
                      uuid
                    }
                    org_unit_hierarchy_model {
                      uuid
                    }
                    time_planning {
                      uuid
                    }
                    parent {
                      uuid
                    }
                  }
                }
              }
            }
            """
        )
        variables: dict[str, object] = {
            "unit_uuid": unit_uuid,
            "from_date": from_date,
            "to_date": to_date,
        }
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return GetOrgUnitTimeline.parse_obj(data).org_units

    async def create_org_unit(
        self, input: OrganisationUnitCreateInput
    ) -> CreateOrgUnitOrgUnitCreate:
        query = gql(
            """
            mutation CreateOrgUnit($input: OrganisationUnitCreateInput!) {
              org_unit_create(input: $input) {
                uuid
              }
            }
            """
        )
        variables: dict[str, object] = {"input": input}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return CreateOrgUnit.parse_obj(data).org_unit_create

    async def update_org_unit(
        self, input: OrganisationUnitUpdateInput
    ) -> UpdateOrgUnitOrgUnitUpdate:
        query = gql(
            """
            mutation UpdateOrgUnit($input: OrganisationUnitUpdateInput!) {
              org_unit_update(input: $input) {
                uuid
              }
            }
            """
        )
        variables: dict[str, object] = {"input": input}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return UpdateOrgUnit.parse_obj(data).org_unit_update

    async def terminate_org_unit(
        self, input: OrganisationUnitTerminateInput
    ) -> TerminateOrgUnitOrgUnitTerminate:
        query = gql(
            """
            mutation TerminateOrgUnit($input: OrganisationUnitTerminateInput!) {
              org_unit_terminate(input: $input) {
                uuid
              }
            }
            """
        )
        variables: dict[str, object] = {"input": input}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return TerminateOrgUnit.parse_obj(data).org_unit_terminate

    async def get_person(self, cpr: Any) -> GetPersonEmployees:
        query = gql(
            """
            query GetPerson($cpr: CPR!) {
              employees(filter: {cpr_numbers: [$cpr], from_date: null, to_date: null}) {
                objects {
                  validities {
                    uuid
                  }
                }
              }
            }
            """
        )
        variables: dict[str, object] = {"cpr": cpr}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return GetPerson.parse_obj(data).employees

    async def create_engagement(
        self, input: EngagementCreateInput
    ) -> CreateEngagementEngagementCreate:
        query = gql(
            """
            mutation CreateEngagement($input: EngagementCreateInput!) {
              engagement_create(input: $input) {
                uuid
              }
            }
            """
        )
        variables: dict[str, object] = {"input": input}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return CreateEngagement.parse_obj(data).engagement_create

    async def get_engagement_timeline(
        self,
        cpr: Any,
        user_key: str,
        from_date: Union[Optional[datetime], UnsetType] = UNSET,
        to_date: Union[Optional[datetime], UnsetType] = UNSET,
    ) -> GetEngagementTimelineEngagements:
        query = gql(
            """
            query GetEngagementTimeline($cpr: CPR!, $user_key: String!, $from_date: DateTime, $to_date: DateTime) {
              engagements(
                filter: {employee: {cpr_numbers: [$cpr]}, user_keys: [$user_key], from_date: $from_date, to_date: $to_date}
              ) {
                objects {
                  validities {
                    uuid
                    user_key
                    primary {
                      uuid
                    }
                    validity {
                      from
                      to
                    }
                    extension_1
                    extension_2
                    extension_3
                    extension_4
                    extension_5
                    extension_6
                    extension_7
                    extension_8
                    extension_9
                    extension_10
                    person {
                      uuid
                    }
                    org_unit {
                      uuid
                    }
                    engagement_type {
                      uuid
                    }
                    job_function {
                      uuid
                      user_key
                    }
                  }
                }
              }
            }
            """
        )
        variables: dict[str, object] = {
            "cpr": cpr,
            "user_key": user_key,
            "from_date": from_date,
            "to_date": to_date,
        }
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return GetEngagementTimeline.parse_obj(data).engagements

    async def update_engagement(
        self, input: EngagementUpdateInput
    ) -> UpdateEngagementEngagementUpdate:
        query = gql(
            """
            mutation UpdateEngagement($input: EngagementUpdateInput!) {
              engagement_update(input: $input) {
                uuid
              }
            }
            """
        )
        variables: dict[str, object] = {"input": input}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return UpdateEngagement.parse_obj(data).engagement_update

    async def terminate_engagement(
        self, input: EngagementTerminateInput
    ) -> TerminateEngagementEngagementTerminate:
        query = gql(
            """
            mutation TerminateEngagement($input: EngagementTerminateInput!) {
              engagement_terminate(input: $input) {
                uuid
              }
            }
            """
        )
        variables: dict[str, object] = {"input": input}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return TerminateEngagement.parse_obj(data).engagement_terminate

    async def _testing__create_employee(
        self, uuid: UUID, given_name: str, surname: str
    ) -> TestingCreateEmployeeEmployeeCreate:
        query = gql(
            """
            mutation _Testing_CreateEmployee($uuid: UUID!, $given_name: String!, $surname: String!) {
              employee_create(
                input: {uuid: $uuid, given_name: $given_name, surname: $surname}
              ) {
                uuid
              }
            }
            """
        )
        variables: dict[str, object] = {
            "uuid": uuid,
            "given_name": given_name,
            "surname": surname,
        }
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return TestingCreateEmployee.parse_obj(data).employee_create

    async def _testing__create_org_unit(
        self,
        uuid: UUID,
        name: str,
        user_key: str,
        from_date: datetime,
        org_unit_type: UUID,
        org_unit_level: Union[Optional[UUID], UnsetType] = UNSET,
        parent: Union[Optional[UUID], UnsetType] = UNSET,
    ) -> TestingCreateOrgUnitOrgUnitCreate:
        query = gql(
            """
            mutation _Testing_CreateOrgUnit($uuid: UUID!, $name: String!, $user_key: String!, $from_date: DateTime!, $org_unit_type: UUID!, $org_unit_level: UUID, $parent: UUID) {
              org_unit_create(
                input: {uuid: $uuid, name: $name, user_key: $user_key, validity: {from: $from_date}, org_unit_type: $org_unit_type, org_unit_level: $org_unit_level, parent: $parent}
              ) {
                uuid
              }
            }
            """
        )
        variables: dict[str, object] = {
            "uuid": uuid,
            "name": name,
            "user_key": user_key,
            "from_date": from_date,
            "org_unit_type": org_unit_type,
            "org_unit_level": org_unit_level,
            "parent": parent,
        }
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return TestingCreateOrgUnit.parse_obj(data).org_unit_create

    async def _testing__get_org_unit(self, uuid: UUID) -> TestingGetOrgUnitOrgUnits:
        query = gql(
            """
            query _Testing_GetOrgUnit($uuid: UUID!) {
              org_units(filter: {uuids: [$uuid]}) {
                objects {
                  current {
                    validity {
                      from
                      to
                    }
                    uuid
                    user_key
                    name
                    parent {
                      uuid
                      name
                    }
                    org_unit_level {
                      uuid
                      user_key
                      name
                    }
                  }
                }
              }
            }
            """
        )
        variables: dict[str, object] = {"uuid": uuid}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return TestingGetOrgUnit.parse_obj(data).org_units

    async def _testing__create_engagement(
        self,
        from_date: datetime,
        org_unit: UUID,
        engagement_type: UUID,
        job_function: UUID,
        person: UUID,
    ) -> TestingCreateEngagementEngagementCreate:
        query = gql(
            """
            mutation _Testing_CreateEngagement($from_date: DateTime!, $org_unit: UUID!, $engagement_type: UUID!, $job_function: UUID!, $person: UUID!) {
              engagement_create(
                input: {validity: {from: $from_date}, org_unit: $org_unit, engagement_type: $engagement_type, job_function: $job_function, person: $person}
              ) {
                uuid
              }
            }
            """
        )
        variables: dict[str, object] = {
            "from_date": from_date,
            "org_unit": org_unit,
            "engagement_type": engagement_type,
            "job_function": job_function,
            "person": person,
        }
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return TestingCreateEngagement.parse_obj(data).engagement_create

    async def _testing__get_org_unit_address(
        self, org_unit: UUID, addr_type: UUID
    ) -> TestingGetOrgUnitAddressOrgUnits:
        query = gql(
            """
            query _Testing_GetOrgUnitAddress($org_unit: UUID!, $addr_type: UUID!) {
              org_units(filter: {uuids: [$org_unit]}) {
                objects {
                  current {
                    addresses(filter: {address_types: [$addr_type]}) {
                      value
                      user_key
                    }
                  }
                }
              }
            }
            """
        )
        variables: dict[str, object] = {"org_unit": org_unit, "addr_type": addr_type}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return TestingGetOrgUnitAddress.parse_obj(data).org_units

    async def _testing__create_person(
        self, input: EmployeeCreateInput
    ) -> TestingCreatePersonEmployeeCreate:
        query = gql(
            """
            mutation _Testing_CreatePerson($input: EmployeeCreateInput!) {
              employee_create(input: $input) {
                uuid
              }
            }
            """
        )
        variables: dict[str, object] = {"input": input}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return TestingCreatePerson.parse_obj(data).employee_create
