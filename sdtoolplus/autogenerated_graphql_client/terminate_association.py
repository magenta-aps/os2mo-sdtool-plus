from uuid import UUID

from .base_model import BaseModel


class TerminateAssociation(BaseModel):
    association_terminate: "TerminateAssociationAssociationTerminate"


class TerminateAssociationAssociationTerminate(BaseModel):
    uuid: UUID


TerminateAssociation.update_forward_refs()
TerminateAssociationAssociationTerminate.update_forward_refs()
