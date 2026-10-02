from uuid import UUID

from .base_model import BaseModel


class TestingCreateRootOrg(BaseModel):
    org_create: "TestingCreateRootOrgOrgCreate"


class TestingCreateRootOrgOrgCreate(BaseModel):
    uuid: UUID


TestingCreateRootOrg.update_forward_refs()
TestingCreateRootOrgOrgCreate.update_forward_refs()
