from fastapi import APIRouter, Request, Depends, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pathlib import Path

from app.database import get_db
from app import models, schemas
from app.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user_from_cookie,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(tags=["pages"])


# === Главная страница ===
@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    filter: str = "all",  # ← новый параметр
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_current_user_from_cookie),
):
    ratings = []
    if current_user:
        query = db.query(models.Rating).filter(models.Rating.user_id == current_user.id)
        if filter == "want_to_watch":
            query = query.filter(models.Rating.status == "want_to_watch")
        elif filter == "watched":
            query = query.filter(models.Rating.status == "watched")
        elif filter == "rated":
            query = query.filter(models.Rating.score.isnot(None))

        ratings = query.order_by(models.Rating.created_at.desc()).all()

    return templates.TemplateResponse(request, "index.html", {
        "user": current_user,
        "ratings": ratings,
        "active_filter": filter,
    })


# === Страница логина ===
@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {})


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(request, "login.html", {
            "error": "Неверный username или пароль",
        }, status_code=401)

    token = create_access_token({"sub": user.username, "user_id": user.id})
    redirect = RedirectResponse(url="/", status_code=303)
    redirect.set_cookie(
        key="access_token", value=token,
        httponly=True, max_age=60 * 60 * 24, samesite="lax",
    )
    return redirect


# === Страница регистрации ===
@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {})


@router.post("/register", response_class=HTMLResponse)
def register_submit(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    if db.query(models.User).filter(models.User.username == username).first():
        return templates.TemplateResponse(request, "register.html", {
            "error": "Username уже занят",
        }, status_code=400)

    if db.query(models.User).filter(models.User.email == email).first():
        return templates.TemplateResponse(request, "register.html", {
            "error": "Email уже занят",
        }, status_code=400)

    user = models.User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.username, "user_id": user.id})
    redirect = RedirectResponse(url="/", status_code=303)
    redirect.set_cookie(
        key="access_token", value=token,
        httponly=True, max_age=60 * 60 * 24, samesite="lax",
    )
    return redirect


# === Выход ===
@router.get("/logout")
def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("access_token")
    return response


# === Страница поиска ===
@router.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    q: str = "",
    current_user: models.User | None = Depends(get_current_user_from_cookie),
):
    results = []
    if q:
        from app.tmdb import search_movies, build_poster_url
        try:
            data = await search_movies(q)
            results = [
                {
                    "tmdb_id": m["id"],
                    "title": m.get("title", "Без названия"),
                    "overview": m.get("overview", ""),
                    "release_date": m.get("release_date", ""),
                    "poster_url": build_poster_url(m.get("poster_path")),
                }
                for m in data.get("results", [])
            ]
        except Exception as e:
            results = [{"error": str(e)}]

    return templates.TemplateResponse(request, "search.html", {
    "user": current_user,
    "query": q,
    "results": results,
    })
    
    
@router.get("/stats", response_class=HTMLResponse)
def stats_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User | None = Depends(get_current_user_from_cookie),
):
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    from sqlalchemy import func
    total = db.query(models.Rating).filter(models.Rating.user_id == current_user.id).count()
    watched = db.query(models.Rating).filter(
        models.Rating.user_id == current_user.id,
        models.Rating.status == "watched"
    ).count()
    avg = db.query(func.avg(models.Rating.score)).filter(
        models.Rating.user_id == current_user.id,
        models.Rating.score.isnot(None)
    ).scalar()

    stats = {
        "total": total,
        "watched": watched,
        "want_to_watch": total - watched,
        "avg_score": round(float(avg), 1) if avg else None,
    }

    return templates.TemplateResponse(request, "stats.html", {
        "user": current_user,
        "stats": stats,
    })