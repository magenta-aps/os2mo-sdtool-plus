import uuid

from gql import gql

from ..mo_org_unit_importer import MOOrgTreeImport


class _MockGraphQLSession:
    _root_org_uuid = str(uuid.uuid4())

    def __init__(self) -> None:
        self._response = None

    def execute(self, query: gql) -> dict:
        return self._response


class _MockGraphQLSessionGetOrgUUID(_MockGraphQLSession):
    def __init__(self) -> None:
        super().__init__()
        self.expected_org_uuid = self._root_org_uuid
        self._response = {"org": {"uuid": self.expected_org_uuid}}


class _MockGraphQLSessionGetOrgUnits(_MockGraphQLSessionGetOrgUUID):
    def __init__(self) -> None:
        super().__init__()
        self.expected_org_units = [{"objects": self.get_org_units()}]
        self._response = {"org_units": self.expected_org_units}

    def execute(self, query: gql) -> dict:
        name = query.to_dict()['definitions'][0]['name']['value']
        if name == "GetOrgUUID":
            return {"org": {"uuid": self.expected_org_uuid}}
        else:
            return self._response

    def get_org_units(self) -> list[dict]:
        # Mock children of root org
        self.parent_uuid = str(uuid.uuid4())
        org_units = [
            {"uuid": self.parent_uuid, "parent_uuid": self.expected_org_uuid}
            for _ in range(2)
        ]
        # Mock grandchildren (== children of parent org units)
        org_units.extend(
            [
                {"uuid": str(uuid.uuid4()), "parent_uuid": self.parent_uuid}
                for _ in range(2)
            ]
        )
        return org_units


class TestMOOrgTreeImport:
    def test_get_org_uuid(self):
        session = _MockGraphQLSessionGetOrgUUID()
        instance = MOOrgTreeImport(session)
        assert instance.get_org_uuid() == session.expected_org_uuid

    def test_get_org_units(self):
        session = _MockGraphQLSessionGetOrgUnits()
        instance = MOOrgTreeImport(session)
        assert len(instance.get_org_units()) == len(session.expected_org_units)

    def test_build_trees(self):
        session = _MockGraphQLSessionGetOrgUUID()
        instance = MOOrgTreeImport(session)
        source = _MockGraphQLSessionGetOrgUnits()
        trees = instance._build_trees(source.get_org_units())
        assert len(trees) == 2
        for tree in trees:
            assert tree["uuid"] == source.parent_uuid
            assert tree["parent_uuid"] == session.expected_org_uuid
            for child in tree["children"]:
                assert child["uuid"] not in (session.expected_org_uuid, source.parent_uuid)
                assert child["parent_uuid"] == tree["uuid"]

    def test_as_anytree_root(self):
        session = _MockGraphQLSessionGetOrgUnits()
        instance = MOOrgTreeImport(session)
        anytree_root = instance.as_anytree_root()
        assert anytree_root.is_root
