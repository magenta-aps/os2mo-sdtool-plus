from uuid import UUID

from .base_model import BaseModel


class CreateLeave(BaseModel):
    leave_create: "CreateLeaveLeaveCreate"


class CreateLeaveLeaveCreate(BaseModel):
    uuid: UUID


CreateLeave.update_forward_refs()
CreateLeaveLeaveCreate.update_forward_refs()
