import os
import httpx
from dotenv import load_dotenv

load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"  # для постеров


async def search_movies(query: str, page: int = 1) -> dict:
    """Ищет фильмы по названию через TMDB API."""
    if not TMDB_API_KEY or TMDB_API_KEY == "placeholder":
        raise ValueError("TMDB_API_KEY не настроен в .env")

    url = f"{TMDB_BASE_URL}/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": query,
        "page": page,
        "language": "ru-RU",  # русские названия и описания
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


async def get_movie_details(tmdb_id: int) -> dict:
    """Получает подробную информацию о фильме."""
    url = f"{TMDB_BASE_URL}/movie/{tmdb_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "ru-RU",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def build_poster_url(poster_path: str | None) -> str | None:
    """Строит полный URL постера."""
    if not poster_path:
        return None
    return f"{TMDB_IMAGE_BASE}{poster_path}"