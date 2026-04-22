"""Multi-channel message adapters."""

from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel
from enum import Enum
import asyncio


class Channel(str, Enum):
    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    SLACK = "slack"
    TEAMS = "teams"
    WEB = "web"


class ChannelMessage(BaseModel):
    channel: Channel
    message_id: str
    from_user: str
    to_user: str
    content: str
    attachments: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}


class ChannelConfig(BaseModel):
    channel: Channel
    enabled: bool = False
    config: dict[str, Any] = {}


class ChannelAdapter:
    """Base adapter interface."""

    async def send_message(self, message: ChannelMessage) -> dict[str, Any]:
        raise NotImplementedError

    async def receive_message(self, payload: dict[str, Any]) -> Optional[ChannelMessage]:
        raise NotImplementedError


class WhatsAppAdapter(ChannelAdapter):
    def __init__(self, phone_number_id: str = "", access_token: str = ""):
        self.phone_number_id = phone_number_id
        self.access_token = access_token

    async def send_message(self, message: ChannelMessage) -> dict[str, Any]:
        return {
            "messaging_product": "whatsapp",
            "to": message.to_user,
            "type": "text",
            "text": {"body": message.content},
        }

    async def receive_message(self, payload: dict[str, Any]) -> Optional[ChannelMessage]:
        entry = payload.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return None

        msg = messages[0]
        return ChannelMessage(
            channel=Channel.WHATSAPP,
            message_id=msg.get("id", ""),
            from_user=msg.get("from", ""),
            to_user=value.get("metadata", {}).get("phone_number_id", ""),
            content=msg.get("text", {}).get("body", ""),
        )


class TelegramAdapter(ChannelAdapter):
    def __init__(self, bot_token: str = ""):
        self.bot_token = bot_token

    async def send_message(self, message: ChannelMessage) -> dict[str, Any]:
        return {
            "chat_id": message.to_user,
            "text": message.content,
        }

    async def receive_message(self, payload: dict[str, Any]) -> Optional[ChannelMessage]:
        update = payload.get("message")
        if not update:
            return None

        return ChannelMessage(
            channel=Channel.TELEGRAM,
            message_id=str(update.get("message_id", "")),
            from_user=str(update.get("from", {}).get("id", "")),
            to_user=str(update.get("chat", {}).get("id", "")),
            content=update.get("text", ""),
        )


class SlackAdapter(ChannelAdapter):
    def __init__(self, bot_token: str = "", signing_secret: str = ""):
        self.bot_token = bot_token
        self.signing_secret = signing_secret

    async def send_message(self, message: ChannelMessage) -> dict[str, Any]:
        return {
            "channel": message.to_user,
            "text": message.content,
        }

    async def receive_message(self, payload: dict[str, Any]) -> Optional[ChannelMessage]:
        event = payload.get("event")
        if not event:
            return None

        return ChannelMessage(
            channel=Channel.SLACK,
            message_id=event.get("ts", ""),
            from_user=event.get("user", ""),
            to_user=event.get("channel", ""),
            content=event.get("text", ""),
        )


class TeamsAdapter(ChannelAdapter):
    def __init__(self, app_id: str = "", app_secret: str = ""):
        self.app_id = app_id
        self.app_secret = app_secret

    async def send_message(self, message: ChannelMessage) -> dict[str, Any]:
        return {
            "type": "message",
            "from": {"id": message.from_user, "name": "Bot"},
            "text": message.content,
        }

    async def receive_message(self, payload: dict[str, Any]) -> Optional[ChannelMessage]:
        activity = payload.get("activity")
        if not activity:
            return None

        from_user = activity.get("from", {})
        return ChannelMessage(
            channel=Channel.TEAMS,
            message_id=activity.get("id", ""),
            from_user=from_user.get("id", ""),
            to_user=activity.get("recipient", {}).get("id", ""),
            content=activity.get("text", ""),
        )


class ChannelDispatcher:
    def __init__(self):
        self._adapters: dict[Channel, ChannelAdapter] = {}
        self._configs: dict[str, ChannelConfig] = {}

    def register_adapter(self, channel: Channel, adapter: ChannelAdapter) -> None:
        self._adapters[channel] = adapter

    async def send_message(self, channel: Channel, message: ChannelMessage) -> dict[str, Any]:
        adapter = self._adapters.get(channel)
        if not adapter:
            raise ValueError(f"No adapter for channel: {channel}")
        return await adapter.send_message(message)

    async def normalize_message(
        self,
        channel: Channel,
        payload: dict[str, Any],
    ) -> Optional[ChannelMessage]:
        adapter = self._adapters.get(channel)
        if not adapter:
            return None
        return await adapter.receive_message(payload)


def get_channel_dispatcher() -> ChannelDispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = ChannelDispatcher()
    return _dispatcher


_dispatcher: Optional[ChannelDispatcher] = None