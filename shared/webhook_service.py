from typing import Any, Callable
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
import hashlib
import hmac
import asyncio
import json


class WebhookEventType(str, Enum):
    CONVERSATION_CREATED = "conversation.created"
    CONVERSATION_RESOLVED = "conversation.resolved"
    CONVERSATION_ESCALATED = "conversation.escalated"
    MESSAGE_RECEIVED = "message.received"
    MESSAGE_SENT = "message.sent"
    HITL_REQUESTED = "hitl.requested"
    HITL_TAKEN = "hitl.taken"
    HITL_COMPLETED = "hitl.completed"
    BILLING_LIMIT_EXCEEDED = "billing.limit_exceeded"
    BILLING_PAYMENT_FAILED = "billing.payment_failed"
    FEEDBACK_RECEIVED = "feedback.received"


class WebhookConfig(BaseModel):
    id: str
    tenant_id: str
    url: str
    secret_key: str
    event_types: list[str]
    enabled: bool = True
    transform_template: str | None = None
    retry_policy: dict[str, Any] = {"max_attempts": 3, "backoff": "exponential"}


class WebhookDelivery(BaseModel):
    id: str
    webhook_id: str
    event_type: str
    payload: dict[str, Any]
    status: str = "pending"
    attempts: int = 0
    last_attempt_at: datetime | None = None
    error: str | None = None
    response_code: int | None = None
    created_at: datetime


class WebhookService:
    def __init__(self, db_pool=None, redis_client=None):
        self.db = db_pool
        self.redis = redis_client
        self._webhooks: dict[str, WebhookConfig] = {}
        self._delivery_queue: asyncio.Queue = asyncio.Queue()
        self._event_handlers: dict[str, list[Callable]] = {}

    async def create_webhook(
        self,
        tenant_id: str,
        url: str,
        secret_key: str,
        event_types: list[str],
    ) -> WebhookConfig:
        webhook = WebhookConfig(
            id=f"wh_{datetime.now().timestamp()}",
            tenant_id=tenant_id,
            url=url,
            secret_key=secret_key,
            event_types=event_types,
        )
        self._webhooks[webhook.id] = webhook
        await self._persist_webhook(webhook)
        return webhook

    async def delete_webhook(self, webhook_id: str) -> bool:
        if webhook_id in self._webhooks:
            del self._webhooks[webhook_id]
            await self._delete_webhook_from_db(webhook_id)
            return True
        return False

    async def list_webhooks(self, tenant_id: str) -> list[WebhookConfig]:
        return [w for w in self._webhooks.values() if w.tenant_id == tenant_id]

    def verify_signature(self, payload: str, signature: str, secret: str) -> bool:
        expected = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def emit_event(
        self,
        tenant_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        webhooks = await self.list_webhooks(tenant_id)
        
        for webhook in webhooks:
            if webhook.enabled and event_type in webhook.event_types:
                await self._queue_delivery(webhook, event_type, payload)

    async def deliver_pending(self) -> None:
        while not self._delivery_queue.empty():
            delivery = await self._delivery_queue.get()
            await self._execute_delivery(delivery)

    async def _queue_delivery(
        self,
        webhook: WebhookConfig,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        delivery = WebhookDelivery(
            id=f"del_{datetime.now().timestamp()}",
            webhook_id=webhook.id,
            event_type=event_type,
            payload=payload,
        )
        await self._delivery_queue.put(delivery)

    async def _execute_delivery(self, delivery: WebhookDelivery) -> None:
        webhook = self._webhooks.get(delivery.webhook_id)
        if not webhook:
            return
        
        payload_json = json.dumps(delivery.payload)
        signature = hmac.new(
            webhook.secret_key.encode(),
            payload_json.encode(),
            hashlib.sha256,
        ).hexdigest()
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    webhook.url,
                    json=json.loads(payload_json),
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": signature,
                        "X-Event-Type": delivery.event_type,
                    },
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    delivery.response_code = resp.status
                    delivery.status = "success" if resp.status < 400 else "failed"
        except Exception as e:
            delivery.status = "failed"
            delivery.error = str(e)
        
        delivery.attempts += 1
        delivery.last_attempt_at = datetime.now()
        
        if delivery.status == "failed" and delivery.attempts < 3:
            await self._retry_delivery(delivery)
        else:
            await self._persist_delivery(delivery)

    async def _retry_delivery(self, delivery: WebhookDelivery) -> None:
        backoff = 2 ** delivery.attempts
        await asyncio.sleep(backoff)
        await self._delivery_queue.put(delivery)

    async def _persist_webhook(self, webhook: WebhookConfig) -> None:
        pass

    async def _delete_webhook_from_db(self, webhook_id: str) -> None:
        pass

    async def _persist_delivery(self, delivery: WebhookDelivery) -> None:
        pass


_global_webhook_service: WebhookService | None = None


def get_webhook_service() -> WebhookService:
    global _global_webhook_service
    if _global_webhook_service is None:
        _global_webhook_service = WebhookService()
    return _global_webhook_service