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
from services.video import VideoService


router = APIRouter(
    prefix='/videos',
    tags=['Videos']
)


@router.get("/get-videos", response_model=VideoList)
async def get_videos_list(session: AsyncSession = Depends(get_session), current_user: User = Depends(AuthBackend().get_current_user)):
    return await VideoService(session, current_user).get_videos_for_user()


@router.post("/save-info-about-video")
async def save_info_about_video(video_schema: VideoSchema, session: AsyncSession = Depends(get_session), current_camera: Camera = Depends(AuthBackend().get_current_device)):
    video_saved = await VideoService(session, current_camera=current_camera).save_info_about_video(video_schema)
    if not video_saved:
        raise HTTPException(status_code=500, detail="Video not saved")
    return Response(status_code=201)
