from typing import List

from .base_model import BaseModel


class RerunEvents(BaseModel):
    event_rerun: List["RerunEventsEventRerun"]


class RerunEventsEventRerun(BaseModel):
    subject: str
    priority: int
    silenced: bool
    listener: "RerunEventsEventRerunListener"


class RerunEventsEventRerunListener(BaseModel):
    user_key: str


RerunEvents.update_forward_refs()
RerunEventsEventRerun.update_forward_refs()
RerunEventsEventRerunListener.update_forward_refs()
