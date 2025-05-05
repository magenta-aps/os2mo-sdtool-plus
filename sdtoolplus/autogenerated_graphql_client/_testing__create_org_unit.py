from uuid import UUID

from .base_model import BaseModel


class TestingCreateOrgUnit(BaseModel):
    org_unit_create: "TestingCreateOrgUnitOrgUnitCreate"


class TestingCreateOrgUnitOrgUnitCreate(BaseModel):
    uuid: UUID


TestingCreateOrgUnit.update_forward_refs()
TestingCreateOrgUnitOrgUnitCreate.update_forward_refs()
