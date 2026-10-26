from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# === Схемы для User ===

class UserCreate(BaseModel):
    """Данные для регистрации."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    """Данные для входа."""
    username: str
    password: str


class UserResponse(BaseModel):
    """Что возвращаем клиенту (БЕЗ пароля!)."""
    id: int
    username: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True  # Позволяет читать данные из SQLAlchemy-модели


class Token(BaseModel):
    """Ответ при успешном логине."""
    access_token: str
    token_type: str = "bearer"
    
    
# === Схемы для Movie ===

class MovieResponse(BaseModel):
    """Информация о фильме (из TMDB или из нашей БД)."""
    tmdb_id: int
    title: str
    overview: str | None = None
    release_date: str | None = None
    poster_url: str | None = None


class MovieSearchResult(BaseModel):
    """Результат поиска: список фильмов."""
    page: int
    total_results: int
    results: list[MovieResponse]
    
    
# === Схемы для Rating (оценки/избранное) ===

class RatingCreate(BaseModel):
    """Добавление фильма в избранное."""
    tmdb_id: int
    status: str = Field("want_to_watch", pattern="^(want_to_watch|watched)$")


class RatingUpdate(BaseModel):
    """Обновление оценки/статуса."""
    score: int | None = Field(None, ge=1, le=10)
    status: str | None = Field(None, pattern="^(want_to_watch|watched)$")


class RatingResponse(BaseModel):
    """Ответ с информацией о фильме + оценке."""
    id: int
    movie: MovieResponse
    score: int | None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True