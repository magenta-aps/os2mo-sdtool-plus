# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from datetime import datetime

from gql import gql
from more_itertools import one
from raclients.graph.client import PersistentGraphQLClient

from sdtoolplus.autogenerated_graphql_client import AddressCreateInput
from sdtoolplus.autogenerated_graphql_client import AddressUpdateInput
from sdtoolplus.autogenerated_graphql_client import RAValidityInput
from sdtoolplus.config import SDToolPlusSettings
from sdtoolplus.depends import GraphQLClient
from sdtoolplus.mo_org_unit_importer import Address
from sdtoolplus.mo_org_unit_importer import AddressTypeUUID
from sdtoolplus.mo_org_unit_importer import OrgUnitNode

GET_ENGAGEMENTS = gql(
    """
    query GetOrgUnitEngagements($uuid: UUID!, $from_date: DateTime!) {
      org_units(filter: {uuids: [$uuid]}) {
        objects {
          objects {
            engagements(filter: {from_date: $from_date, to_date: null}) {
              uuid
              validity {
                from
                to
              }
            }
          }
        }
      }
    }
    """
)


def get_graphql_client(settings: SDToolPlusSettings) -> PersistentGraphQLClient:
    return PersistentGraphQLClient(
        url=f"{settings.mora_base}/graphql/v7",
        client_id=settings.client_id,
        client_secret=settings.client_secret.get_secret_value(),
        auth_realm=settings.auth_realm,
        auth_server=settings.auth_server,  # type: ignore
        sync=True,
        httpx_client_kwargs={"timeout": None},
        fetch_schema_from_transport=True,
    )


async def get_address_type_uuid(
    gql_client: GraphQLClient, address_type: str
) -> AddressTypeUUID:
    addr_types = await gql_client.address_types()
    current = one(addr_types.objects).current

    assert current is not None

    addr_classes = current.classes
    addr_type_uuid = one(
        addr_class.uuid
        for addr_class in addr_classes
        if addr_class.user_key == address_type
    )
    return addr_type_uuid


async def add_address(
    gql_client: GraphQLClient,
    org_unit_node: OrgUnitNode,
    addr: Address,
    from_date: datetime,
    to_date: datetime | None,
) -> Address:
    created_addr = await gql_client.create_address(
        AddressCreateInput(
            org_unit=org_unit_node.uuid,
            value=addr.value,
            address_type=addr.address_type.uuid,
            validity=RAValidityInput(
                from_=from_date,
                to=to_date,
            ),
        )
    )

    created_addr_current = created_addr.current
    assert created_addr_current is not None

    return Address(
        uuid=created_addr_current.uuid,
        value=addr.value,
        address_type=addr.address_type,
    )


async def update_address(
    gql_client: GraphQLClient,
    addr: Address,
    from_date: datetime,
    to_date: datetime | None,
):
    await gql_client.update_address(
        AddressUpdateInput(
            uuid=addr.uuid,
            address_type=addr.address_type.uuid,
            value=addr.value,
            validity=RAValidityInput(
                from_=from_date,
                to=to_date,
            ),
        )
    )
