from typing import List

from .base_model import BaseModel


class GetEvents(BaseModel):
    events: "GetEventsEvents"


class GetEventsEvents(BaseModel):
    objects: List["GetEventsEventsObjects"]


class GetEventsEventsObjects(BaseModel):
    subject: str
    priority: int


GetEvents.update_forward_refs()
GetEventsEvents.update_forward_refs()
GetEventsEventsObjects.update_forward_refs()
