"""
Axway SecureTransport API client.

When settings.mock_axway is True (default), all methods return realistic
demo data so the app runs without a live Axway instance.

When mock_axway is False, each method calls the real Axway Admin REST API
at https://<host>:444/api/v1.4 — replace the PLACEHOLDER comments below
with your actual endpoint paths once you have API access.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from config.settings import settings

# ── Mock data ──────────────────────────────────────────────────────────────

_NOW = lambda: datetime.now(timezone.utc)  # noqa: E731

MOCK_PARTNERS: list[dict] = [
    {
        "id": "ACME-001", "name": "Acme Corp", "protocol": "SFTP",
        "sla_tier": "GOLD", "host": "sftp.acme.com", "port": 22,
        "active": True, "expected_transfer_interval_hours": 4,
    },
    {
        "id": "GLOBEX-002", "name": "Globex Industries", "protocol": "AS2",
        "sla_tier": "PLATINUM", "as2_url": "http://as2.globex.com:4080/as2",
        "active": True, "expected_transfer_interval_hours": 2,
    },
    {
        "id": "INITECH-003", "name": "Initech LLC", "protocol": "HTTPS",
        "sla_tier": "SILVER", "api_url": "https://api.initech.com/files",
        "active": True, "expected_transfer_interval_hours": 24,
    },
    {
        "id": "UMBRELLA-004", "name": "Umbrella Corp", "protocol": "SFTP",
        "sla_tier": "GOLD", "host": "sftp.umbrella.com", "port": 22,
        "active": True, "expected_transfer_interval_hours": 6,
    },
    {
        "id": "WAYNE-005", "name": "Wayne Enterprises", "protocol": "FTPS",
        "sla_tier": "PLATINUM", "host": "ftps.wayne.com", "port": 990,
        "active": True, "expected_transfer_interval_hours": 1,
    },
]

MOCK_CERTIFICATES: list[dict] = [
    {
        "id": "CERT-001", "common_name": "sftp.acme.com", "partner_id": "ACME-001",
        "partner_name": "Acme Corp", "subject": "CN=sftp.acme.com, O=Acme Corp, C=US",
        "issuer": "CN=DigiCert TLS RSA SHA256 2020 CA1", "algorithm": "SHA256withRSA",
        "key_size": 2048, "days_until_expiry": 7, "status": "ACTIVE",
    },
    {
        "id": "CERT-002", "common_name": "ftps.wayne.com", "partner_id": "WAYNE-005",
        "partner_name": "Wayne Enterprises", "subject": "CN=ftps.wayne.com, O=Wayne Enterprises",
        "issuer": "CN=Sectigo RSA Domain Validation Secure Server CA", "algorithm": "SHA256withRSA",
        "key_size": 2048, "days_until_expiry": 14, "status": "ACTIVE",
    },
    {
        "id": "CERT-003", "common_name": "api.initech.com", "partner_id": "INITECH-003",
        "partner_name": "Initech LLC", "subject": "CN=api.initech.com, O=Initech LLC",
        "issuer": "CN=Let's Encrypt Authority X3", "algorithm": "SHA256withRSA",
        "key_size": 2048, "days_until_expiry": 78, "status": "ACTIVE",
    },
    {
        "id": "CERT-004", "common_name": "as2.globex.com", "partner_id": "GLOBEX-002",
        "partner_name": "Globex Industries", "subject": "CN=as2.globex.com",
        "issuer": "CN=GlobalSign RSA OV SSL CA 2018", "algorithm": "SHA256withRSA",
        "key_size": 4096, "days_until_expiry": 312, "status": "ACTIVE",
    },
    {
        "id": "CERT-005", "common_name": "sftp.umbrella.com", "partner_id": "UMBRELLA-004",
        "partner_name": "Umbrella Corp", "subject": "CN=sftp.umbrella.com, O=Umbrella Corp",
        "issuer": "CN=DigiCert TLS RSA SHA256 2020 CA1", "algorithm": "SHA256withRSA",
        "key_size": 2048, "days_until_expiry": 245, "status": "ACTIVE",
    },
]

MOCK_SSH_KEYS: list[dict] = [
    {
        "id": "KEY-001", "partner_id": "ACME-001", "partner_name": "Acme Corp",
        "key_type": "RSA", "key_size": 2048, "fingerprint": "SHA256:oldAcmeKey/abc123",
        "age_days": 730, "status": "ACTIVE", "algorithm": "ssh-rsa",
    },
    {
        "id": "KEY-002", "partner_id": "UMBRELLA-004", "partner_name": "Umbrella Corp",
        "key_type": "ECDSA", "key_size": 256, "fingerprint": "SHA256:umbrellaKey/xyz789",
        "age_days": 180, "status": "ACTIVE", "algorithm": "ecdsa-sha2-nistp256",
    },
    {
        "id": "KEY-003", "partner_id": "WAYNE-005", "partner_name": "Wayne Enterprises",
        "key_type": "RSA", "key_size": 1024, "fingerprint": "SHA256:wayneOldKey/def456",
        "age_days": 1200, "status": "ACTIVE", "algorithm": "ssh-rsa",
        "weak": True,  # RSA-1024 is deprecated
    },
]

MOCK_SERVICES: list[dict] = [
    {"name": "SSH Listener", "status": "RUNNING", "port": 22, "uptime_hours": 720},
    {"name": "AS2 Adapter", "status": "RUNNING", "port": 8080, "uptime_hours": 720},
    {"name": "HTTP Server", "status": "RUNNING", "port": 443, "uptime_hours": 720},
    {"name": "Transfer Manager", "status": "RUNNING", "port": None, "uptime_hours": 720},
    {"name": "Admin Server", "status": "RUNNING", "port": 444, "uptime_hours": 720},
]

MOCK_JVM: dict = {
    "heap_used_mb": 3276,
    "heap_max_mb": 4096,
    "heap_pct": 80,
    "gc_collections_per_hour": 12,
    "gc_pause_avg_ms": 180,
    "thread_count": 142,
    "status": "WARNING",
}

MOCK_DISK: dict = {
    "path": "/opt/axway/SecureTransport",
    "used_gb": 312,
    "total_gb": 500,
    "used_pct": 62,
    "status": "OK",
}

MOCK_QUEUES: list[dict] = [
    {"id": "Q-ACME-001", "partner_id": "ACME-001", "partner_name": "Acme Corp",
     "depth": 47, "oldest_item_minutes": 28, "status": "ELEVATED"},
    {"id": "Q-GLOBEX-002", "partner_id": "GLOBEX-002", "partner_name": "Globex Industries",
     "depth": 3, "oldest_item_minutes": 2, "status": "OK"},
    {"id": "Q-INITECH-003", "partner_id": "INITECH-003", "partner_name": "Initech LLC",
     "depth": 0, "oldest_item_minutes": 0, "status": "OK"},
    {"id": "Q-UMBRELLA-004", "partner_id": "UMBRELLA-004", "partner_name": "Umbrella Corp",
     "depth": 0, "oldest_item_minutes": 0, "status": "OK"},
    {"id": "Q-WAYNE-005", "partner_id": "WAYNE-005", "partner_name": "Wayne Enterprises",
     "depth": 8, "oldest_item_minutes": 5, "status": "OK"},
]


def _mock_transfers(partner_id: str | None = None, minutes: int = 60) -> list[dict]:
    """Generate realistic mock transfer history."""
    now = _NOW()
    transfers = []

    scenarios = {
        "ACME-001": {"failures": 8, "successes": 2, "error": "HOST_KEY_VERIFICATION_FAILED",
                     "protocol": "SFTP", "partner_name": "Acme Corp"},
        "GLOBEX-002": {"failures": 1, "successes": 14, "error": "AS2_MDN_TIMEOUT",
                       "protocol": "AS2", "partner_name": "Globex Industries"},
        "INITECH-003": {"failures": 0, "successes": 5, "error": None,
                        "protocol": "HTTPS", "partner_name": "Initech LLC"},
        "UMBRELLA-004": {"failures": 0, "successes": 0, "error": None,
                         "protocol": "SFTP", "partner_name": "Umbrella Corp"},
        "WAYNE-005": {"failures": 0, "successes": 22, "error": None,
                      "protocol": "FTPS", "partner_name": "Wayne Enterprises"},
    }

    partners_to_generate = [partner_id] if partner_id else list(scenarios.keys())

    for pid in partners_to_generate:
        s = scenarios.get(pid, {"failures": 0, "successes": 5, "error": None,
                                "protocol": "SFTP", "partner_name": pid})
        for i in range(s["failures"]):
            transfers.append({
                "id": f"XFER-{pid[:4]}-F{i:03d}",
                "partner_id": pid,
                "partner_name": s["partner_name"],
                "protocol": s["protocol"],
                "status": "FAILED",
                "error_code": s["error"],
                "error_message": _error_message(s["error"]),
                "bytes": 0,
                "started_at": (now - timedelta(minutes=random.randint(1, minutes))).isoformat(),
                "duration_ms": random.randint(500, 3000),
            })
        for i in range(s["successes"]):
            size = random.randint(1024, 10 * 1024 * 1024)
            transfers.append({
                "id": f"XFER-{pid[:4]}-S{i:03d}",
                "partner_id": pid,
                "partner_name": s["partner_name"],
                "protocol": s["protocol"],
                "status": "COMPLETED",
                "error_code": None,
                "error_message": None,
                "bytes": size,
                "started_at": (now - timedelta(minutes=random.randint(1, minutes))).isoformat(),
                "duration_ms": random.randint(800, 15000),
            })

    return transfers


def _error_message(code: str | None) -> str | None:
    messages = {
        "HOST_KEY_VERIFICATION_FAILED": "Host key verification failed: remote host identification has changed",
        "AS2_MDN_TIMEOUT": "MDN not received within 300 seconds; connection refused on partner MDN endpoint",
        "CERT_EXPIRED": "Certificate expired: notAfter date has passed",
        "AUTH_FAILED": "Authentication failed: invalid credentials or key rejected",
        "CIPHER_MISMATCH": "Unable to negotiate cipher suite: no matching algorithm found",
    }
    return messages.get(code) if code else None


# ── Client class ───────────────────────────────────────────────────────────

class AxwayClient:
    """
    Axway SecureTransport Admin API client.
    All methods work in mock mode by default.
    Switch to real mode by setting MOCK_AXWAY=false and providing credentials.
    """

    def __init__(self) -> None:
        self._mock = settings.mock_axway
        if not self._mock:
            self._http = httpx.Client(
                base_url=settings.axway_admin_url,
                auth=(settings.axway_admin_user, settings.axway_admin_password),
                verify=False,  # many on-prem Axway installs use self-signed certs
                timeout=30,
            )

    # ── Partner operations ─────────────────────────────────────────────────

    def list_partners(self) -> list[dict[str, Any]]:
        if self._mock:
            return MOCK_PARTNERS
        # PLACEHOLDER: replace with actual Axway endpoint
        # GET /api/v1.4/accounts
        resp = self._http.get("/api/v1.4/accounts")
        resp.raise_for_status()
        return resp.json().get("result", [])

    def get_partner(self, partner_id: str) -> dict[str, Any] | None:
        if self._mock:
            return next((p for p in MOCK_PARTNERS if p["id"] == partner_id), None)
        # PLACEHOLDER: GET /api/v1.4/accounts/{partner_id}
        resp = self._http.get(f"/api/v1.4/accounts/{partner_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    # ── Transfer operations ────────────────────────────────────────────────

    def list_transfers(
        self,
        partner_id: str | None = None,
        status: str | None = None,
        since_minutes: int = 60,
    ) -> list[dict[str, Any]]:
        if self._mock:
            transfers = _mock_transfers(partner_id, since_minutes)
            if status:
                transfers = [t for t in transfers if t["status"] == status]
            return transfers
        # PLACEHOLDER: GET /api/v1.4/transfers
        params: dict = {"limit": 200}
        if partner_id:
            params["accountName"] = partner_id
        if status:
            params["status"] = status
        resp = self._http.get("/api/v1.4/transfers", params=params)
        resp.raise_for_status()
        return resp.json().get("result", [])

    def retry_transfer(self, transfer_id: str) -> dict[str, Any]:
        if self._mock:
            return {"transfer_id": transfer_id, "status": "QUEUED", "mock": True}
        # PLACEHOLDER: POST /api/v1.4/transfers/{transfer_id}/resubmit
        resp = self._http.post(f"/api/v1.4/transfers/{transfer_id}/resubmit")
        resp.raise_for_status()
        return resp.json()

    # ── Certificate operations ─────────────────────────────────────────────

    def list_certificates(self) -> list[dict[str, Any]]:
        if self._mock:
            return MOCK_CERTIFICATES
        # PLACEHOLDER: GET /api/v1.4/certificates
        resp = self._http.get("/api/v1.4/certificates")
        resp.raise_for_status()
        return resp.json().get("result", [])

    def get_certificate(self, cert_id: str) -> dict[str, Any] | None:
        if self._mock:
            return next((c for c in MOCK_CERTIFICATES if c["id"] == cert_id), None)
        # PLACEHOLDER: GET /api/v1.4/certificates/{cert_id}
        resp = self._http.get(f"/api/v1.4/certificates/{cert_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def import_certificate(self, cert_pem: str, partner_id: str) -> dict[str, Any]:
        if self._mock:
            return {"cert_id": f"CERT-NEW-{partner_id}", "status": "IMPORTED", "mock": True}
        # PLACEHOLDER: POST /api/v1.4/certificates/import
        resp = self._http.post("/api/v1.4/certificates/import",
                               json={"certificate": cert_pem, "accountName": partner_id})
        resp.raise_for_status()
        return resp.json()

    # ── SSH Key operations ─────────────────────────────────────────────────

    def list_ssh_keys(self) -> list[dict[str, Any]]:
        if self._mock:
            return MOCK_SSH_KEYS
        # PLACEHOLDER: GET /api/v1.4/sshKeys
        resp = self._http.get("/api/v1.4/sshKeys")
        resp.raise_for_status()
        return resp.json().get("result", [])

    def get_known_hosts(self, partner_id: str) -> list[dict[str, Any]]:
        if self._mock:
            key = next((k for k in MOCK_SSH_KEYS if k["partner_id"] == partner_id), None)
            return [key] if key else []
        # PLACEHOLDER: GET /api/v1.4/accounts/{partner_id}/sshKnownHosts
        resp = self._http.get(f"/api/v1.4/accounts/{partner_id}/sshKnownHosts")
        resp.raise_for_status()
        return resp.json().get("result", [])

    def update_known_host(self, partner_id: str, fingerprint: str, key_type: str) -> dict[str, Any]:
        if self._mock:
            return {"partner_id": partner_id, "fingerprint": fingerprint,
                    "key_type": key_type, "status": "UPDATED", "mock": True}
        # PLACEHOLDER: PUT /api/v1.4/accounts/{partner_id}/sshKnownHosts
        resp = self._http.put(
            f"/api/v1.4/accounts/{partner_id}/sshKnownHosts",
            json={"fingerprint": fingerprint, "keyType": key_type},
        )
        resp.raise_for_status()
        return resp.json()

    # ── Service operations ─────────────────────────────────────────────────

    def list_services(self) -> list[dict[str, Any]]:
        if self._mock:
            return MOCK_SERVICES
        # PLACEHOLDER: GET /api/v1.4/services
        resp = self._http.get("/api/v1.4/services")
        resp.raise_for_status()
        return resp.json().get("result", [])

    def restart_service(self, service_name: str) -> dict[str, Any]:
        if self._mock:
            return {"service": service_name, "status": "RESTARTED", "mock": True}
        # PLACEHOLDER: POST /api/v1.4/services/{service_name}/restart
        resp = self._http.post(f"/api/v1.4/services/{service_name}/restart")
        resp.raise_for_status()
        return resp.json()

    # ── Queue operations ───────────────────────────────────────────────────

    def list_queues(self) -> list[dict[str, Any]]:
        if self._mock:
            return MOCK_QUEUES
        # PLACEHOLDER: GET /api/v1.4/transferQueues
        resp = self._http.get("/api/v1.4/transferQueues")
        resp.raise_for_status()
        return resp.json().get("result", [])

    def clear_queue(self, queue_id: str) -> dict[str, Any]:
        if self._mock:
            return {"queue_id": queue_id, "status": "CLEARED", "mock": True}
        # PLACEHOLDER: DELETE /api/v1.4/transferQueues/{queue_id}/items
        resp = self._http.delete(f"/api/v1.4/transferQueues/{queue_id}/items")
        resp.raise_for_status()
        return resp.json()

    # ── JVM & Disk metrics ─────────────────────────────────────────────────

    def get_jvm_metrics(self) -> dict[str, Any]:
        if self._mock:
            return MOCK_JVM
        # PLACEHOLDER: GET /api/v1.4/monitoring/jvm
        resp = self._http.get("/api/v1.4/monitoring/jvm")
        resp.raise_for_status()
        return resp.json()

    def get_disk_metrics(self) -> dict[str, Any]:
        if self._mock:
            return MOCK_DISK
        # PLACEHOLDER: GET /api/v1.4/monitoring/disk
        resp = self._http.get("/api/v1.4/monitoring/disk")
        resp.raise_for_status()
        return resp.json()

    # ── Last transfer timestamps ───────────────────────────────────────────

    def get_last_transfer_time(self, partner_id: str) -> datetime | None:
        """Return the timestamp of the most recent successful transfer for a partner."""
        if self._mock:
            # Umbrella Corp has been silent for 2 days (demo scenario)
            if partner_id == "UMBRELLA-004":
                return _NOW() - timedelta(days=2, hours=3)
            return _NOW() - timedelta(minutes=random.randint(5, 120))
        # PLACEHOLDER: query transfers API with partner filter + COMPLETED status
        transfers = self.list_transfers(partner_id=partner_id, status="COMPLETED", since_minutes=2880)
        if not transfers:
            return None
        return max(datetime.fromisoformat(t["started_at"]) for t in transfers)


# Module-level singleton
axway = AxwayClient()
