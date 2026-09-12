"""
routes/audit_routes.py

Cryptographic Merkle DAG Audit Trail API endpoints for air-gapped sovereign
refinery compliance and forensic verification (SIH26117).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel

from core.audit_merkle import get_audit_log

logger = logging.getLogger(__name__)


class RecordEventRequest(BaseModel):
    action: str
    details: Dict[str, Any]
    department: Optional[str] = None
    egress_status: Optional[str] = "0-WAN_VERIFIED_INTERNAL"


def setup_audit_routes(auth_manager=None) -> APIRouter:
    router = APIRouter(prefix="/api/audit", tags=["audit"])

    def _get_user(request: Request) -> str:
        user = getattr(request.state, "current_user", None)
        return user or "anonymous"

    def _get_dept(username: str) -> str:
        if auth_manager and hasattr(auth_manager, "get_user_department"):
            return auth_manager.get_user_department(username)
        return "GENERAL_OPERATIONS"

    @router.get("/stats")
    async def get_audit_stats(request: Request) -> Dict[str, Any]:
        """Return cryptographic audit trail status, block count, and Merkle root."""
        try:
            stats = get_audit_log().get_stats()
            user = _get_user(request)
            stats["caller_department"] = _get_dept(user)
            return stats
        except Exception as e:
            logger.error(f"Error fetching audit stats: {e}")
            raise HTTPException(500, f"Failed to retrieve audit stats: {str(e)}")

    @router.get("/blocks")
    async def get_audit_blocks(
        request: Request,
        limit: int = Query(50, ge=1, le=500),
    ) -> Dict[str, Any]:
        """Retrieve recent cryptographically chained audit blocks."""
        try:
            blocks = get_audit_log().get_recent_blocks(limit=limit)
            return {
                "blocks": blocks,
                "count": len(blocks),
                "merkle_root": get_audit_log().compute_merkle_root(),
                "egress_status": "0-WAN_VERIFIED_INTERNAL",
            }
        except Exception as e:
            logger.error(f"Error fetching audit blocks: {e}")
            raise HTTPException(500, f"Failed to retrieve audit blocks: {str(e)}")

    @router.get("/verify")
    async def verify_audit_trail(request: Request) -> Dict[str, Any]:
        """Verify the cryptographic integrity and non-repudiation of the entire audit chain."""
        try:
            is_valid, issues = get_audit_log().verify_audit_chain()
            root = get_audit_log().compute_merkle_root()
            all_blocks = get_audit_log().get_all_blocks()
            return {
                "is_valid": is_valid,
                "discrepancies": issues,
                "merkle_root": root,
                "total_blocks_verified": len(all_blocks),
                "compliance_status": "CERTIFIED_TAMPER_EVIDENT" if is_valid else "TAMPERING_DETECTED",
                "egress_status": "0-WAN_VERIFIED_INTERNAL",
            }
        except Exception as e:
            logger.error(f"Error verifying audit trail: {e}")
            raise HTTPException(500, f"Audit verification failed: {str(e)}")

    @router.get("/root")
    async def get_merkle_root() -> Dict[str, str]:
        """Get the current SHA-256 Merkle root digest for sovereign forensic compliance."""
        try:
            return {"merkle_root": get_audit_log().compute_merkle_root()}
        except Exception as e:
            logger.error(f"Error computing Merkle root: {e}")
            raise HTTPException(500, f"Failed to compute Merkle root: {str(e)}")

    @router.post("/record")
    async def record_compliance_event(
        body: RecordEventRequest,
        request: Request,
    ) -> Dict[str, Any]:
        """Record a custom industrial compliance or operational event into the Merkle DAG."""
        user = _get_user(request)
        dept = body.department or _get_dept(user)
        try:
            block = get_audit_log().record_event(
                user=user,
                department=dept,
                action=body.action,
                details=body.details,
                egress_status=body.egress_status or "0-WAN_VERIFIED_INTERNAL",
            )
            return {"ok": True, "block": block}
        except Exception as e:
            logger.error(f"Error recording audit event: {e}")
            raise HTTPException(500, f"Failed to record audit event: {str(e)}")

    @router.get("/export")
    async def export_audit_trail(request: Request) -> Response:
        """Export the complete audit chain for PSU/statutory compliance archival."""
        try:
            content = get_audit_log().export_chain()
            return Response(
                content=content,
                media_type="application/x-ndjson",
                headers={"Content-Disposition": "attachment; filename=odin_merkle_audit_trail.jsonl"},
            )
        except Exception as e:
            logger.error(f"Error exporting audit trail: {e}")
            raise HTTPException(500, f"Failed to export audit trail: {str(e)}")

    return router
