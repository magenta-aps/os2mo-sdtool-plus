# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
import pytest

from ..mo_class import MOClass
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
        mock_class_data: list[dict] = _MockGraphQLSessionGetClassesInFacet.class_data
        expected_class_0: MOClass = MOClass(
            uuid=mock_class_data[0]["uuid"],
            name=mock_class_data[0]["name"],
            user_key=mock_class_data[0]["user_key"],
        )
        expected_class_1: MOClass = MOClass(
            uuid=mock_class_data[1]["uuid"],
            name=mock_class_data[1]["name"],
            user_key=mock_class_data[1]["user_key"],
        )
        instance: _MOClassMapImpl = _MOClassMapImpl(
            mock_graphql_session_get_classes_in_facet
        )
        assert len(instance.classes) == len(mock_class_data)
        assert instance.classes[0] == expected_class_0
        assert instance.classes[1] == expected_class_1

    def test_getitem_returns_mo_class(
        self,
        mock_graphql_session_get_classes_in_facet: _MockGraphQLSessionGetClassesInFacet,
    ):
        instance: _MOClassMapImpl = _MOClassMapImpl(
            mock_graphql_session_get_classes_in_facet
        )
        assert instance["N0"] == MOClass(
            uuid=_MockGraphQLSessionGetClassesInFacet.class_data[0]["uuid"],
            name=_MockGraphQLSessionGetClassesInFacet.class_data[0]["name"],
            user_key=_MockGraphQLSessionGetClassesInFacet.class_data[0]["user_key"],
        )

    def test_getitem_raises_keyerror_on_unknown_key(
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
