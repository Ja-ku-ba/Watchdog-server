import json
from typing import List, Optional

from fastapi import APIRouter, Depends, Response, status,  APIRouter, File, \
    UploadFile, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from db.connector import get_session
from schemas.user import UserCreate, UserToken, UserAuthenticate, \
    UserRefreshToken, UserAccessToken, UserNotificationToken, \
    UserNotificationSettings, VerifiedUsers, AddVerifiedUser, UserGroups
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
async def add_verified_user(verified_user: str = Form(...), files: List[UploadFile] = File(...), session: AsyncSession = Depends(get_session), current_user: User = Depends(AuthBackend().get_current_user)):
    verified_user_data = AddVerifiedUser(**json.loads(verified_user))
    return await UserService(session).add_verified_user(current_user, verified_user_data, files)


@router.get('/verified-user/photo/{hash}')
async def get_verified_user_photo(hash: str, session: AsyncSession = Depends(get_session), current_user: User = Depends(AuthBackend().get_current_user)):
    file_path = await UserService(session).get_verified_user_photo(current_user, hash)
    return FileResponse(
        file_path,
        media_type="image/jpeg",
    )


@router.delete('/verified-user/photo/{hash}')
async def get_verified_user_photo(hash: str, session: AsyncSession = Depends(get_session), current_user: User = Depends(AuthBackend().get_current_user)):
    return await UserService(session).delete_verified_user_photo(current_user, hash)


@router.put('/verified-user/{name_hash}')
async def update_verified_user(
    name_hash: str, verified_user: str = Form(...), files: Optional[List[UploadFile]] = None,
    session: AsyncSession = Depends(get_session), current_user: User = Depends(AuthBackend().get_current_user),
):
    try:
        verified_user_data = AddVerifiedUser(**json.loads(verified_user))

        user_service = UserService(session)
        await user_service.update_verified_user(verified_user_data, current_user, name_hash, files)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"detail": "Użytkownik został zaktualizowany"}
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Niepoprawny format JSON"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete('/verified-user/{name_hash}')
async def get_verified_user_photo(name_hash: str, session: AsyncSession = Depends(get_session), current_user: User = Depends(AuthBackend().get_current_user)):
    return await UserService(session).delete_verified_user(current_user, name_hash)


@router.get("/user-groups-list", response_model=list[UserGroups])
async def register_device(current_user: User = Depends(AuthBackend().get_current_user), session: AsyncSession = Depends(get_session)):
    return await UserService(session).get_user_groups(current_user)
