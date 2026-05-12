from typing import List, Optional

from ..types import CPRNumber
from .base_model import BaseModel


class GetPersonCpr(BaseModel):
    employees: "GetPersonCprEmployees"


class GetPersonCprEmployees(BaseModel):
    objects: List["GetPersonCprEmployeesObjects"]


class GetPersonCprEmployeesObjects(BaseModel):
    validities: List["GetPersonCprEmployeesObjectsValidities"]


class GetPersonCprEmployeesObjectsValidities(BaseModel):
    cpr_number: Optional[CPRNumber]


GetPersonCpr.update_forward_refs()
GetPersonCprEmployees.update_forward_refs()
GetPersonCprEmployeesObjects.update_forward_refs()
GetPersonCprEmployeesObjectsValidities.update_forward_refs()
