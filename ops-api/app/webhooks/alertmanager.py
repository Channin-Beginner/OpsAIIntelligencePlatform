from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.alerts.service import process_alertmanager_webhook
from app.common.response import success
from app.database import get_db
from app.schemas.common import AlertmanagerWebhookPayload

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/alertmanager")
def post_alertmanager_webhook(
    db: Annotated[Session, Depends(get_db)],
    payload: AlertmanagerWebhookPayload,
):
    result = process_alertmanager_webhook(db, payload)
    return success(data=result.model_dump())
