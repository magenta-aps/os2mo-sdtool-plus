from typing import Any, List, Optional

from .base_model import BaseModel


class GetPersonCPR(BaseModel):
    employees: "GetPersonCPREmployees"


class GetPersonCPREmployees(BaseModel):
    objects: List["GetPersonCPREmployeesObjects"]


class GetPersonCPREmployeesObjects(BaseModel):
    validities: List["GetPersonCPREmployeesObjectsValidities"]


class GetPersonCPREmployeesObjectsValidities(BaseModel):
    cpr_number: Optional[Any]


GetPersonCPR.update_forward_refs()
GetPersonCPREmployees.update_forward_refs()
GetPersonCPREmployeesObjects.update_forward_refs()
GetPersonCPREmployeesObjectsValidities.update_forward_refs()
