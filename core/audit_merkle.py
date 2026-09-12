"""
core/audit_merkle.py

Cryptographically verifiable, append-only Merkle DAG audit logger for
industrial compliance in air-gapped sovereign refinery operations (SIH26117).
Every prompt, tool execution, model inference, and document clearance check
is chained via SHA-256 cryptographic hashes for non-repudiation and forensic audits.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_AUDIT_LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "audit_trail.jsonl",
)
GENESIS_PREV_HASH = "0" * 64


def _canonical_json(data: Any) -> str:
    """Produce deterministic JSON string representation for hashing."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256(content: str) -> str:
    """Compute hex SHA-256 digest of a UTF-8 string."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class MerkleAuditLog:
    """Thread-safe, append-only cryptographic audit logger."""

    def __init__(self, log_path: str = DEFAULT_AUDIT_LOG_PATH):
        self.log_path = log_path
        self._lock = threading.Lock()
        self._ensure_log_dir()
        self._last_block: Optional[Dict[str, Any]] = self._read_last_block()

    def _ensure_log_dir(self) -> None:
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def _read_last_block(self) -> Optional[Dict[str, Any]]:
        """Read the last block from the append-only log file."""
        if not os.path.exists(self.log_path):
            return None
        last_line = ""
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        last_line = line
            if last_line:
                return json.loads(last_line)
        except Exception as e:
            logger.error(f"Error reading audit log tail: {e}")
        return None

    def record_event(
        self,
        user: str,
        department: str,
        action: str,
        details: Dict[str, Any],
        egress_status: str = "0-WAN_VERIFIED_INTERNAL",
    ) -> Dict[str, Any]:
        """Record an event, cryptographically chained to the previous block."""
        with self._lock:
            now_iso = datetime.now(timezone.utc).isoformat()
            if self._last_block is None:
                index = 0
                prev_hash = GENESIS_PREV_HASH
            else:
                index = int(self._last_block.get("index", -1)) + 1
                prev_hash = str(self._last_block.get("hash", GENESIS_PREV_HASH))

            payload_to_hash = {
                "index": index,
                "timestamp": now_iso,
                "prev_hash": prev_hash,
                "user": user or "anonymous",
                "department": department or "UNASSIGNED",
                "action": action,
                "details": details,
                "egress_status": egress_status,
            }

            block_hash = _sha256(_canonical_json(payload_to_hash))
            block = dict(payload_to_hash)
            block["hash"] = block_hash

            # Atomic append to audit file
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(block) + "\n")

            self._last_block = block
            return block

    def verify_audit_chain(self) -> Tuple[bool, List[str]]:
        """Verify the cryptographic integrity of the entire audit chain.

        Returns (is_valid, list_of_discrepancies).
        """
        with self._lock:
            if not os.path.exists(self.log_path):
                return True, []

            issues = []
            expected_prev_hash = GENESIS_PREV_HASH
            expected_index = 0

            with open(self.log_path, "r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        block = json.loads(line)
                    except json.JSONDecodeError:
                        issues.append(f"Line {line_no}: Invalid JSON formatting.")
                        continue

                    idx = block.get("index")
                    prev_hash = block.get("prev_hash")
                    stored_hash = block.get("hash")

                    if idx != expected_index:
                        issues.append(
                            f"Line {line_no}: Index mismatch. Expected {expected_index}, got {idx}."
                        )

                    if prev_hash != expected_prev_hash:
                        issues.append(
                            f"Line {line_no} (Index {idx}): Prev hash mismatch. "
                            f"Expected {expected_prev_hash}, got {prev_hash} (Chain broken!)."
                        )

                    # Recompute hash
                    recomputed_payload = {
                        "index": idx,
                        "timestamp": block.get("timestamp"),
                        "prev_hash": prev_hash,
                        "user": block.get("user"),
                        "department": block.get("department"),
                        "action": block.get("action"),
                        "details": block.get("details"),
                        "egress_status": block.get("egress_status"),
                    }
                    expected_hash = _sha256(_canonical_json(recomputed_payload))
                    if stored_hash != expected_hash:
                        issues.append(
                            f"Line {line_no} (Index {idx}): Tampered block hash! "
                            f"Expected {expected_hash}, got {stored_hash}."
                        )

                    expected_prev_hash = stored_hash
                    expected_index = idx + 1

            is_valid = len(issues) == 0
            return is_valid, issues

    def get_all_blocks(self) -> List[Dict[str, Any]]:
        """Retrieve all audit blocks in chronological order."""
        with self._lock:
            if not os.path.exists(self.log_path):
                return []
            blocks: List[Dict[str, Any]] = []
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            blocks.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            return blocks

    def get_recent_blocks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent audit blocks in chronological order (tail of log)."""
        with self._lock:
            if not os.path.exists(self.log_path):
                return []
            blocks: List[Dict[str, Any]] = []
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            blocks.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            return blocks[-limit:] if limit > 0 else blocks

    def compute_merkle_root(
        self,
        hashes: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> str:
        """Compute the Merkle root hash for block hashes.

        If hashes is None, computes across all blocks (or up to limit if specified).
        """
        if hashes is None:
            blocks = self.get_recent_blocks(limit=limit) if limit else self.get_all_blocks()
            hashes = [b["hash"] for b in blocks if "hash" in b]

        if not hashes:
            return GENESIS_PREV_HASH

        current_level = list(hashes)
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                combined = _sha256(left + right)
                next_level.append(combined)
            current_level = next_level

        return current_level[0]

    def get_stats(self) -> Dict[str, Any]:
        """Return cryptographic audit statistics and tamper check status."""
        is_valid, issues = self.verify_audit_chain()
        all_blocks = self.get_all_blocks()
        total_blocks = len(all_blocks)
        last_block = all_blocks[-1] if all_blocks else None
        merkle_root = self.compute_merkle_root()

        return {
            "total_blocks": total_blocks,
            "genesis_hash": GENESIS_PREV_HASH,
            "merkle_root": merkle_root,
            "last_block_hash": last_block.get("hash") if last_block else GENESIS_PREV_HASH,
            "last_block_index": last_block.get("index") if last_block else -1,
            "last_timestamp": last_block.get("timestamp") if last_block else None,
            "is_valid": is_valid,
            "discrepancies": issues,
            "egress_status": "0-WAN_VERIFIED_INTERNAL",
            "compliance_status": "CERTIFIED_TAMPER_EVIDENT" if is_valid else "TAMPERING_DETECTED",
        }

    def export_chain(self) -> str:
        """Export the entire audit chain as JSONL text."""
        with self._lock:
            if not os.path.exists(self.log_path):
                return ""
            with open(self.log_path, "r", encoding="utf-8") as f:
                return f.read()


# Singleton instance
_audit_log_instance: Optional[MerkleAuditLog] = None
_audit_log_init_lock = threading.Lock()


def get_audit_log() -> MerkleAuditLog:
    """Return the global MerkleAuditLog singleton."""
    global _audit_log_instance
    if _audit_log_instance is None:
        with _audit_log_init_lock:
            if _audit_log_instance is None:
                _audit_log_instance = MerkleAuditLog()
    return _audit_log_instance
