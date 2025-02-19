# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from unittest.mock import MagicMock
from unittest.mock import patch
from uuid import UUID
from uuid import uuid4

from hypothesis import given
from hypothesis import strategies as st
from pydantic import parse_obj_as

from sdtoolplus.mo_org_unit_importer import Address
from sdtoolplus.mo_org_unit_importer import AddressType
from sdtoolplus.mo_org_unit_importer import MOOrgTreeImport
from sdtoolplus.mo_org_unit_importer import OrgUnit
from sdtoolplus.mo_org_unit_importer import OrgUnitNode
from sdtoolplus.mo_org_unit_importer import OrgUUID
from sdtoolplus.models import AddressTypeUserKey
from .conftest import SharedIdentifier


@st.composite
def flat_org_units(draw, uuids=st.uuids()) -> tuple[OrgUUID, list[OrgUnit]]:
    """Construct an flat `OrgUnit` list, representing a tree consisting of three levels:
    - a single root node
    - one or more child nodes, whose parent is the root node
    - one or more grandchild nodes, whose parent is one of the child nodes above it
    """
    root_org_uuid = draw(uuids)
    root_org_unit = draw(st.builds(OrgUnit, uuid=st.just(root_org_uuid)))
    children = draw(
        st.lists(
            st.builds(OrgUnit, parent_uuid=st.just(root_org_unit.uuid)),
            min_size=1,
        )
    )
    grandchildren = draw(
        st.lists(
            st.builds(OrgUnit, parent_uuid=st.sampled_from([c.uuid for c in children]))
        )
    )
    return root_org_uuid, [root_org_unit] + children + grandchildren


class TestMOOrgTreeImport:
    def test_get_org_uuid(self, mock_graphql_session):
        instance = MOOrgTreeImport(mock_graphql_session)
        assert instance.get_org_uuid() == SharedIdentifier.root_org_uuid
        assert isinstance(instance.get_org_uuid(), OrgUUID)

    def test_get_org_units(self, mock_graphql_session):
        instance = MOOrgTreeImport(mock_graphql_session)
        assert instance.get_org_units() == [
            OrgUnit(
                uuid=n.uuid,
                parent_uuid=n.parent_uuid,
                user_key=n.user_key,
                name=n.name,
                org_unit_level_uuid=n.org_unit_level_uuid,
                addresses=[
                    Address(
                        uuid=UUID("599ce718-5ba9-48f1-958f-17ed39b13d27"),
                        name="Grønnegade 2, 1000 Andeby",
                        address_type=AddressType(
                            user_key=AddressTypeUserKey.POSTAL_ADDR.value,
                            uuid=UUID("7bd066ea-e8e5-42b1-9211-73562da54b9b"),
                        ),
                    )
                ],
            )
            for n in (
                mock_graphql_session.expected_children
                + mock_graphql_session.expected_grandchildren
            )
        ]

    def test_build_trees(self, mock_graphql_session):
        instance = MOOrgTreeImport(mock_graphql_session)
        trees = instance._build_trees(
            parse_obj_as(list[OrgUnit], mock_graphql_session.tree_as_flat_list_of_dicts)
        )
        assert trees == mock_graphql_session.expected_trees

    @given(flat_org_units())
    def test_build_trees_robustness(
        self, flat_org_units: tuple[OrgUUID, list[OrgUnit]]
    ):
        org_uuid, org_units = flat_org_units
        with patch.object(MOOrgTreeImport, "get_org_uuid", return_value=org_uuid):
            instance = MOOrgTreeImport(None)
            instance._build_trees(org_units)

    def test_as_single_tree(self, mock_graphql_session):
        instance = MOOrgTreeImport(mock_graphql_session)
        root_uuid = uuid4()
        root, _ = instance.as_single_tree(root_uuid, "", None)
        assert isinstance(root, OrgUnitNode)
        assert root.children == tuple(mock_graphql_session.expected_trees)
        assert root.is_root
        assert root.uuid == root_uuid
        assert [child.is_leaf for child in root.children]

    def test_as_single_tree_for_subtree(self, mock_graphql_session):
        """
        We test that function 'as_single_tree' is capable of generating af subtree
        of OUs from the units in MO. The feature we are testing is most easily
        explained by an example. Assume the OU tree in MO looks like this:

             A (uuidA)
            / \
          B    C (uuidC)
         / \  / \
        D  E F   G (uuidG)
                / \
               H   I

        Calling the function as 'instance.as_single_tree(root_uuid, "uuidC/uuidG")' should
        return the tree:

                root (root_uuid)
                / \
               H   I
        """

        # Arrange
        unit1 = OrgUnitNode(
            uuid=UUID("10000000-0000-0000-0000-000000000000"),
            user_key="unit1",
            name="unit1",
        )
        OrgUnitNode(
            uuid=UUID("11000000-0000-0000-0000-000000000000"),
            user_key="unit11",
            name="unit11",
            parent=unit1,
        )
        OrgUnitNode(
            uuid=UUID("12000000-0000-0000-0000-000000000000"),
            user_key="unit12",
            name="unit12",
            parent=unit1,
        )

        unit2 = OrgUnitNode(
            uuid=UUID("20000000-0000-0000-0000-000000000000"),
            user_key="unit2",
            name="unit2",
        )
        OrgUnitNode(
            uuid=UUID("21000000-0000-0000-0000-000000000000"),
            user_key="unit21",
            name="unit21",
            parent=unit2,
        )
        unit22 = OrgUnitNode(
            uuid=UUID("22000000-0000-0000-0000-000000000000"),
            user_key="unit22",
            name="unit22",
            parent=unit2,
        )
        unit221 = OrgUnitNode(
            uuid=UUID("22100000-0000-0000-0000-000000000000"),
            user_key="unit221",
            name="unit221",
            parent=unit22,
        )
        unit222 = OrgUnitNode(
            uuid=UUID("22200000-0000-0000-0000-000000000000"),
            user_key="unit222",
            name="unit222",
            parent=unit22,
        )

        instance = MOOrgTreeImport(mock_graphql_session)
        instance._build_trees = MagicMock(return_value=[unit1, unit2])

        # Act
        actual, _ = instance.as_single_tree(
            SharedIdentifier.root_org_uuid,
            "20000000-0000-0000-0000-000000000000/22000000-0000-0000-0000-000000000000",
            None,
        )

        # Assert
        assert actual.uuid == SharedIdentifier.root_org_uuid
        assert actual.name == "<root>"
        assert isinstance(actual, OrgUnitNode)
        assert actual.children == (unit221, unit222)
        assert actual.is_root
        assert actual.uuid == SharedIdentifier.root_org_uuid


class TestOrgUnitNode:
    def test_constructor(self, sd_expected_validity):
        assert OrgUnitNode(
            uuid=uuid4(),
            parent_uuid=uuid4(),
            user_key="dep1",
            parent=None,
            name="Department 1",
            org_unit_level_uuid=uuid4(),
            addresses=[
                Address(
                    name="Hovedgaden 1, 1000 Andeby",
                    address_type=AddressType(
                        user_key=AddressTypeUserKey.POSTAL_ADDR.value
                    ),
                ),
                Address(
                    name="123456789",
                    address_type=AddressType(
                        user_key=AddressTypeUserKey.PNUMBER_ADDR.value
                    ),
                ),
            ],
            validity=sd_expected_validity,
        )

    def test_from_org_unit_for_addresses(self):
        # Arrange
        org_unit_dict: dict = {
            "uuid": "10000000-0000-0000-0000-000000000000",
            "parent_uuid": "00000000-0000-0000-0000-000000000000",
            "user_key": "user_key",
            "name": "name",
            "org_unit_level_uuid": "2bf13894-b60a-4769-bad6-39d41d9242aa",
            "addresses": [
                {
                    "name": "1004130546",
                    "uuid": "393e30c5-114f-41df-8497-dc2ed0a339a7",
                    "address_type": {
                        "user_key": "Pnummer",
                        "uuid": "b79bd813-a3cb-46a5-b890-e30227c94af8",
                    },
                },
                {
                    "name": "Grønnegade 2, 1000 Andeby",
                    "uuid": "599ce718-5ba9-48f1-958f-17ed39b13d27",
                    "address_type": {
                        "user_key": "AddressMailUnit",
                        "uuid": "7bd066ea-e8e5-42b1-9211-73562da54b9b",
                    },
                },
            ],
        }

        org_unit = parse_obj_as(OrgUnit, org_unit_dict)

        # Act
        org_unit_node = OrgUnitNode.from_org_unit(org_unit)

        # Assert
        addr1, addr2 = org_unit_node.addresses
        assert addr1.uuid == UUID("393e30c5-114f-41df-8497-dc2ed0a339a7")
        assert addr1.name == "1004130546"
        assert addr1.address_type.user_key == AddressTypeUserKey.PNUMBER_ADDR.value

        assert addr2.uuid == UUID("599ce718-5ba9-48f1-958f-17ed39b13d27")
        assert addr2.name == "Grønnegade 2, 1000 Andeby"
        assert addr2.address_type.user_key == AddressTypeUserKey.POSTAL_ADDR.value
