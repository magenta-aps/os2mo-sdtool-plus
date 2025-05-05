from uuid import UUID

from .base_model import BaseModel


class TestingUpdateRelatedUnits(BaseModel):
    related_units_update: "TestingUpdateRelatedUnitsRelatedUnitsUpdate"


class TestingUpdateRelatedUnitsRelatedUnitsUpdate(BaseModel):
    uuid: UUID


TestingUpdateRelatedUnits.update_forward_refs()
TestingUpdateRelatedUnitsRelatedUnitsUpdate.update_forward_refs()
