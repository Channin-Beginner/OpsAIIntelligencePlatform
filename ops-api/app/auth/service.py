from datetime import datetime, timedelta

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.exceptions import UnauthorizedError
from app.config import get_settings
from app.models.sys_user import SysUser
from app.schemas.common import LoginRequest, LoginResponse


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user_id: int, username: str, role: str) -> str:
    settings = get_settings()
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise UnauthorizedError()


def login(db: Session, body: LoginRequest) -> LoginResponse:
    user = db.scalar(select(SysUser).where(SysUser.username == body.username))
    if user is None or not user.is_active:
        raise UnauthorizedError(message="用户名或密码错误")
    if not verify_password(body.password, user.password_hash):
        raise UnauthorizedError(message="用户名或密码错误")

    token = create_access_token(user.id, user.username, user.role)
    return LoginResponse(
        access_token=token,
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
    )


def get_user_from_token(db: Session, token: str) -> SysUser:
    payload = decode_token(token)
    user_id = int(payload.get("sub", 0))
    user = db.get(SysUser, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError()
    return user
