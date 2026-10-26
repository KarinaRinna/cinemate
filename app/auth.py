import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import bcrypt
import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Cookie


load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "fallback_secret_key")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


def hash_password(password: str) -> str:
    """Превращает пароль в bcrypt-хеш."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет, совпадает ли введённый пароль с хешем."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def create_access_token(data: dict) -> str:
    """Создаёт JWT-токен с полезной нагрузкой data."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app import models

# Схема: "Bearer <token>" в заголовке Authorization
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> models.User:
    """
    Извлекает токен из заголовка Authorization,
    декодирует его и возвращает User из БД.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить токен",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception

    return user

def get_current_user_from_cookie(
    access_token: str | None = Cookie(None),
    db: Session = Depends(get_db),
) -> models.User | None:
    """
    Читает JWT из cookie. Возвращает User или None.
    В отличие от get_current_user, НЕ выбрасывает 401 —
    это позволяет страницам работать и без авторизации.
    """
    if not access_token:
        return None
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
    except jwt.PyJWTError:
        return None

    user = db.query(models.User).filter(models.User.username == username).first()
    return user


def get_current_user_flexible(
    access_token: str | None = Cookie(None),
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db),
) -> models.User:
    """Читает токен сначала из заголовка Authorization, потом из cookie."""
    token = None
    if credentials:
        token = credentials.credentials
    elif access_token:
        token = access_token
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(401, "Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")
    
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(401, "User not found")
    return user