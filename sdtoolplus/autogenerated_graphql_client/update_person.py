from uuid import UUID

from .base_model import BaseModel


class UpdatePerson(BaseModel):
    employee_update: "UpdatePersonEmployeeUpdate"


class UpdatePersonEmployeeUpdate(BaseModel):
    uuid: UUID


UpdatePerson.update_forward_refs()
UpdatePersonEmployeeUpdate.update_forward_refs()
