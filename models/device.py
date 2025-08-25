from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime, ForeignKey, select, or_
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_utils import ChoiceType
from uuid import uuid4
from db.connector import Base
from constants.models.video import VIDEO_TYPES, VIDEO_TYPE_INTRUDER


class Camera(Base):
    __tablename__ = "cameras"
    
    id = Column(Integer, primary_key=True, index=True)
    device_name = Column(String, unique=True)
    activated_at = Column(DateTime)
    software_version = Column(Numeric, default=0)
    active = Column(Boolean, default=True)
    
    # relacja do connectora
    camera_groups = relationship("CameraGroupConnector", back_populates="camera")
    videos = relationship("Video", back_populates="camera")


class CameraGroupConnector(Base):
    __tablename__ = "camera_group_connectors"
    
    id = Column(Integer, primary_key=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"))
    group_id = Column(Integer, ForeignKey("groups.id"))
    
    # relacje do encji
    camera = relationship("Camera", back_populates="camera_groups")
    group = relationship("Group", back_populates="camera_groups")
