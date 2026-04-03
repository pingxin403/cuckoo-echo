"""Order management tools with configurable backend."""
from __future__ import annotations

import structlog

from chat_service.agent.tools.registry import register_tool
from shared.config import get_settings

log = structlog.get_logger()


class OrderServiceClient:
    """Configurable order service client — supports real HTTP API and mock mode."""

    def __init__(self, base_url: str = "", mock_mode: bool = True):
        self.base_url = base_url
        self.mock_mode = mock_mode

    async def get_order_status(self, order_id: str, tenant_id: str) -> dict:
        if self.mock_mode:
            return self._mock_order_status(order_id, tenant_id)
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/orders/{order_id}",
                headers={"X-Tenant-ID": tenant_id},
                timeout=5.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def update_shipping_address(
        self, order_id: str, address: str, tenant_id: str
    ) -> dict:
        if self.mock_mode:
            return self._mock_update_address(order_id, address, tenant_id)
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.put(
                f"{self.base_url}/orders/{order_id}/address",
                json={"address": address},
                headers={"X-Tenant-ID": tenant_id},
                timeout=5.0,
            )
            resp.raise_for_status()
            return resp.json()

    def _mock_order_status(self, order_id: str, tenant_id: str) -> dict:
        return {
            "order_id": order_id,
            "tenant_id": tenant_id,
            "status": "shipped",
            "tracking_number": "SF1234567890",
            "estimated_delivery": "2026-04-05",
        }

    def _mock_update_address(
        self, order_id: str, address: str, tenant_id: str
    ) -> dict:
        return {
            "order_id": order_id,
            "tenant_id": tenant_id,
            "new_address": address,
            "updated": True,
        }


# Module-level instance — configurable via Settings
_settings = get_settings()
_client = OrderServiceClient(
    base_url=getattr(_settings, "tool_order_service_url", ""),
    mock_mode=getattr(_settings, "tool_mock_mode", True),
)


@register_tool("get_order_status", description="Query order status by order ID")
async def get_order_status(order_id: str, tenant_id: str) -> dict:
    """Query order status. tenant_id included in every outbound request."""
    log.info("get_order_status", order_id=order_id, tenant_id=tenant_id)
    return await _client.get_order_status(order_id, tenant_id)


@register_tool(
    "update_shipping_address", description="Update shipping address for an order"
)
async def update_shipping_address(
    order_id: str, address: str, tenant_id: str
) -> dict:
    """Update shipping address. tenant_id included in every outbound request."""
    log.info("update_shipping_address", order_id=order_id, tenant_id=tenant_id)
    return await _client.update_shipping_address(order_id, address, tenant_id)
