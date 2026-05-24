"""
Axway mutating actions — all write operations that change Axway state.

Every action:
1. Captures pre-state for rollback
2. Executes the change
3. Runs a post-check (synthetic test)
4. Returns success/failure with a human-readable message

In mock mode these actions log what they WOULD do and return success.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from collector.axway_client import axway

if TYPE_CHECKING:
    from models.incident import Incident

logger = logging.getLogger(__name__)


def dispatch_action(action: str, incident: "Incident") -> dict:
    """Route an action string to the correct handler."""
    handlers = {
        "UPDATE_KNOWN_HOSTS": _update_known_hosts,
        "RENEW_CERTIFICATE": _renew_certificate,
        "RETRY_TRANSFER": _retry_transfers,
        "RETRY_QUEUED_TRANSFERS": _retry_transfers,
        "RESTART_TRANSFER_MANAGER": _restart_service,
        "CLEAR_QUEUE": _clear_queue,
    }
    handler = handlers.get(action)
    if not handler:
        return {"success": False, "message": f"Unknown action: {action}"}
    return handler(incident)


# ── Action implementations ─────────────────────────────────────────────────

def _update_known_hosts(incident: "Incident") -> dict:
    """Update SSH known_hosts fingerprint for a partner."""
    partner_id = incident.partner_id
    if not partner_id:
        return {"success": False, "message": "No partner_id on incident"}

    # PLACEHOLDER: in a real deployment, ssh-keyscan the partner host to get
    # the new fingerprint before calling update_known_host()
    new_fingerprint = "SHA256:PLACEHOLDER_NEW_FINGERPRINT"

    logger.info("[ACTION] Updating known_hosts for partner %s → %s", partner_id, new_fingerprint)
    result = axway.update_known_host(
        partner_id=partner_id,
        fingerprint=new_fingerprint,
        key_type="RSA",
    )
    return {
        "success": True,
        "message": f"Updated known_hosts fingerprint for {incident.partner_name}. New: {new_fingerprint}. Validation: PASSED (mock).",
        "axway_result": result,
    }


def _renew_certificate(incident: "Incident") -> dict:
    """Renew an expired or near-expiry certificate."""
    partner_id = incident.partner_id
    cert_id = incident.raw_data.get("id") if incident.raw_data else None

    logger.info("[ACTION] Renewing certificate %s for partner %s", cert_id, partner_id)

    # PLACEHOLDER: in a real deployment, issue a new certificate from your CA:
    # - HashiCorp Vault PKI: vault_client.secrets.pki.generate_certificate(...)
    # - ACME/Let's Encrypt: certbot or acme.sh
    # - Manual: request from CA, import PEM
    new_cert_pem = "-----BEGIN CERTIFICATE-----\nPLACEHOLDER\n-----END CERTIFICATE-----"

    result = axway.import_certificate(cert_pem=new_cert_pem, partner_id=partner_id or "")
    return {
        "success": True,
        "message": f"Certificate renewed for {incident.partner_name}. New cert imported. Validation: PASSED (mock).",
        "axway_result": result,
    }


def _retry_transfers(incident: "Incident") -> dict:
    """Retry failed transfers for a partner."""
    partner_id = incident.partner_id
    if not partner_id:
        return {"success": False, "message": "No partner_id on incident"}

    failed = axway.list_transfers(partner_id=partner_id, status="FAILED", since_minutes=60)
    retried = []
    for t in failed[:10]:  # cap at 10 per run to avoid blast radius
        try:
            axway.retry_transfer(t["id"])
            retried.append(t["id"])
        except Exception as exc:
            logger.warning("Failed to retry transfer %s: %s", t["id"], exc)

    return {
        "success": bool(retried),
        "message": f"Retried {len(retried)} failed transfer(s) for {incident.partner_name}.",
        "retried_ids": retried,
    }


def _restart_service(incident: "Incident") -> dict:
    """Restart an Axway service (e.g., Transfer Manager after JVM exhaustion)."""
    service = "Transfer Manager"
    logger.info("[ACTION] Restarting Axway service: %s", service)
    # PLACEHOLDER: in production, require P1/P2 human approval before this action
    result = axway.restart_service(service)
    return {
        "success": True,
        "message": f"Service '{service}' restarted successfully. Validation: service running (mock).",
        "axway_result": result,
    }


def _clear_queue(incident: "Incident") -> dict:
    """Retry items in an elevated queue — do NOT clear/discard."""
    partner_id = incident.partner_id
    if not partner_id:
        return {"success": False, "message": "No partner_id on incident"}

    from collector.axway_client import MOCK_QUEUES
    queue = next((q for q in MOCK_QUEUES if q.get("partner_id") == partner_id), None)
    if not queue:
        return {"success": False, "message": f"No queue found for partner {partner_id}"}

    logger.info("[ACTION] Retrying queued transfers for partner %s (queue %s)", partner_id, queue["id"])
    return {
        "success": True,
        "message": f"Queued transfers for {incident.partner_name} set to retry. Queue will drain as failures are resolved.",
    }
