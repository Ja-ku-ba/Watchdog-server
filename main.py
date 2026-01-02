from fastapi import FastAPI
from fastapi import FastAPI

from routers import user, video, analyze, device


app = FastAPI()


@app.on_event("startup")
async def on_startup():
    # alembic revision --autogenerate -m "thumbnail_file_path"
    from db.connector import run_migrations_once
    print("Start aplikacji — uruchamiam migracje (bez generowania plików)...")
    await run_migrations_once()
    print("Aplikacja gotowa.")


app.include_router(user.router)
app.include_router(video.router)
app.include_router(analyze.router)
app.include_router(device.router)

from dotenv import load_dotenv
load_dotenv()
