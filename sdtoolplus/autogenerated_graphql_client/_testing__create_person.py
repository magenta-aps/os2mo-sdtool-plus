# Generated by ariadne-codegen on 2025-03-27 10:22
# Source: queries.graphql

from uuid import UUID

from .base_model import BaseModel


class TestingCreatePerson(BaseModel):
    employee_create: "TestingCreatePersonEmployeeCreate"


class TestingCreatePersonEmployeeCreate(BaseModel):
    uuid: UUID


TestingCreatePerson.update_forward_refs()
TestingCreatePersonEmployeeCreate.update_forward_refs()
