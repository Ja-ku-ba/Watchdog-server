from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from fastapi.responses import Response

from db.connector import get_session
from services.analyze import AnalyzeService, PseudoAnalyzeService
from utils.auth import AuthBackend
from models.device import Camera
from models.user import User


router = APIRouter(
    prefix='/analyze',
    tags=['Analyze']
)


@router.post("/upload-face-to-analyze/")
async def anlyze(recorded_at: str = Form(...), file: UploadFile = File(...), session: AsyncSession = Depends(get_session), current_camera: Camera = Depends(AuthBackend().get_current_device)):
    if not await AnalyzeService(session, current_camera).save_file_to_analyze(file, recorded_at):
        raise HTTPException(status_code=500, detail="File not saved")
    return Response(status_code=202)


@router.post("/upload-known-face/")
async def anlyze(file: UploadFile = File(...), session: AsyncSession = Depends(get_session), current_user: User = Depends(AuthBackend().get_current_user)):
    if not await PseudoAnalyzeService(session, current_user).save_file_to_analyze(file):
        raise HTTPException(status_code=500, detail="File not saved")
    return Response(status_code=202)
