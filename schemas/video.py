from typing import List
from datetime import date, timedelta
from pydantic import BaseModel, RootModel


class Video(BaseModel):
    camera: str
    type: str
    importance_level: int
    recorded_at: str
    record_length: str
    hash: str


class VideoList(RootModel[List[Video]]):
    pass


