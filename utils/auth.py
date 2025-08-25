import jwt
from datetime import datetime, timedelta, timezone
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Union, Any
from passlib.context import CryptContext

from db.connector import get_session
from utils.env_variables import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_MINUTES
from models.user import User
from schemas.user import UserDataFromToken


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/users/new-token"
)


class AuthBackend:
    def verify_password(self, plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password):
        return pwd_context.hash(password)

    # def authenticate_user(self, fake_db, username: str, password: str):
    #     user = get_user(fake_db, username)
    #     if not user:
    #         return False
    #     if not verify_password(password, user.hashed_password):
    #         return False
    #     return user

    def create_refresh_token(self, email: str) -> str:
        expires_delta = datetime.utcnow() + timedelta(minutes=int(REFRESH_TOKEN_EXPIRE_MINUTES))
        encoded_jwt = jwt.encode({
                "exp": expires_delta, 
                "email": str(email)
            }, 
            SECRET_KEY, 
            ALGORITHM
        )
        return encoded_jwt

    def create_access_token(self, email: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
        encoded_jwt = jwt.encode({
                'email': email,
                'exp': expire
            }, 
            SECRET_KEY, 
            ALGORITHM
        )
        return encoded_jwt
    
    async def refresh_acces_token(self, session: AsyncSession, refresh_token: str) -> str:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is unactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
        refresh_token_data = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if datetime.now() >= datetime.fromtimestamp(refresh_token_data['exp']):
            raise credentials_exception
        user = await User.get_user_by_email_or_username(session, email=refresh_token_data['email'])
        if user is None:
            raise credentials_exception
        
        return {
            'access_token': self.create_access_token(user.email),
        }

    async def get_current_user(self, session: AsyncSession = Depends(get_session), token: str = Depends(oauth2_scheme)) -> User:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("email")
            
            if email is None:
                raise credentials_exception
                
            token_scopes = payload.get("scopes", [])
            token_data = UserDataFromToken(email=email, scopes=token_scopes)
            
        except jwt.ExpiredSignatureError as jwtESE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as jwtITE:
            raise credentials_exception

        user = await User.get_user_by_email_or_username(session, email=token_data.email)
        if user is None:
            raise credentials_exception
        print(f"User id: {user.id}")
        return User(
            id=user.id,
            username=user.username,
            email=user.email,
            active=user.active,
            # scopes=user.scopes
        )

    async def get_current_active_user(self, current_user: Annotated[User, Depends(get_current_user)]):
        if current_user.disabled:
            raise HTTPException(status_code=400, detail="Inactive user")
        return current_user

