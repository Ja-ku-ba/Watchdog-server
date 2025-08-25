from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Interval
from sqlalchemy.orm import relationship
from sqlalchemy_utils import ChoiceType

from db.connector import Base
from constants.models.video import VIDEO_TYPES, VIDEO_TYPE_INTRUDER


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    recorded_at = Column(DateTime)
    record_length = Column(Interval)
    type = Column(ChoiceType(VIDEO_TYPES, impl=String(255)), default=VIDEO_TYPE_INTRUDER)
    
    file_path = Column(String)
    thumbnial_file_path = Column(String)
    
    hash = Column(String(32), unique=True, nullable=False)
    importance_level = Column(Numeric)

    camera_id = Column(Integer, ForeignKey('cameras.id'))
    camera = relationship("Camera", back_populates="videos")

    @property
    def type_display(self) -> str:
        if self.type is None:
            return ""
        return dict(VIDEO_TYPES).get(self.type, self.type)