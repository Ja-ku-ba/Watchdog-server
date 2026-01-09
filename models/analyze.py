from uuid import uuid4

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, select
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession

from db.connector import Base


class FilesAnalyze(Base):
    __tablename__ = "files_analyze"

    id = Column(Integer, primary_key=True, index=True)
    recorded_at = Column(DateTime)
    reported_at = Column(DateTime)
    file_path = Column(String)
    
    deleted = Column(Boolean, nullable=False, default=False)
    analyzed = Column(Boolean, nullable=False, default=False)
    reported = Column(Boolean, nullable=False, default=False)

    camera_id = Column(Integer, ForeignKey('cameras.id'), nullable=False)
    camera = relationship("Camera", back_populates="files_analyzes")


class FacesFromUser(Base):
    __tablename__ = "faces_from_users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    name_hash = Column(String, nullable=False)

    created_at = Column(DateTime)
    file_path = Column(String, nullable=False)
    hash = Column(String(36), unique=True, nullable=False)

    deleted = Column(Boolean, nullable=False, default=False)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="faces_from_user")

    async def generate_hash(self, session: AsyncSession):
        while True:
            new_hash = str(uuid4())[-32:]
            result = await session.execute(
                select(FacesFromUser).filter(FacesFromUser.hash == new_hash)
            )
            existing_face = result.scalars().first()
            
            if not existing_face:
                self.hash = new_hash
                break
