# Generated by ariadne-codegen on 2025-03-10 11:37
# Source: queries.graphql

from uuid import UUID

from .base_model import BaseModel


class TestingCreateEmployee(BaseModel):
    employee_create: "TestingCreateEmployeeEmployeeCreate"


class TestingCreateEmployeeEmployeeCreate(BaseModel):
    uuid: UUID


TestingCreateEmployee.update_forward_refs()
TestingCreateEmployeeEmployeeCreate.update_forward_refs()
