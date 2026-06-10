from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.service import get_user_from_token
from app.database import get_db
from app.models.sys_user import SysUser

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> SysUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        from app.common.exceptions import UnauthorizedError

        raise UnauthorizedError()
    return get_user_from_token(db, credentials.credentials)
