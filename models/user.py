from sqlalchemy import select, or_
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from constants.models.video import VIDEO_TYPE_FRIEND, VIDEO_TYPE_INTRUDER, VIDEO_TYPE_UNKNOWN
from db.connector import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True)
    username = Column(String, unique=True)
    password = Column(String)

    active = Column(Boolean, default=True)
    super_user = Column(Boolean, default=False)

    activated_at = Column(DateTime)

    token = Column(String, unique=True)

    notification_token = Column(String, unique=True)
    old_notification_token = Column(String, unique=True)
    

    user_group_connectors = relationship("UserGroupConnector", back_populates="user")
    faces_from_user = relationship("FacesFromUser", back_populates="user")
    user_notifications = relationship("UserNotifications", back_populates="user", uselist=False)

    @classmethod
    async def get_user_by_email_or_username(cls, session: AsyncSession, email: str|None=None, username: str|None=None):
        conditions = []
        if email:
            conditions.append(cls.email.ilike(email))
        if username:
            conditions.append(cls.username.ilike(username))
        
        result = await session.execute(
            select(cls).filter(or_(*conditions))
        )
        users_query = result.scalars().all()
        
        if len(users_query) > 1 or not users_query:
            return None
            
        user = users_query[0]
        return user
    
    async def generate_token(self, session: AsyncSession):
        while True:
            new_token = str(uuid4())
            # Async query
            result = await session.execute(
                select(User).filter(User.token == new_token)
            )
            existing_user = result.scalars().first()
            
            if not existing_user:
                self.token = new_token
                break

    def get_allowed_notification_types(self):
        allowed_notifications = set()
        if self.user_notifications is None:
            return allowed_notifications
    
        if self.user_notifications.notification_new_video:
            allowed_notifications.add(VIDEO_TYPE_UNKNOWN)
        if self.user_notifications.notification_intruder:
            allowed_notifications.add(VIDEO_TYPE_INTRUDER)
        if self.user_notifications.notification_friend:
            allowed_notifications.add(VIDEO_TYPE_FRIEND)
        
        return allowed_notifications


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    user_group_connectors = relationship("UserGroupConnector", back_populates="group")
    cameras_group_connector = relationship("CameraGroupConnector", back_populates="group")


class UserGroupConnector(Base):
    __tablename__ = "user_group_connectors"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="user_group_connectors")

    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    group = relationship("Group", back_populates="user_group_connectors")


class UserNotifications(Base):
    __tablename__ = "user_notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    
    notification_new_video = Column(Boolean, default=False)
    notification_intruder = Column(Boolean, default=False)
    notification_friend = Column(Boolean, default=False)

    user = relationship("User", back_populates="user_notifications")
