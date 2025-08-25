from sqlalchemy import select, or_
from sqlalchemy import Table, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from db.connector import Base


class UserGroupConnector(Base):
    __tablename__ = "user_group_connectors"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    
    # relacje dwustronne
    user = relationship("User", back_populates="user_group_connectors")
    group = relationship("Group", back_populates="user_group_connectors")


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    token = Column(String, unique=True)
    email = Column(String, unique=True)
    password = Column(String)
    active = Column(Boolean, default=True)
    super_user = Column(Boolean, default=False)
    activated_at = Column(DateTime)
    
    user_group_connectors = relationship("UserGroupConnector", back_populates="user")
    groups = relationship("Group", secondary="user_group_connectors", viewonly=True)
    
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


class Group(Base):
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    
    # relacje z użytkownikami
    user_group_connectors = relationship("UserGroupConnector", back_populates="group")
    users = relationship("User", secondary="user_group_connectors", viewonly=True)
    
    # relacje z kamerami
    camera_groups = relationship("CameraGroupConnector", back_populates="group")
    # POPRAWKA: zmieniono secondary na prawidłową nazwę tabeli
    cameras = relationship("Camera", secondary="camera_group_connectors", viewonly=True)




# class UserGroupConnector(Base):
#     __tablename__ = "user_group_connectors"

#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
#     group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)

#     # relacje dwustronne
#     user = relationship("User", back_populates="user_group_connectors")
#     group = relationship("Group", back_populates="user_group_connectors")


# class User(Base):
#     __tablename__ = "users"

#     id = Column(Integer, primary_key=True, index=True)
#     username = Column(String, unique=True)
#     token = Column(String, unique=True)
#     email = Column(String, unique=True)
#     password = Column(String)
#     active = Column(Boolean, default=True)
#     super_user = Column(Boolean, default=False)
#     activated_at = Column(DateTime)

#     user_group_connectors = relationship("UserGroupConnector", back_populates="user")
#     groups = relationship("Group", secondary="user_group_connectors", viewonly=True)

#     @classmethod
#     async def get_user_by_email_or_username(cls, session: AsyncSession, email: str|None=None, username: str|None=None):
#         conditions = []
#         if email:
#             conditions.append(cls.email.ilike(email))
#         if username:
#             conditions.append(cls.username.ilike(username))
#         result = await session.execute(
#             select(cls).filter(or_(*conditions))
#         )
#         users_querry = result.scalars().all()
#         if len(users_querry) > 1 or not users_querry:
#             return None
#         user = users_querry[0]
#         return user

#     async def generate_token(self, session: AsyncSession):
#         while True:
#             new_token = str(uuid4())
            
#             # Async query
#             result = await session.execute(
#                 select(User).filter(User.token == new_token)
#             )
#             existing_user = result.scalars().first()
            
#             if not existing_user:
#                 self.token = new_token
#                 break


# class Group(Base):
#     __tablename__ = "groups"

#     id = Column(Integer, primary_key=True)
#     name = Column(String, nullable=False)

#     # relacje z użytkownikami
#     user_group_connectors = relationship("UserGroupConnector", back_populates="group")
#     users = relationship("User", secondary="user_group_connectors", viewonly=True)

#     # relacje z kamerami
#     camera_group_connectors = relationship("CameraGroupConnector", back_populates="group")
#     cameras = relationship("Camera", secondary="camera_to_groups", viewonly=True)