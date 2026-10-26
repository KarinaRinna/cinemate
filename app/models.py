from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связь: один юзер -> много оценок
    ratings = relationship("Rating", back_populates="user", cascade="all, delete-orphan")


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, index=True)
    tmdb_id = Column(Integer, unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    overview = Column(Text, nullable=True)
    release_date = Column(String(20), nullable=True)
    poster_path = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связь: один фильм -> много оценок
    ratings = relationship("Rating", back_populates="movie", cascade="all, delete-orphan")


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"), nullable=False)
    score = Column(Integer, nullable=True)  # 1-10, может быть NULL если только "хочу посмотреть"
    status = Column(String(20), default="want_to_watch")  # want_to_watch | watched
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи обратно
    user = relationship("User", back_populates="ratings")
    movie = relationship("Movie", back_populates="ratings")

    # Один юзер может поставить только одну оценку одному фильму
    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="unique_user_movie"),
    )