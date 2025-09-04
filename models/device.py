from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime, ForeignKey, select
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from db.connector import Base


class Camera(Base):
    __tablename__ = "cameras"
    
    id = Column(Integer, primary_key=True, index=True)
    device_name = Column(String, unique=True)
    activated_at = Column(DateTime)
    software_version = Column(Numeric, default=0)
    active = Column(Boolean, default=True)
    
    camera_groups = relationship("CameraGroupConnector", back_populates="camera")
    videos = relationship("Video", back_populates="camera")


class CameraGroupConnector(Base):
    __tablename__ = "camera_group_connectors"
    
    id = Column(Integer, primary_key=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"))
    group_id = Column(Integer, ForeignKey("groups.id"))
    
    camera = relationship("Camera", back_populates="camera_groups")
    group = relationship("Group", back_populates="camera_groups")


    ############################################
    # works like serchable property in django
    @hybrid_property
    def camera_device_name(self):
        return self.camera.device_name if self.camera else None

    @camera_device_name.expression
    def camera_device_name(cls):
        return select(Camera.device_name).where(Camera.id == cls.camera_id).scalar_subquery() 
    ############################################
