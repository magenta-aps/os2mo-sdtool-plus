# Generated by ariadne-codegen on 2025-03-27 10:22
# Source: queries.graphql

from uuid import UUID

from .base_model import BaseModel


class TerminateLeave(BaseModel):
    leave_terminate: "TerminateLeaveLeaveTerminate"


class TerminateLeaveLeaveTerminate(BaseModel):
    uuid: UUID


TerminateLeave.update_forward_refs()
TerminateLeaveLeaveTerminate.update_forward_refs()
