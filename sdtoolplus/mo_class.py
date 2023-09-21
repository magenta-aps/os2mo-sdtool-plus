# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from uuid import UUID

import pydantic
from gql import gql


class MOClass(pydantic.BaseModel):
    uuid: UUID
    user_key: str
    name: str


class MOClassMap:
    """Retrieve the MO classes in a given facet, and make those MO classes available for
    lookup by their name or `user_key`  by using a `MOClassMap` for dictionary-style
    lookups.

    `MOClassMap` is intended to be subclassed, each subclass handling a specific MO
    facet. This is achieved by defining the `facet_user_key` property on each subclass.
    See the `MOOrgUnitLevelMap` and `MOOrgUnitTypeMap` classes.
    """

    def __init__(self, session) -> None:
        self.session = session
        self.classes = self._get_classes_in_facet(self.facet_user_key)

    @property
    def facet_user_key(self) -> str:
        """Return the `user_key` of the facet whose classes we are retrieving"""
        raise NotImplementedError("must be implemented by subclass")

    def _get_classes_in_facet(self, facet_user_key: str) -> list[MOClass]:
        """Retrieve the classes in the MO facet given by `facet_user_key`"""
        doc = self.session.execute(
            gql(
                """
                query GetClassesInFacet($facet_user_key: String!) {
                    classes(facet_user_keys: [$facet_user_key]) {
                        uuid
                        user_key
                        name
                    }
                }
                """
            ),
            {"facet_user_key": facet_user_key},
        )
        return pydantic.parse_obj_as(list[MOClass], doc["classes"])

    def __getitem__(self, item: str) -> MOClass:
        """Support dictionary-style item lookups on class name or `user_key`.
        E.g.:
            >>> org_unit_type_map = MOOrgUnitTypeMap(session)
            >>> mo_org_unit_type_map["Afdeling"]
            MOClass(uuid=UUID('9d2ac723-d5e5-4e7f-9c7f-b207bd223bc2'), user_key='Afdeling', name='Afdeling')
        """
        for cls in self.classes:
            if item in (cls.name, cls.user_key):
                return cls
        raise KeyError(item)


class MOOrgUnitLevelMap(MOClassMap):
    """Class map of the classes in the MO facet `org_unit_level`"""

    @property
    def facet_user_key(self) -> str:
        return "org_unit_level"


class MOOrgUnitTypeMap(MOClassMap):
    """Class map of the classes in the MO facet `org_unit_type`"""

    @property
    def facet_user_key(self) -> str:
        return "org_unit_type"
