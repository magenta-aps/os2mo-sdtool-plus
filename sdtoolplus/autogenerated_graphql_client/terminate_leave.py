from uuid import UUID

from .base_model import BaseModel


class TerminateLeave(BaseModel):
    leave_terminate: "TerminateLeaveLeaveTerminate"


class TerminateLeaveLeaveTerminate(BaseModel):
    uuid: UUID


TerminateLeave.update_forward_refs()
TerminateLeaveLeaveTerminate.update_forward_refs()
