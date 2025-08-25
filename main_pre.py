from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from routers import user, video


app = FastAPI()

@app.on_event("startup")
async def on_startup():
    # from db.connector import run_migrations
    # await run_migrations()
    pass

app.include_router(user.router)
app.include_router(video.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # W produkcji użyj konkretnych domen
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, Response
import os


VIDEO_PATH = "/home/kuba/Desktop/watchdog_server/FILES/Boing377.mp4"

@app.api_route("/BigBuckBunny.mp4", methods=["GET", "HEAD"])
async def video_endpoint(request: Request):
    file_path = VIDEO_PATH
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video not found")

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
