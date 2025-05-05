from uuid import UUID

from .base_model import BaseModel


class TerminateEngagement(BaseModel):
    engagement_terminate: "TerminateEngagementEngagementTerminate"


class TerminateEngagementEngagementTerminate(BaseModel):
    uuid: UUID


TerminateEngagement.update_forward_refs()
TerminateEngagementEngagementTerminate.update_forward_refs()
