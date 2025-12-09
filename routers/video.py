import os
from fastapi import APIRouter, Depends,  Request, HTTPException
from fastapi.responses import StreamingResponse, Response, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from schemas.video import VideoList, VideoSchema
from db.connector import get_session
from utils.auth import AuthBackend
from models.user import User
from models.device import Camera
from services.video import VideoService, VideoStramingService


router = APIRouter(
    prefix='/videos',
    tags=['Videos']
)


@router.get("/get-videos-hashes", response_model=List[str])
async def get_videos_list(offset: int = 0, limit: int = 15, session: AsyncSession = Depends(get_session), current_user: User = Depends(AuthBackend().get_current_user)):
    return await VideoService(session, current_user).get_video_hashes_for_user(offset, limit)


@router.get("/get-videos", response_model=VideoList)
async def get_videos_list(session: AsyncSession = Depends(get_session), current_user: User = Depends(AuthBackend().get_current_user)):
    return await VideoService(session, current_user).get_videos_for_user()


@router.get("/thumbnail/{file_hash}", response_model=VideoList)
async def get_thumbnail(file_hash: str, session: AsyncSession = Depends(get_session), current_user: User = Depends(AuthBackend().get_current_user)):
    file_path = await VideoService(session, current_user).get_video_path_for_user(file_hash)
    if not file_path or not os.path.exists(file_path.get('thumbnail')):
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(path=file_path.get('thumbnail'), filename="thumbnail.png", media_type="image/png")


@router.post("/save-info-about-video")
async def save_info_about_video(video_schema: VideoSchema, session: AsyncSession = Depends(get_session), current_camera: Camera = Depends(AuthBackend().get_current_device)):
    video_saved = await VideoService(session, current_camera=current_camera).save_info_about_video(video_schema)
    if not video_saved:
        raise HTTPException(status_code=500, detail="Video not saved")
    return Response(status_code=201)
