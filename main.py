from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

from routers import user, video


app = FastAPI()

@app.on_event("startup")
async def on_startup():
    from db.connector import run_migrations_once
    print("Start aplikacji — uruchamiam migracje (bez generowania plików)...")
    await run_migrations_once()
    print("Aplikacja gotowa.")

app.include_router(user.router)
app.include_router(video.router)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # W produkcji użyj konkretnych domen
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


from dotenv import load_dotenv
load_dotenv()

from fastadmin import fastapi_app as admin_app
from db.admin import UserAdmin
app.mount("/admin", admin_app)

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
