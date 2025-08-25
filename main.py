from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from routers import user, video
# from db.admin import admin_app


app = FastAPI()

@app.on_event("startup")
async def on_startup():

    from db.connector import run_migrations_once
    print("Start aplikacji — uruchamiam migracje (bez generowania plików)...")
    await run_migrations_once()
    print("Aplikacja gotowa.")

app.include_router(user.router)
app.include_router(video.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # W produkcji użyj konkretnych domen
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
