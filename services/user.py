import os
import datetime
import shutil
from typing import List

from fastapi import HTTPException, status, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case, update, or_
from sqlalchemy.orm import selectinload

from models.analyze import FacesFromUser
from models.user import User, UserNotifications, Group, UserGroupConnector
from schemas.user import UserCreate, UserToken, UserNotificationToken, UserNotificationSettings
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
        users_in_same_groups = (
            select(UserGroupConnector.user_id)
            .where(
                UserGroupConnector.group_id.in_(
                    select(UserGroupConnector.group_id)
                    .where(UserGroupConnector.user_id == current_user.id)
                )
            )
            .distinct()
        )

        stmt = (
            select(
                FacesFromUser.name.label("name"),
                FacesFromUser.name_hash.label("hash"),
                func.array_agg(func.distinct(FacesFromUser.hash)).label("image_hashes"),
                func.count(func.distinct(FacesFromUser.id)).label("files_counter"),
            )
            .where(
                or_(
                    FacesFromUser.user_id == current_user.id,
                    FacesFromUser.user_id.in_(users_in_same_groups)
                )
            )
            .group_by(
                FacesFromUser.name,
                FacesFromUser.name_hash,
            )
        )

        result = await self.session.execute(stmt)
        return result.all()

    async def add_verified_user(self, current_user: User, verified_user, files: List[UploadFile]):
        query = select(
            func.count(FacesFromUser.id).label('total_count'),
            func.sum(
                case(
                    (func.lower(FacesFromUser.name) == func.lower(verified_user.name), 1),
                    else_=0
                )
            ).label('name_exists')
        ).where(
            FacesFromUser.user_id == current_user.id
        )

        result = await self.session.execute(query)
        row = result.one()

        user_count = row.total_count
        name_exists = False
        if row.name_exists:
            name_exists = row.name_exists > 0

        if name_exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Użytkownik o tej nazwie już istnieje"
            )

        if user_count >= 3:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Możesz posiadać maksymalnie 3 zweryfikowanych użytkowników, nie możesz dodać nowego"
            )

        user_hash = None
        for file in files:
            if not file.content_type.startswith("image/"):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Plik nie jest zdjęciem"
                )

            created_at = datetime.datetime.now()
            file_path = self.save_photo_to_files(current_user, file, created_at)
            new_face = FacesFromUser(
                user_id=current_user.id,
                name=verified_user.name,
                file_path=file_path,
                created_at=datetime.datetime.now()
            )
            await new_face.generate_hash(self.session)
            if not user_hash:
                # Do it this way, there is no connctror from user to file
                # model structure in this aspect is flat, assign hash so 
                # when user watns to operante on instance there is reference 
                # to this specfic user in group
                user_hash = new_face.hash
            new_face.name_hash = user_hash
            self.session.add(new_face)
            await self.session.commit()
        return True

    async def get_verified_user_photo(self, current_user: User, hash: str):
        face_photo = await self.__get_verified_user_photo_by_ucer_hash(current_user, hash)
        file_path = face_photo.file_path
        # if not os.path.exists(file_path):
            # raise HTTPException(
                # status_code=status.HTTP_404_NOT_FOUND,
                # detail="Plik nie istnieje"
            # )

        return file_path

    async def delete_verified_user_photo(self, current_user: User, hash: str):
        total_photos = await self.count_name_hash_for_photo(current_user, hash)
        if total_photos <= 1:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Użytkownik musi posiadać conajmniej jedno zdjęcie"
            )

        face_photo = await self.__get_verified_user_photo_by_ucer_hash(current_user, hash)
        file_path = face_photo.file_path
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Plik nie istnieje"
            )
        else:
            file_path = face_photo.file_path
            try:
                os.remove(file_path)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Nie udało się usunąć pliku: {e}"
                )

        await self.session.delete(face_photo)
        await self.session.commit()
        return Response(
            status_code=status.HTTP_200_OK,
            content="Usunięto zdjęcie"
        )

    async def update_verified_user(self, verified_user_data, current_user, name_hash, files):
        new_name = verified_user_data.name
        if not new_name or len(new_name.strip()) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nazwa musi mieć minimum 3 znaki"
            )

        existing_photos_count = await self.count_photos_for_name_hash(current_user, name_hash)
        new_files_count = len(files) if files else 0
        total_photos = existing_photos_count + new_files_count

        if total_photos > 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Możesz mieć maksymalnie 3 zdjęcia. Aktualnie: {existing_photos_count}, próbujesz dodać: {new_files_count}"
            )

        if files:
            for file in files:
                created_at = datetime.datetime.now()
                file_path = self.save_photo_to_files(current_user, file, created_at)
                new_face = FacesFromUser(
                    user_id=current_user.id,
                    name=new_name,
                    file_path=file_path,
                    created_at=datetime.datetime.now()
                )
                await new_face.generate_hash(self.session)
                new_face.name_hash = name_hash
                self.session.add(new_face)
            await self.session.commit()

        
        await self.update_verified_user_name(current_user, name_hash, new_name)

    async def update_verified_user_name(self, current_user, name_hash, new_name):
        stmt = (
            update(FacesFromUser)
            .where(
                FacesFromUser.name_hash == name_hash,
                FacesFromUser.user_id.in_(
                    select(UserGroupConnector.user_id).where(
                        UserGroupConnector.group_id.in_(
                            select(UserGroupConnector.group_id).where(
                                UserGroupConnector.user_id == current_user.id
                            )
                        )
                    )
                )
            )
            .values(name=new_name)
        )

        result = await self.session.execute(stmt)

        if result.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Nie znaleziono użytkownika lub brak dostępu"
            )

        await self.session.commit()

    async def __get_verified_user_photo_by_ucer_hash(self, current_user, hash):
        users_in_same_groups = (
            select(UserGroupConnector.user_id)
            .where(
                UserGroupConnector.group_id.in_(
                    select(UserGroupConnector.group_id)
                    .where(UserGroupConnector.user_id == current_user.id)
                )
            )
        )

        query = select(FacesFromUser).where(
            FacesFromUser.hash == hash,
            or_(
                FacesFromUser.user_id == current_user.id,
                FacesFromUser.user_id.in_(users_in_same_groups)
            )
        )
    
        result = await self.session.execute(query)
        face_photo = result.scalar_one_or_none()
        
        if not face_photo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nie znaleziono zdjęcia lub brak dostępu"
            )
        return face_photo

    async def __extract_name_hash_from_photo_hash(self, current_user, photo_hash):
        stmt = (
            select(FacesFromUser.name_hash)
            .where(
                FacesFromUser.hash == photo_hash,
                FacesFromUser.user_id.in_(
                    select(UserGroupConnector.user_id).where(
                        UserGroupConnector.group_id.in_(
                            select(UserGroupConnector.group_id).where(
                                UserGroupConnector.user_id == current_user.id
                            )
                        )
                    )
                )
            )
            .limit(1)
        )

        result = await self.session.execute(stmt)
        name_hash = result.scalar_one_or_none()

        if not name_hash:
            raise HTTPException(
                status_code=404,
                detail="Nie znaleziono zdjęcia lub brak dostępu"
            )

        return name_hash

    async def count_photos_for_name_hash(self, current_user: User, name_hash: str) -> int:
        stmt = (
            select(func.count(FacesFromUser.id))
            .where(
                FacesFromUser.name_hash == name_hash,
                FacesFromUser.user_id.in_(
                    select(UserGroupConnector.user_id).where(
                        UserGroupConnector.group_id.in_(
                            select(UserGroupConnector.group_id).where(
                                UserGroupConnector.user_id == current_user.id
                            )
                        )
                    )
                )
            )
        )

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_name_hash_for_photo(self, current_user, hash):
        name_hash = await self.__extract_name_hash_from_photo_hash(current_user, hash)
        query = select(func.count(FacesFromUser.id)).where(
            FacesFromUser.name_hash == name_hash,
            FacesFromUser.user_id.in_(
                select(UserGroupConnector.user_id)
                .where(UserGroupConnector.group_id.in_(
                    select(UserGroupConnector.group_id)
                    .where(UserGroupConnector.user_id == current_user.id)
                ))
            )
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def delete_verified_user(self, current_user: User, name_hash: str):
        query = select(FacesFromUser).where(
            FacesFromUser.name_hash == name_hash,
            FacesFromUser.user_id.in_(
                select(UserGroupConnector.user_id)
                .where(UserGroupConnector.group_id.in_(
                    select(UserGroupConnector.group_id)
                    .where(UserGroupConnector.user_id == current_user.id)
                ))
            )
        )
        
        results = await self.session.execute(query)
        faces = results.scalars().all()
        
        if not faces:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nie znaleziono użytkownika"
            )
        
        file_paths = []
        
        for face in faces:
            file_path = face.file_path
            
            if not os.path.exists(file_path):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Plik nie istnieje: {file_path}"
                )
            
            file_paths.append(file_path)
            await self.session.delete(face)

        try:
            for file_path in file_paths:
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(str(e))
                    raise e

            await self.session.commit()

            return Response(
                status_code=status.HTTP_200_OK,
                content="Usunięto użytkownika"
            )

        except Exception as e:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Nie udało się usunąć użytkownika"
            )

    async def get_user_groups(self, current_user:User):
        """Pobiera grupy użytkownika posortowane alfabetycznie."""
        stmt = (
            select(Group)
            .join(UserGroupConnector, UserGroupConnector.group_id == Group.id)
            .where(UserGroupConnector.user_id == current_user.id)
            .options(
                selectinload(Group.user_group_connectors).selectinload(UserGroupConnector.user)
            )
            .order_by(Group.name.asc())
            .distinct()
        )
        
        result = await self.session.execute(stmt)
        groups = result.scalars().unique().all()
        
        groups_data = []
        
        for group in groups:
            users_list = sorted([
                user_group_connector.user.email
                for user_group_connector in group.user_group_connectors
                if user_group_connector.user
            ])
            
            groups_data.append({
                "name": group.name,
                "users": users_list
            })
        
        return groups_data

    @staticmethod
    def save_photo_to_files(current_user, file, created_at=datetime.datetime.now()):
        file_path = os.path.join(UPLOAD_DIR_KNOWN, current_user.username, )

        if not os.path.exists(file_path):
            os.makedirs(file_path)

        file_path = os.path.join(file_path, f'{created_at}_{file.filename}')

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return file_path
