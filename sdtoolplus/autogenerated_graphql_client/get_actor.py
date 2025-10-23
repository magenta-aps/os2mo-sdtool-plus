from uuid import UUID

from .base_model import BaseModel


class GetActor(BaseModel):
    me: "GetActorMe"


class GetActorMe(BaseModel):
    actor: "GetActorMeActor"


class GetActorMeActor(BaseModel):
    uuid: UUID


GetActor.update_forward_refs()
GetActorMe.update_forward_refs()
GetActorMeActor.update_forward_refs()
