from typing import List
from datetime import datetime
from pydantic import BaseModel, RootModel


class Video(BaseModel):
    camera: str
    type: str
    importance_level: int
    recorded_at: str
    record_length: str
    hash: str
    url: str


class VideoList(RootModel[List[Video]]):
    pass


# ,camera: Camera, file_path: str, recorded_at: datetime, record_length: float
class VideoSchema(BaseModel):
    file_path: str
    recorded_at: str
    record_length: int
