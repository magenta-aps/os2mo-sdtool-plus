from uuid import UUID

from .base_model import BaseModel


class TestingUpdateManager(BaseModel):
    manager_update: "TestingUpdateManagerManagerUpdate"


class TestingUpdateManagerManagerUpdate(BaseModel):
    uuid: UUID


TestingUpdateManager.update_forward_refs()
TestingUpdateManagerManagerUpdate.update_forward_refs()
