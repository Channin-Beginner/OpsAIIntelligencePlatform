from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.alerts.service import process_grafana_webhook
from app.common.response import success
from app.database import get_db
from app.schemas.common import AlertmanagerWebhookPayload

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/grafana")
def post_grafana_webhook(
    db: Annotated[Session, Depends(get_db)],
    payload: AlertmanagerWebhookPayload,
):
    """
    接收 Grafana Unified Alerting Webhook。

    Grafana Contact Point 选用 Alertmanager 兼容 JSON 格式，
    写入 alert_event.source=grafana 并复用 Alert Center 归并逻辑。
    """
    result = process_grafana_webhook(db, payload)
    return success(data=result.model_dump())
