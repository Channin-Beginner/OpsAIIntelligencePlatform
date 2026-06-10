from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.service import login
from app.common.response import success
from app.database import get_db
from app.schemas.common import LoginRequest

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post("/login")
def post_login(
    body: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
):
    result = login(db, body)
    return success(data=result.model_dump())
