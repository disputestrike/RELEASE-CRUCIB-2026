"""Ecosystem routes — VS Code extension config and code generation."""

from __future__ import annotations

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ecosystem"])


@router.get("/ecosystem/vscode/config")
async def ecosystem_vscode_config():
    from ecosystem_integration import ecosystem_manager

    config = ecosystem_manager.vscode.generate_extension_config()
    return {
        "status": "success",
        "extension_id": ecosystem_manager.vscode.extension_id,
        "version": ecosystem_manager.vscode.version,
        "config": config,
    }


@router.get("/ecosystem/vscode/extension-code")
async def ecosystem_vscode_extension_code():
    from ecosystem_integration import ecosystem_manager

    code = ecosystem_manager.vscode.generate_extension_code()
    return {"status": "success", "code": code}
