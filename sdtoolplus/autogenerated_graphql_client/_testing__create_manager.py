from uuid import UUID

from .base_model import BaseModel


class TestingCreateManager(BaseModel):
    manager_create: "TestingCreateManagerManagerCreate"


class TestingCreateManagerManagerCreate(BaseModel):
    uuid: UUID


TestingCreateManager.update_forward_refs()
TestingCreateManagerManagerCreate.update_forward_refs()
