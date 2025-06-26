from uuid import UUID

from .base_model import BaseModel


class UpdateAssociation(BaseModel):
    association_update: "UpdateAssociationAssociationUpdate"


class UpdateAssociationAssociationUpdate(BaseModel):
    uuid: UUID


UpdateAssociation.update_forward_refs()
UpdateAssociationAssociationUpdate.update_forward_refs()
