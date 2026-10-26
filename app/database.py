import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Загружаем переменные из .env
load_dotenv()

# Читаем URL базы данных
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL не найден в .env файле!")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)

# Создаём движок (engine) — соединение с PostgreSQL
engine = create_engine(DATABASE_URL)

# Фабрика сессий — через неё будем делать запросы к БД
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для всех моделей (таблиц)
Base = declarative_base()


# Зависимость для FastAPI: даёт сессию БД и закрывает после запроса
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()