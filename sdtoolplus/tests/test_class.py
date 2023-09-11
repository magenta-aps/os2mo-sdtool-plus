# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import pytest

from ..mo_class import MOClassMap
from ..mo_class import MOOrgUnitLevelMap
from ..mo_class import MOOrgUnitTypeMap
from .conftest import _MockGraphQLSessionGetClassesInFacet


class _MOClassMapImpl(MOClassMap):
    """Dummy implementation of a `MOClassMap` subclass, used for testing the behavior
    of properly-defined subclasses."""

    @property
    def facet_user_key(self) -> str:
        return "facet_user_key"


class TestMOClassMap:
    def test_parses_mo_classes(
        self,
        mock_graphql_session_get_classes_in_facet: _MockGraphQLSessionGetClassesInFacet,
    ) -> None:
        instance: _MOClassMapImpl = _MOClassMapImpl(
            mock_graphql_session_get_classes_in_facet
        )
        assert [(cls.name, cls.user_key) for cls in instance.classes] == [
            (name, name) for name in _MockGraphQLSessionGetClassesInFacet.class_names
        ]

    def test_getitem(
        self,
        mock_graphql_session_get_classes_in_facet: _MockGraphQLSessionGetClassesInFacet,
    ) -> None:
        instance: _MOClassMapImpl = _MOClassMapImpl(
            mock_graphql_session_get_classes_in_facet
        )
        with pytest.raises(KeyError):
            instance["unknown key"]

    def test_facet_user_key_property(
        self,
        mock_graphql_session_get_classes_in_facet: _MockGraphQLSessionGetClassesInFacet,
    ) -> None:
        with pytest.raises(NotImplementedError):
            MOClassMap(mock_graphql_session_get_classes_in_facet)


class TestMOOrgUnitLevelMap:
    def test_facet_user_key_property(
        self,
        mock_graphql_session_get_classes_in_facet: _MockGraphQLSessionGetClassesInFacet,
    ) -> None:
        instance: MOOrgUnitLevelMap = MOOrgUnitLevelMap(
            mock_graphql_session_get_classes_in_facet
        )
        assert instance.facet_user_key == "org_unit_level"


class TestMOOrgUnitTypeMap:
    def test_facet_user_key_property(
        self,
        mock_graphql_session_get_classes_in_facet: _MockGraphQLSessionGetClassesInFacet,
    ) -> None:
        instance: MOOrgUnitTypeMap = MOOrgUnitTypeMap(
            mock_graphql_session_get_classes_in_facet
        )
        assert instance.facet_user_key == "org_unit_type"
