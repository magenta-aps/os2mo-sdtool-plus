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
from ._testing__get_org_unit import TestingGetOrgUnit
from ._testing__get_org_unit import TestingGetOrgUnitOrgUnits
from ._testing__get_org_unit_address import TestingGetOrgUnitAddress
from ._testing__get_org_unit_address import TestingGetOrgUnitAddressOrgUnits
from ._testing__update_related_units import TestingUpdateRelatedUnits
from ._testing__update_related_units import TestingUpdateRelatedUnitsRelatedUnitsUpdate
from .address_types import AddressTypes
from .address_types import AddressTypesFacets
from .async_base_client import AsyncBaseClient
from .base_model import UNSET
from .base_model import UnsetType
from .create_address import CreateAddress
from .create_address import CreateAddressAddressCreate
from .create_class import CreateClass
from .create_class import CreateClassClassCreate
from .create_engagement import CreateEngagement
from .create_engagement import CreateEngagementEngagementCreate
from .create_leave import CreateLeave
from .create_leave import CreateLeaveLeaveCreate
from .create_org_unit import CreateOrgUnit
from .create_org_unit import CreateOrgUnitOrgUnitCreate
from .create_person import CreatePerson
from .create_person import CreatePersonEmployeeCreate
from .delete_address import DeleteAddress
from .delete_address import DeleteAddressAddressDelete
from .get_address_timeline import GetAddressTimeline
from .get_address_timeline import GetAddressTimelineAddresses
from .get_class import GetClass
from .get_class import GetClassClasses
from .get_engagement_timeline import GetEngagementTimeline
from .get_engagement_timeline import GetEngagementTimelineEngagements
from .get_engagements import GetEngagements
from .get_engagements import GetEngagementsEngagements
from .get_facet_uuid import GetFacetUuid
from .get_facet_uuid import GetFacetUuidFacets
from .get_leave import GetLeave
from .get_leave import GetLeaveLeaves
from .get_org_unit_timeline import GetOrgUnitTimeline
from .get_org_unit_timeline import GetOrgUnitTimelineOrgUnits
from .get_organization import GetOrganization
from .get_organization import GetOrganizationOrg
from .get_parent_roots import GetParentRoots
from .get_parent_roots import GetParentRootsOrgUnits
from .get_person import GetPerson
from .get_person import GetPersonEmployees
from .get_person_timeline import GetPersonTimeline
from .get_person_timeline import GetPersonTimelineEmployees
from .get_related_units import GetRelatedUnits
from .get_related_units import GetRelatedUnitsRelatedUnits
from .input_types import AddressCreateInput
from .input_types import AddressFilter
from .input_types import AddressTerminateInput
from .input_types import AddressUpdateInput
from .input_types import ClassCreateInput
from .input_types import ClassFilter
from .input_types import ClassUpdateInput
from .input_types import EmployeeCreateInput
from .input_types import EmployeeFilter
from .input_types import EmployeeUpdateInput
from .input_types import EngagementCreateInput
from .input_types import EngagementFilter
from .input_types import EngagementTerminateInput
from .input_types import EngagementUpdateInput
from .input_types import EventSendInput
from .input_types import LeaveCreateInput
from .input_types import LeaveFilter
from .input_types import LeaveTerminateInput
from .input_types import LeaveUpdateInput
from .input_types import OrganisationUnitCreateInput
from .input_types import OrganisationUnitFilter
from .input_types import OrganisationUnitTerminateInput
from .input_types import OrganisationUnitUpdateInput
from .input_types import RelatedUnitFilter
from .input_types import RelatedUnitsUpdateInput
from .send_event import SendEvent
from .terminate_address import TerminateAddress
from .terminate_address import TerminateAddressAddressTerminate
from .terminate_engagement import TerminateEngagement
from .terminate_engagement import TerminateEngagementEngagementTerminate
from .terminate_leave import TerminateLeave
from .terminate_leave import TerminateLeaveLeaveTerminate
from .terminate_org_unit import TerminateOrgUnit
from .terminate_org_unit import TerminateOrgUnitOrgUnitTerminate
from .update_address import UpdateAddress
from .update_address import UpdateAddressAddressUpdate
from .update_class import UpdateClass
from .update_class import UpdateClassClassUpdate
from .update_engagement import UpdateEngagement
from .update_engagement import UpdateEngagementEngagementUpdate
from .update_leave import UpdateLeave
from .update_leave import UpdateLeaveLeaveUpdate
from .update_org_unit import UpdateOrgUnit
from .update_org_unit import UpdateOrgUnitOrgUnitUpdate
from .update_person import UpdatePerson
from .update_person import UpdatePersonEmployeeUpdate


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

    async def get_address_timeline(
        self, input: AddressFilter
    ) -> GetAddressTimelineAddresses:
        query = gql(
            """
            query GetAddressTimeline($input: AddressFilter!) {
              addresses(filter: $input) {
                objects {
                  uuid
                  validities {
                    address_type {
                      uuid
                      name
                      user_key
                    }
                    visibility_uuid
                    user_key
                    value
                    uuid
                    validity {
                      from
                      to
                    }
                  }
                }
              }
            }
            """
        )
        variables: dict[str, object] = {"input": input}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return GetAddressTimeline.parse_obj(data).addresses

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
                uuid
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
                uuid
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

    async def terminate_address(
        self, input: AddressTerminateInput
    ) -> TerminateAddressAddressTerminate:
        query = gql(
            """
            mutation TerminateAddress($input: AddressTerminateInput!) {
              address_terminate(input: $input) {
                uuid
              }
            }
            """
        )
        variables: dict[str, object] = {"input": input}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return TerminateAddress.parse_obj(data).address_terminate

    async def delete_address(self, addr_uuid: UUID) -> DeleteAddressAddressDelete:
        query = gql(
            """
            mutation DeleteAddress($addr_uuid: UUID!) {
              address_delete(uuid: $addr_uuid) {
                uuid
              }
            }
            """
        )
        variables: dict[str, object] = {"addr_uuid": addr_uuid}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return DeleteAddress.parse_obj(data).address_delete

    async def get_facet_uuid(self, user_key: str) -> GetFacetUuidFacets:
        query = gql(
            """
            query GetFacetUuid($user_key: String!) {
              facets(filter: {user_keys: [$user_key]}) {
                objects {
                  uuid
                }
              }
            }
            """
        )
        variables: dict[str, object] = {"user_key": user_key}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return GetFacetUuid.parse_obj(data).facets

    async def get_class(self, class_filter: ClassFilter) -> GetClassClasses:
        query = gql(
            """
            query GetClass($class_filter: ClassFilter!) {
              classes(filter: $class_filter) {
                objects {
                  uuid
                  current {
                    uuid
                    user_key
                    name
                    scope
                    parent {
                      uuid
                      user_key
                      scope
                    }
                  }
                }
              }
            }
            """
        )
        variables: dict[str, object] = {"class_filter": class_filter}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return GetClass.parse_obj(data).classes

    async def create_class(self, input: ClassCreateInput) -> CreateClassClassCreate:
        query = gql(
            """
            mutation CreateClass($input: ClassCreateInput!) {
              class_create(input: $input) {
                uuid
              }
            }
            """
        )
        variables: dict[str, object] = {"input": input}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return CreateClass.parse_obj(data).class_create

    async def update_class(self, input: ClassUpdateInput) -> UpdateClassClassUpdate:
        query = gql(
            """
            mutation UpdateClass($input: ClassUpdateInput!) {
              class_update(input: $input) {
                uuid
              }
            }
            """
        )
        variables: dict[str, object] = {"input": input}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return UpdateClass.parse_obj(data).class_update

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
                    unit_type_uuid
                    org_unit_hierarchy
                    time_planning_uuid
                    parent_uuid
                    addresses {
                      uuid
                      name
                      user_key
                      value
                      address_type {
                        user_key
                        name
                      }
                      visibility {
                        uuid
                      }
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

    async def get_parent_roots(
        self, input: OrganisationUnitFilter
    ) -> GetParentRootsOrgUnits:
        query = gql(
            """
            query GetParentRoots($input: OrganisationUnitFilter!) {
              org_units(filter: $input) {
                objects {
                  uuid
                }
              }
            }
            """
        )
        variables: dict[str, object] = {"input": input}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return GetParentRoots.parse_obj(data).org_units

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
                  uuid
                }
              }
            }
            """
        )
        variables: dict[str, object] = {"cpr": cpr}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return GetPerson.parse_obj(data).employees

    async def get_person_timeline(
        self, filter: Union[Optional[EmployeeFilter], UnsetType] = UNSET
    ) -> GetPersonTimelineEmployees:
        query = gql(
            """
            query GetPersonTimeline($filter: EmployeeFilter) {
              employees(filter: $filter) {
                objects {
                  uuid
                  validities {
                    addresses {
                      address_type {
                        user_key
                        scope
                      }
                      name
                    }
                    cpr_number
                    given_name
                    surname
                    validity {
                      from
                      to
                    }
                  }
                }
              }
            }
            """
        )
        variables: dict[str, object] = {"filter": filter}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return GetPersonTimeline.parse_obj(data).employees

    async def create_person(
        self, input: EmployeeCreateInput
    ) -> CreatePersonEmployeeCreate:
        query = gql(
            """
            mutation CreatePerson($input: EmployeeCreateInput!) {
              employee_create(input: $input) {
                uuid
              }
            }
            """
        )
        variables: dict[str, object] = {"input": input}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return CreatePerson.parse_obj(data).employee_create

    async def update_person(
        self, input: EmployeeUpdateInput
    ) -> UpdatePersonEmployeeUpdate:
        query = gql(
            """
            mutation UpdatePerson($input: EmployeeUpdateInput!) {
              employee_update(input: $input) {
                uuid
              }
            }
            """
        )
        variables: dict[str, object] = {"input": input}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return UpdatePerson.parse_obj(data).employee_update

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

    async def get_engagements(
        self, input: EngagementFilter
    ) -> GetEngagementsEngagements:
        query = gql(
            """
            query GetEngagements($input: EngagementFilter!) {
              engagements(filter: $input) {
                objects {
                  uuid
                  validities {
                    user_key
                    validity {
                      from
                      to
                    }
                    person {
                      cpr_number
                    }
                  }
                }
              }
            }
            """
        )
        variables: dict[str, object] = {"input": input}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return GetEngagements.parse_obj(data).engagements

    async def get_engagement_timeline(
        self,
        person: UUID,
        user_key: str,
        from_date: Union[Optional[datetime], UnsetType] = UNSET,
        to_date: Union[Optional[datetime], UnsetType] = UNSET,
    ) -> GetEngagementTimelineEngagements:
        query = gql(
            """
            query GetEngagementTimeline($person: UUID!, $user_key: String!, $from_date: DateTime, $to_date: DateTime) {
              engagements(
                filter: {employee: {uuids: [$person]}, user_keys: [$user_key], from_date: $from_date, to_date: $to_date}
              ) {
                objects {
                  uuid
                  validities {
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
                    org_unit(filter: {from_date: $from_date, to_date: $to_date}) {
                      uuid
                    }
                    engagement_type {
                      uuid
                      user_key
                      name
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
            "person": person,
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

    async def get_leave(self, filter: LeaveFilter) -> GetLeaveLeaves:
        query = gql(
            """
            query GetLeave($filter: LeaveFilter!) {
              leaves(filter: $filter) {
                objects {
                  uuid
                  validities {
                    user_key
                    person {
                      uuid
                    }
                    engagement {
                      uuid
                    }
                    leave_type {
                      uuid
                    }
                    validity {
                      from
                      to
                    }
                  }
                }
              }
            }
            """
        )
        variables: dict[str, object] = {"filter": filter}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return GetLeave.parse_obj(data).leaves

    async def create_leave(self, input: LeaveCreateInput) -> CreateLeaveLeaveCreate:
        query = gql(
            """
            mutation CreateLeave($input: LeaveCreateInput!) {
              leave_create(input: $input) {
                uuid
              }
            }
            """
        )
        variables: dict[str, object] = {"input": input}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return CreateLeave.parse_obj(data).leave_create

    async def update_leave(self, input: LeaveUpdateInput) -> UpdateLeaveLeaveUpdate:
        query = gql(
            """
            mutation UpdateLeave($input: LeaveUpdateInput!) {
              leave_update(input: $input) {
                uuid
              }
            }
            """
        )
        variables: dict[str, object] = {"input": input}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return UpdateLeave.parse_obj(data).leave_update

    async def terminate_leave(
        self, input: LeaveTerminateInput
    ) -> TerminateLeaveLeaveTerminate:
        query = gql(
            """
            mutation TerminateLeave($input: LeaveTerminateInput!) {
              leave_terminate(input: $input) {
                uuid
              }
            }
            """
        )
        variables: dict[str, object] = {"input": input}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return TerminateLeave.parse_obj(data).leave_terminate

    async def get_related_units(
        self, filter: RelatedUnitFilter
    ) -> GetRelatedUnitsRelatedUnits:
        query = gql(
            """
            query GetRelatedUnits($filter: RelatedUnitFilter!) {
              related_units(filter: $filter) {
                objects {
                  validities {
                    uuid
                    validity {
                      from
                      to
                    }
                    org_units {
                      uuid
                    }
                  }
                }
              }
            }
            """
        )
        variables: dict[str, object] = {"filter": filter}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return GetRelatedUnits.parse_obj(data).related_units

    async def send_event(self, input: EventSendInput) -> bool:
        query = gql(
            """
            mutation SendEvent($input: EventSendInput!) {
              event_send(input: $input)
            }
            """
        )
        variables: dict[str, object] = {"input": input}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return SendEvent.parse_obj(data).event_send

    async def _testing__update_related_units(
        self, input: RelatedUnitsUpdateInput
    ) -> TestingUpdateRelatedUnitsRelatedUnitsUpdate:
        query = gql(
            """
            mutation _Testing_UpdateRelatedUnits($input: RelatedUnitsUpdateInput!) {
              related_units_update(input: $input) {
                uuid
              }
            }
            """
        )
        variables: dict[str, object] = {"input": input}
        response = await self.execute(query=query, variables=variables)
        data = self.get_data(response)
        return TestingUpdateRelatedUnits.parse_obj(data).related_units_update

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
