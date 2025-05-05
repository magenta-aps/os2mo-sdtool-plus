from uuid import UUID

from .base_model import BaseModel


class TestingCreateEngagement(BaseModel):
    engagement_create: "TestingCreateEngagementEngagementCreate"


class TestingCreateEngagementEngagementCreate(BaseModel):
    uuid: UUID


TestingCreateEngagement.update_forward_refs()
TestingCreateEngagementEngagementCreate.update_forward_refs()
