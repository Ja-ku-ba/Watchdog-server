from fastapi import APIRouter, Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from db.connector import get_session
from schemas.user import UserCreate, UserToken, UserAuthenticate, UserRefreshToken, UserAccessToken
from services.user import UserService
from utils.auth import AuthBackend
from models.user import User


router = APIRouter(
    prefix='/users',
    tags=['Users']
)

@router.post("/register", response_model=UserToken)
async def create_user(user_schema: UserCreate, session: AsyncSession = Depends(get_session)):
    return await UserService(session).register(user_schema)


@router.post("/login", response_model=UserToken)
async def create_user(user_schema: UserAuthenticate, session: AsyncSession = Depends(get_session)):
    return await UserService(session).login(user_schema)


@router.post('/new-token', response_model=UserAccessToken)
async def refresh_acces_token(token: UserRefreshToken, session: AsyncSession = Depends(get_session), current_user: User = Depends(AuthBackend().get_current_user)):
    return await UserService(session).refresh_acces_token(token)