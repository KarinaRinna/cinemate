from fastapi import APIRouter, Depends, HTTPException, Query
from app.auth import get_current_user
from app import models, schemas
from app.tmdb import search_movies, build_poster_url
from app.database import get_db
from sqlalchemy.orm import Session
from app.auth import get_current_user, get_current_user_flexible


router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("/search", response_model=schemas.MovieSearchResult)
async def search(
    q: str = Query(..., min_length=1, description="Поисковый запрос"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    current_user: models.User = Depends(get_current_user_flexible),
):
    """Ищет фильмы через TMDB. Требует авторизации."""
    try:
        data = await search_movies(q, page)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ошибка TMDB: {e}")

    # Преобразуем сырой ответ TMDB в наш формат
    results = []
    for movie in data.get("results", []):
        results.append(schemas.MovieResponse(
            tmdb_id=movie["id"],
            title=movie.get("title", "Без названия"),
            overview=movie.get("overview"),
            release_date=movie.get("release_date"),
            poster_url=build_poster_url(movie.get("poster_path")),
        ))

    return schemas.MovieSearchResult(
        page=data.get("page", 1),
        total_results=data.get("total_results", 0),
        results=results,
    )
    
    
@router.post("/{tmdb_id}/add", response_model=schemas.RatingResponse, status_code=201)
async def add_movie_to_watchlist(
    tmdb_id: int,
    rating_data: schemas.RatingCreate,
    current_user: models.User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """
    Добавляет фильм в избранное.
    - Если фильма нет в БД — сначала загружает из TMDB и сохраняет.
    - Если уже добавлен — обновляет статус.
    """
    # 1. Ищем фильм в нашей БД
    movie = db.query(models.Movie).filter(models.Movie.tmdb_id == tmdb_id).first()

    # 2. Если нет — идём в TMDB и создаём
    if not movie:
        from app.tmdb import get_movie_details
        try:
            tmdb_data = await get_movie_details(tmdb_id)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Ошибка TMDB: {e}")

        movie = models.Movie(
            tmdb_id=tmdb_data["id"],
            title=tmdb_data.get("title", "Без названия"),
            overview=tmdb_data.get("overview"),
            release_date=tmdb_data.get("release_date"),
            poster_path=tmdb_data.get("poster_path"),
        )
        db.add(movie)
        db.commit()
        db.refresh(movie)

    # 3. Проверяем, не добавил ли юзер уже этот фильм
    existing_rating = db.query(models.Rating).filter(
        models.Rating.user_id == current_user.id,
        models.Rating.movie_id == movie.id,
    ).first()

    if existing_rating:
        # Обновляем статус
        existing_rating.status = rating_data.status
        db.commit()
        db.refresh(existing_rating)
        return _build_rating_response(existing_rating, movie)

    # 4. Создаём новую запись в ratings
    rating = models.Rating(
        user_id=current_user.id,
        movie_id=movie.id,
        status=rating_data.status,
    )
    db.add(rating)
    db.commit()
    db.refresh(rating)

    return _build_rating_response(rating, movie)


@router.get("/me", response_model=list[schemas.RatingResponse])
def my_movies(
    current_user: models.User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """Возвращает все фильмы текущего пользователя."""
    ratings = (
        db.query(models.Rating)
        .filter(models.Rating.user_id == current_user.id)
        .order_by(models.Rating.created_at.desc())
        .all()
    )

    return [
        _build_rating_response(r, r.movie)
        for r in ratings
    ]


@router.patch("/{tmdb_id}/rate", response_model=schemas.RatingResponse)
def rate_movie(
    tmdb_id: int,
    rating_data: schemas.RatingUpdate,
    current_user: models.User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """Обновляет оценку и/или статус фильма."""
    movie = db.query(models.Movie).filter(models.Movie.tmdb_id == tmdb_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Фильм не найден в вашем списке")

    rating = db.query(models.Rating).filter(
        models.Rating.user_id == current_user.id,
        models.Rating.movie_id == movie.id,
    ).first()
    if not rating:
        raise HTTPException(status_code=404, detail="Сначала добавьте фильм в избранное")

    if rating_data.score is not None:
        rating.score = rating_data.score
    if rating_data.status is not None:
        rating.status = rating_data.status

    db.commit()
    db.refresh(rating)

    return _build_rating_response(rating, movie)


# === Хелпер для формирования ответа ===
def _build_rating_response(rating: models.Rating, movie: models.Movie) -> schemas.RatingResponse:
    from app.tmdb import build_poster_url
    return schemas.RatingResponse(
        id=rating.id,
        movie=schemas.MovieResponse(
            tmdb_id=movie.tmdb_id,
            title=movie.title,
            overview=movie.overview,
            release_date=movie.release_date,
            poster_url=build_poster_url(movie.poster_path),
        ),
        score=rating.score,
        status=rating.status,
        created_at=rating.created_at,
    )
