from uuid import UUID

from .base_model import BaseModel


class UpdateRelatedUnits(BaseModel):
    related_units_update: "UpdateRelatedUnitsRelatedUnitsUpdate"


class UpdateRelatedUnitsRelatedUnitsUpdate(BaseModel):
    uuid: UUID


UpdateRelatedUnits.update_forward_refs()
UpdateRelatedUnitsRelatedUnitsUpdate.update_forward_refs()
