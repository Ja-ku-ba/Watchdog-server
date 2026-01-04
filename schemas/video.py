from typing import List
from pydantic import BaseModel

from schemas.device import Device


class Video(BaseModel):
    camera: str
    type: str
    importance_level: int
    recorded_at: str
    record_length: str
    hash: str
    url: str


class VideoList(BaseModel):
    configured_devices: List[Device]
    videos: List[Video]


class VideoSchema(BaseModel):
    file_path: str
    recorded_at: str
    record_length: int
