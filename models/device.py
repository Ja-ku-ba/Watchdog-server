from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime, ForeignKey, select
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.asyncio import AsyncSession

from db.connector import Base


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    device_name = Column(String, unique=True)
    activated_at = Column(DateTime)
    software_version = Column(Numeric, default=0)
    active = Column(Boolean, default=True)
    device_ip = Column(String, unique=True)
    camera_uid = Column(String, unique=True)
    
    camera_groups = relationship("CameraGroupConnector", back_populates="camera")
    videos = relationship("Video", back_populates="camera")
    files_analyzes = relationship("FilesAnalyze", back_populates="camera")

    @classmethod
    async def get_device_by_uidd(cls, session: AsyncSession, uid: str):
        result = await session.execute(
            select(cls).filter(cls.camera_uid.like(uid))
        )
        camera_query = result.scalars().all()
        
        if len(camera_query) > 1 or not camera_query:
            return None
            
        camera = camera_query[0]
        return camera


class CameraGroupConnector(Base):
    __tablename__ = "camera_group_connectors"
    
    id = Column(Integer, primary_key=True)

    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)    
    camera = relationship("Camera", back_populates="camera_groups")

    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    group = relationship("Group", back_populates="cameras_group_connector")

    @hybrid_property
    # serchable property
    def camera_device_name(self):
        return self.camera.device_name

    @camera_device_name.expression
    def camera_device_name(cls):
        return select(Camera.device_name).where(Camera.id == cls.camera_id).scalar_subquery()
