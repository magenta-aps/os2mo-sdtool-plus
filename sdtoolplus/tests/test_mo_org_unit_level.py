# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import pytest

from ..mo_org_unit_level import MOOrgUnitLevelMap
from .conftest import _MockGraphQLSessionGetClassesInFacet


class TestMOOrgUnitLevelMap:
    def test_parses_mo_org_unit_levels(
        self,
        mock_graphql_session_get_classes_in_facet: _MockGraphQLSessionGetClassesInFacet,
    ) -> None:
        instance: MOOrgUnitLevelMap = MOOrgUnitLevelMap(
            mock_graphql_session_get_classes_in_facet
        )
        assert [(cls.name, cls.user_key) for cls in instance.classes] == [
            (name, name) for name in _MockGraphQLSessionGetClassesInFacet.class_names
        ]

    def test_getitem(
        self,
        mock_graphql_session_get_classes_in_facet: _MockGraphQLSessionGetClassesInFacet,
    ) -> None:
        instance: MOOrgUnitLevelMap = MOOrgUnitLevelMap(
            mock_graphql_session_get_classes_in_facet
        )
        with pytest.raises(KeyError):
            instance["unknown key"]
