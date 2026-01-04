from typing import List
from pydantic import BaseModel


class Device(BaseModel):
    device_ip: str
    device_name: str
