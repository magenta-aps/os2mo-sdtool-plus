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
    def __init__(self, session) -> None:
        self.session = session
        self.classes = self._get_classes_in_facet(self.facet_user_key)

    @property
    def facet_user_key(self) -> str:
        raise NotImplementedError("must be implemented by subclass")

    def _get_classes_in_facet(self, facet_user_key: str) -> list[MOClass]:
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
        for cls in self.classes:
            if item in (cls.name, cls.user_key):
                return cls
        raise KeyError(item)


class MOOrgUnitLevelMap(MOClassMap):
    @property
    def facet_user_key(self) -> str:
        return "org_unit_level"


class MOOrgUnitTypeMap(MOClassMap):
    @property
    def facet_user_key(self) -> str:
        return "org_unit_type"
