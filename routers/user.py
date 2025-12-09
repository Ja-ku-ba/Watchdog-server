from typing import List

from fastapi import APIRouter, Depends, Response, status,  APIRouter, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from db.connector import get_session
from schemas.user import UserCreate, UserToken, UserAuthenticate, UserRefreshToken, \
    UserAccessToken, UserNotificationToken, UserNotificationSettings, VerifiedUsers, \
    AddVerifiedUser
from services.user import UserService
from utils.auth import AuthBackend
from models.user import User
from sqlalchemy.ext.asyncio import AsyncSession


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


@router.patch('/notification-token')
async def refresh_acces_token(notification_token: UserNotificationToken, session: AsyncSession = Depends(get_session), current_user: User = Depends(AuthBackend().get_current_user)):
    success = await UserService(session).assign_notification_token(notification_token, current_user)
    if success:
        return Response(status_code=status.HTTP_200_OK)
    return Response(status_code=status.HTTP_400_BAD_REQUEST)


@router.delete('/notification-token')
async def refresh_acces_token(session: AsyncSession = Depends(get_session), current_user: User = Depends(AuthBackend().get_current_user)):
    success = await UserService(session).delete_notification_token(current_user)
    if success:
        return Response(status_code=status.HTTP_200_OK)
    return Response(status_code=status.HTTP_400_BAD_REQUEST)


@router.get('/user-notification-settings', response_model=UserNotificationSettings)
async def get_user_notifications(session: AsyncSession = Depends(get_session), current_user: User = Depends(AuthBackend().get_current_user)):
    return await UserService(session).get_user_notification_settings(current_user)


@router.put('/user-notification-update', response_model=UserNotificationSettings)
async def get_user_notifications(notifications: UserNotificationSettings, session: AsyncSession = Depends(get_session), current_user: User = Depends(AuthBackend().get_current_user)):
    return await UserService(session).update_user_notification(notifications, current_user)


@router.get('/get-verified-users', response_model=list[VerifiedUsers])
async def get_user_notifications(session: AsyncSession = Depends(get_session), current_user: User = Depends(AuthBackend().get_current_user)):
    return await UserService(session).get_verified_users(current_user)


@router.post('/add-verified-user')
async def add_verified_user(verified_user: AddVerifiedUser, files: List[UploadFile] = File(...), session: AsyncSession = Depends(get_session), current_user: User = Depends(AuthBackend().get_current_user)):
    return await UserService(session).add_verified_user(current_user, verified_user, files)
