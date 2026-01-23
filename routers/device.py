from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from fastapi.responses import Response

from db.connector import get_session
from services.device import DeviceService
from utils.auth import AuthBackend
from models.device import Camera
from schemas.device import RegisterDevice


router = APIRouter(
    prefix='/device',
    tags=['Device']
)


@router.post("/register-device/")
async def register_device(request_device: RegisterDevice, session: AsyncSession = Depends(get_session), current_camera: Camera = Depends(AuthBackend().get_current_device)):
    status = await DeviceService(session, current_camera).register_device(request_device)
    if not status:
        raise HTTPException(status_code=400)
    return Response(status_code=202)
