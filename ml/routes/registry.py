"""
API routes for Model Registry management.

Exposes endpoints for listing versions, querying active models, triggering
promotions/rollbacks, and comparing model performance metrics.
"""

from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query

import model_registry
from logger import get_logger, log_event

router = APIRouter(prefix="/api/ml/models", tags=["registry"])
_logger = get_logger("routes.registry")

_registry_instance: Optional[model_registry.ModelRegistry] = None


def set_global_registry(registry: model_registry.ModelRegistry) -> None:
    """Set the global ModelRegistry instance."""
    global _registry_instance
    _registry_instance = registry


def get_global_registry() -> model_registry.ModelRegistry:
    """Get the global ModelRegistry instance or instantiate default."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = model_registry.ModelRegistry()
    return _registry_instance


@router.get("")
async def list_models() -> dict[str, Any]:
    """List all registered model versions and manifest summary."""
    try:
        reg = get_global_registry()
        manifest = reg.get_manifest()
        return {
            "active_version": manifest.active_version,
            "previous_version": manifest.previous_version,
            "total_versions": len(manifest.versions),
            "versions": [v.model_dump() for v in manifest.versions.values()],
        }
    except Exception as exc:
        log_event(_logger, action="list_models_error", error=str(exc))
        raise HTTPException(
            status_code=500, detail=f"Failed to list models: {exc}"
        ) from exc


@router.get("/active")
async def get_active_model_info() -> dict[str, Any]:
    """Retrieve metadata of the currently active production model."""
    try:
        reg = get_global_registry()
        _, meta = reg.get_active()
        return {
            "status": "active",
            "metadata": meta.model_dump(),
        }
    except Exception as exc:
        log_event(_logger, action="get_active_model_error", error=str(exc))
        raise HTTPException(
            status_code=404, detail=f"No active model available: {exc}"
        ) from exc


@router.get("/compare")
async def compare_models(
    v1: str = Query(..., description="First version tag (e.g. v1)"),
    v2: str = Query(..., description="Second version tag (e.g. v2)"),
) -> dict[str, Any]:
    """Compare performance metrics between two model versions."""
    try:
        reg = get_global_registry()
        comparison = reg.compare(v1, v2)
        return comparison
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        log_event(_logger, action="compare_models_error", error=str(exc))
        raise HTTPException(
            status_code=500, detail=f"Failed to compare models: {exc}"
        ) from exc


@router.get("/{version}")
async def get_model_version(version: str) -> dict[str, Any]:
    """Get metadata for a specific model version."""
    reg = get_global_registry()
    meta = reg.get_version_metadata(version)
    if not meta:
        raise HTTPException(
            status_code=404, detail=f"Model version {version} not found"
        )
    return meta.model_dump()


@router.post("/{version}/promote")
async def promote_model_version(version: str) -> dict[str, Any]:
    """Promote a specific model version to active production status."""
    try:
        reg = get_global_registry()
        success = reg.promote(version)
        if not success:
            raise HTTPException(
                status_code=400, detail=f"Failed to promote version {version}"
            )
        return {
            "status": "promoted",
            "version": version,
            "message": f"Version {version} is now active in production.",
        }
    except HTTPException:
        raise
    except Exception as exc:
        log_event(_logger, action="promote_model_error", error=str(exc))
        raise HTTPException(
            status_code=500, detail=f"Promotion failed: {exc}"
        ) from exc


@router.post("/rollback")
async def rollback_model() -> dict[str, Any]:
    """Roll back active model to the previously active version."""
    try:
        reg = get_global_registry()
        restored = reg.rollback()
        if not restored:
            raise HTTPException(
                status_code=400,
                detail="Rollback failed: No previous version available.",
            )
        return {
            "status": "rolled_back",
            "active_version": restored,
            "message": f"Successfully rolled back to version {restored}.",
        }
    except HTTPException:
        raise
    except Exception as exc:
        log_event(_logger, action="rollback_model_error", error=str(exc))
        raise HTTPException(
            status_code=500, detail=f"Rollback failed: {exc}"
        ) from exc
