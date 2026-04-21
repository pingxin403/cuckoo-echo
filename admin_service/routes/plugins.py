"""Admin Plugin Management API routes."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from shared.plugin_system import (
    PluginManifest,
    get_plugin_registry,
    load_plugin_from_manifest,
    load_plugin_module,
)

log = structlog.get_logger()
router = APIRouter(prefix="/admin/v1/plugins")


class PluginEnableRequest(BaseModel):
    enabled: bool


class PluginInstallRequest(BaseModel):
    name: str
    version: str
    plugin_type: str
    description: str
    entry: str
    permissions: list[str] = []


@router.get("")
async def list_plugins(request: Request):
    """List all registered plugins."""
    registry = get_plugin_registry()
    plugins = registry.list_plugins()

    return [
        {
            "name": p.name,
            "version": p.version,
            "type": p.plugin_type,
            "description": p.description,
            "permissions": p.permissions,
            "author": p.author,
        }
        for p in plugins
    ]


@router.post("")
async def install_plugin(body: PluginInstallRequest, request: Request):
    """Install a new plugin."""
    tenant_id = request.state.tenant_id

    manifest = PluginManifest(
        name=body.name,
        version=body.version,
        plugin_type=body.plugin_type,
        description=body.description,
        entry=body.entry,
        permissions=body.permissions,
        tenant_id=tenant_id,
    )

    registry = get_plugin_registry()

    dummy_module = type("PluginModule", (), {})()
    if hasattr(dummy_module, "register_tools"):
        pass

    registry.register(manifest, dummy_module)

    log.info("plugin_installed", name=body.name, tenant_id=tenant_id)
    return {"installed": True, "name": body.name}


@router.post("/{plugin_name}/enable")
async def toggle_plugin(plugin_name: str, body: PluginEnableRequest, request: Request):
    """Enable or disable a plugin."""
    registry = get_plugin_registry()

    if body.enabled:
        success = registry.enable(plugin_name)
    else:
        success = registry.disable(plugin_name)

    if not success:
        raise HTTPException(status_code=404, detail="Plugin not found")

    return {"name": plugin_name, "enabled": body.enabled}


@router.delete("/{plugin_name}")
async def uninstall_plugin(plugin_name: str, request: Request):
    """Uninstall a plugin."""
    registry = get_plugin_registry()

    if plugin_name not in [p.name for p in registry.list_plugins()]:
        raise HTTPException(status_code=404, detail="Plugin not found")

    disabled = registry.disable(plugin_name)
    del registry._plugins[plugin_name]

    log.info("plugin_uninstalled", name=plugin_name)
    return {"uninstalled": True, "name": plugin_name}


@router.get("/tools")
async def list_plugin_tools(request: Request):
    """List all registered plugin tools."""
    registry = get_plugin_registry()
    tools = list(registry._tools.keys())

    return {"tools": tools}


@router.post("/tools/{tool_name}/execute")
async def execute_plugin_tool(
    tool_name: str,
    request: Request,
    params: dict | None = None,
):
    """Execute a plugin tool."""
    from shared.plugin_system import execute_tool

    try:
        result = await execute_tool(tool_name, **(params or {}))
        return {"result": result}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))