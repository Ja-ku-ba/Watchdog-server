import os
from fastapi import APIRouter, Depends,  Request, HTTPException
from fastapi.responses import StreamingResponse, Response, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.video import VideoList
from db.connector import get_session
from utils.auth import AuthBackend
from models.user import User
from services.video import VideoService, VideoStramingService


router = APIRouter(
    prefix='/videos',
    tags=['Videos']
)


VIDEO_PATH = "/home/kuba/Desktop/watchdog_server/FILES/2025-08-16/1/1/VID20250817115259.mp4"

@router.api_route("/get-videos", response_model=VideoList)
async def get_videos_list(session: AsyncSession = Depends(get_session), current_user: User = Depends(AuthBackend().get_current_user)):
    return await VideoService(session, current_user).get_videos_for_user()


@router.api_route("/thumbnail/{file_hash}", response_model=VideoList)
async def get_thumbnail(file_hash: str, session: AsyncSession = Depends(get_session), current_user: User = Depends(AuthBackend().get_current_user)):
    file_path = await VideoService(session, current_user).get_video_path_for_user(file_hash)
    print(file_path)
    if not file_path or not os.path.exists(file_path.get('thumbnail')):
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(path=file_path.get('thumbnail'), filename="thumbnail.png", media_type="image/png")


@router.api_route("/{file_hash}", methods=["GET", "HEAD"])
async def video_endpoint(file_hash: str, request: Request, session: AsyncSession = Depends(get_session), current_user: User = Depends(AuthBackend().get_current_user)):
    file_path = await VideoService(session, current_user).get_video_path_for_user(file_hash)
    print(file_path)
    if not file_path or not os.path.exists(file_path.get('video')):
        raise HTTPException(status_code=404, detail="Video not found")
    file_path = file_path.get('video')
    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("range")

    def iterfile(start: int, end: int):
        with open(file_path, "rb") as f:
            f.seek(start)
            while start < end:
                chunk_size = min(1024 * 1024, end - start)  # 1MB chunks
                data = f.read(chunk_size)
                if not data:
                    break
                start += len(data)
                yield data

    if range_header:
        # Obsługa np. "bytes=0-1023"
        start_str, end_str = range_header.replace("bytes=", "").split("-")
        start = int(start_str) if start_str else 0
        end = int(end_str) if end_str else file_size - 1

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(end - start + 1),
            "Content-Type": "video/mp4",
        }

        if request.method == "HEAD":
            return Response(status_code=206, headers=headers)

        return StreamingResponse(iterfile(start, end + 1),
                                 status_code=206,
                                 headers=headers)

    # Bez Range → wysyłamy cały plik
    headers = {
        "Content-Length": str(file_size),
        "Content-Type": "video/mp4",
        "Accept-Ranges": "bytes",
    }

    if request.method == "HEAD":
        return Response(status_code=200, headers=headers)

    return StreamingResponse(iterfile(0, file_size), headers=headers)
