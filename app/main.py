from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.database import engine, Base
from app import models
from app.routers import users, movies

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CineMate API", version="0.1.0")

# Пути к шаблонам и статике
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Подключаем роутеры API
app.include_router(users.router)
app.include_router(movies.router)

# Подключаем роутер страниц (HTML)
from app.routers import pages  # импорт здесь, чтобы не было циклов
app.include_router(pages.router)


@app.get("/health")
def health():
    return {"status": "ok"}