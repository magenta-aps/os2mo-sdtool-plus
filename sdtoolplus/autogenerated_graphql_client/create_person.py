from uuid import UUID

from .base_model import BaseModel


class CreatePerson(BaseModel):
    employee_create: "CreatePersonEmployeeCreate"


class CreatePersonEmployeeCreate(BaseModel):
    uuid: UUID


CreatePerson.update_forward_refs()
CreatePersonEmployeeCreate.update_forward_refs()
