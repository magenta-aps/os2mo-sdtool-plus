from uuid import UUID

from .base_model import BaseModel


class DeleteOrgFunction(BaseModel):
    engagement_delete: "DeleteOrgFunctionEngagementDelete"


class DeleteOrgFunctionEngagementDelete(BaseModel):
    uuid: UUID


DeleteOrgFunction.update_forward_refs()
DeleteOrgFunctionEngagementDelete.update_forward_refs()
