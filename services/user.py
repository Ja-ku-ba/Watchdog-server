import os
import datetime
import shutil
from typing import List

from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models.device import Camera, CameraGroupConnector
from models.analyze import FilesAnalyze, FacesFromUser
from models.user import User, UserNotifications, Group, UserGroupConnector
from schemas.user import UserCreate, UserToken, UserNotificationToken, UserNotificationSettings, \
    AddVerifiedUser
from utils.auth import AuthBackend
from utils.env_variables import UPLOAD_DIR_KNOWN


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def register(self, user_schema: UserCreate):
        existing_user = await self._user_exists(user_schema)

        if existing_user is not None:
            if existing_user.email == user_schema.email:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Adres email już istnieje"
                )
            elif existing_user.username == user_schema.username:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Nazwa użytkownika jest zajęta"
                )

        new_user = User(**user_schema.dict())
        await new_user.generate_token(self.session)
        
        hashed_password = AuthBackend().get_password_hash(user_schema.password)
        new_user.password = hashed_password
        new_user.activated_at = datetime.datetime.now()

        self.session.add(new_user)
        await self.session.flush()

        user_notifications = UserNotifications(user_id=new_user.id)
        self.session.add(user_notifications)

        await self.session.commit()
        await self.session.refresh(new_user)

        access_token = AuthBackend().create_access_token(new_user.email)
        refresh_token = AuthBackend().create_refresh_token(new_user.email)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }

    async def login(self, user_schema):
        existing_user = await self.verify_user_cridentials(user_schema.email, user_schema.password)

        access_token = AuthBackend().create_access_token(existing_user.email)
        refresh_token = AuthBackend().create_refresh_token(existing_user.email)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token
        }

    async def _user_exists(self, user_schema):
        return await User.get_user_by_email_or_username(
            session=self.session, username=user_schema.username
            )

    async def refresh_acces_token(self, token: UserToken):
        return await AuthBackend().refresh_acces_token(self.session, token.refresh_token)
    
    async def assign_notification_token(self, notification_token: UserNotificationToken, user: User):
        return await AuthBackend().assign_notification_token(self.session, notification_token, user)
    
    async def delete_notification_token(self, user: User):
        return await AuthBackend().delete_notification_token(self.session, user)
    
    async def verify_user_cridentials(self, email, password):
        existing_user = await User.get_user_by_email_or_username(
            session=self.session, email=email
            )
        
        raise_exception = False


        if existing_user is not None:
            if existing_user.email != email:
                raise_exception = True
        if existing_user is None:
            raise_exception = True

        if not raise_exception:
            password_valid = AuthBackend().verify_password(password, existing_user.password)
            if not password_valid:
                raise_exception = True

        if raise_exception:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Nieprawidłowe hasło lub adres email"
            )
        
        return existing_user
        
    async def get_user_notification_settings(self, current_user: User):
        result = await self.session.execute(
            select(UserNotifications).filter(UserNotifications.user_id == current_user.id)
        )
        notifications = result.scalars().first()
        
        if not notifications:
            notifications = await self.update_user_notification()
        return notifications

    async def update_user_notification(self, updated_notifications: UserNotificationSettings, current_user: User):
        result = await self.session.execute(
            select(UserNotifications).filter(UserNotifications.user_id == current_user.id)
        )
        notifications = result.scalars().first()
        
        if not notifications:
            notifications = UserNotifications(user_id=current_user.id)
            self.session.add(notifications)
        
        update_data = updated_notifications.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(notifications, field, value)
        
        await self.session.commit()
        await self.session.refresh(notifications)

        return notifications

    async def get_verified_users(self, current_user: User):
        result = await self.session.execute(
            select(
                FacesFromUser,
                func.count(FacesFromUser.id).label("images_per_user_in_group")
            )
            .join(User, FacesFromUser.user_id == User.id)
            .join(UserGroupConnector, UserGroupConnector.user_id == User.id)
            .join(Group, UserGroupConnector.group_id == Group.id)
            .where(
                Group.id.in_(
                    select(UserGroupConnector.group_id)
                    .where(UserGroupConnector.user_id == current_user.id)
                )
            )
            .group_by(FacesFromUser.id, FacesFromUser.name)
            .distinct()
        )
        
        rows = result.all()
        return [
            (setattr(face_obj, "images_per_user_in_group", count) or face_obj)
            for face_obj, count in rows
        ]

    async def add_verified_user(self, current_user: User, verified_user: AddVerifiedUser, files: List[UploadFile]):
        query = select(FacesFromUser.name).where(
            FacesFromUser.user_id == current_user.id
        )
        result = await self.session.execute(query)
        existing_names = result.scalars().all()

        if verified_user.name in existing_names:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Użytkownik o tej nazwie już istnieje"
            )
        
        for file in files:
            if not file.content_type.startswith("image/"):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Plik nie jest zdjęciem"
                )
            
            created_at = datetime.datetime.now()
            file_path = os.path.join(UPLOAD_DIR_KNOWN, self._user.username, )
            
            if not os.path.exists(file_path):
                os.makedirs(file_path)
            
            file_path = os.path.join(file_path, f'{created_at}_{file.filename}')
        
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            new_face = FacesFromUser(
                user_id=current_user.id,
                name=verified_user.name,
                file_path=file_path,
                created_at=datetime.datetime.now()
            )
            await new_face.generate_hash(self._session)
            
            self.session.add(new_face)
            await self.session.commit()
        
        return True
