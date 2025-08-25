import datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.connector import get_session
from models.user import User
from schemas.user import UserCreate, UserToken
from utils.auth import AuthBackend

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
        await self.session.commit()
        await self.session.refresh(new_user)
        access_token = AuthBackend().create_access_token(new_user.email)
        refresh_token = AuthBackend().create_refresh_token(new_user.email)

        return {
            # "email": new_user.email,
            # "username": new_user.username,
            "access_token": access_token,
            "refresh_token": refresh_token
        }

    async def login(self, user_schema):
        existing_user = await User.get_user_by_email_or_username(
            session=self.session, email=user_schema.email
            )
        
        raise_exception = False


        if existing_user is not None:
            if existing_user.email != user_schema.email:
                raise_exception = True
        if existing_user is None:
            raise_exception = True

        if not raise_exception:
            password_valid = AuthBackend().verify_password(user_schema.password, existing_user.password)
            if not password_valid:
                raise_exception = True

        if raise_exception:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Nieprawidłowe hasło lub adres email"
            )

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