# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from uuid import UUID

from more_itertools import one

from sdtoolplus.depends import GraphQLClient


async def get_address_type_uuid(gql_client: GraphQLClient, address_type: str) -> UUID:
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
