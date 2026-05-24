"""
Proactive health checks for Axway SecureTransport.

Each check returns a list of Finding dicts. An empty list means the check passed.
A finding becomes an incident if it is not already tracked (deduplicated by fingerprint).
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from collector.axway_client import axway
from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class Finding:
    check_name: str
    category: str           # matches models.incident.Category
    severity: str           # P1-P4
    title: str
    description: str
    partner_id: str | None = None
    partner_name: str | None = None
    protocol: str | None = None
    raw_data: dict = field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        """Stable fingerprint for deduplication (same check + partner + category = same incident)."""
        key = f"{self.check_name}:{self.category}:{self.partner_id or 'global'}"
        return hashlib.md5(key.encode()).hexdigest()[:16]


# ── Check 1: Certificate expiry ────────────────────────────────────────────

def check_cert_expiry() -> list[Finding]:
    findings: list[Finding] = []
    warn_days = settings.cert_expiry_warn_days
    try:
        certs = axway.list_certificates()
        for cert in certs:
            days = cert.get("days_until_expiry", 999)
            if days > warn_days:
                continue
            if days <= 1:
                sev, label = "P1", "CRITICAL"
            elif days <= 7:
                sev, label = "P2", "URGENT"
            elif days <= 15:
                sev, label = "P3", "WARNING"
            else:
                sev, label = "P4", "NOTICE"

            findings.append(Finding(
                check_name="cert_expiry",
                category="TLS_CERT",
                severity=sev,
                title=f"[{label}] Certificate expiring in {days} day(s): {cert['common_name']}",
                description=(
                    f"Certificate '{cert['common_name']}' for partner {cert.get('partner_name', 'unknown')} "
                    f"expires in {days} day(s). "
                    f"Issuer: {cert.get('issuer', 'unknown')}. "
                    f"Algorithm: {cert.get('algorithm', 'unknown')}, Key size: {cert.get('key_size', '?')} bits. "
                    "Immediate renewal required to avoid transfer failures."
                ),
                partner_id=cert.get("partner_id"),
                partner_name=cert.get("partner_name"),
                raw_data=cert,
            ))
    except Exception:
        logger.exception("cert_expiry check failed")
    return findings


# ── Check 2: Transfer failure rate ─────────────────────────────────────────

def check_transfer_failures() -> list[Finding]:
    findings: list[Finding] = []
    threshold = settings.failure_rate_threshold
    try:
        transfers = axway.list_transfers(since_minutes=5)
        # Group failures by partner
        failure_counts: dict[str, list] = {}
        for t in transfers:
            if t["status"] == "FAILED":
                pid = t["partner_id"]
                failure_counts.setdefault(pid, []).append(t)

        for pid, failures in failure_counts.items():
            if len(failures) < threshold:
                continue
            sample = failures[0]
            count = len(failures)
            error_code = sample.get("error_code", "UNKNOWN")

            if count >= 10:
                sev = "P1"
            elif count >= 5:
                sev = "P2"
            else:
                sev = "P3"

            findings.append(Finding(
                check_name="transfer_failures",
                category=_error_to_category(error_code),
                severity=sev,
                title=f"{count} transfer failure(s) in 5 min — {sample['partner_name']} ({sample['protocol']})",
                description=(
                    f"Partner {sample['partner_name']} has {count} failed {sample['protocol']} transfers "
                    f"in the last 5 minutes. Error: {error_code} — {sample.get('error_message', '')}. "
                    "Automatic root cause analysis recommended."
                ),
                partner_id=pid,
                partner_name=sample["partner_name"],
                protocol=sample["protocol"],
                raw_data={"failure_count": count, "sample_transfer": sample, "error_code": error_code},
            ))
    except Exception:
        logger.exception("transfer_failures check failed")
    return findings


# ── Check 3: Partner silence ────────────────────────────────────────────────

def check_partner_silence() -> list[Finding]:
    findings: list[Finding] = []
    try:
        partners = axway.list_partners()
        for partner in partners:
            if not partner.get("active"):
                continue
            expected_hours = partner.get("expected_transfer_interval_hours")
            if not expected_hours:
                continue
            last_transfer = axway.get_last_transfer_time(partner["id"])
            if last_transfer is None:
                silence_hours = expected_hours * 3  # treat unknown as very overdue
            else:
                now = datetime.now(timezone.utc)
                if last_transfer.tzinfo is None:
                    last_transfer = last_transfer.replace(tzinfo=timezone.utc)
                silence_hours = (now - last_transfer).total_seconds() / 3600

            if silence_hours <= expected_hours:
                continue

            overdue_factor = silence_hours / expected_hours
            sev = "P2" if overdue_factor >= 3 else "P3"

            findings.append(Finding(
                check_name="partner_silence",
                category="PARTNER_SILENCE",
                severity=sev,
                title=f"No transfers from {partner['name']} for {silence_hours:.1f}h (expected every {expected_hours}h)",
                description=(
                    f"Partner {partner['name']} ({partner['protocol']}) has not sent any successful transfers "
                    f"for {silence_hours:.1f} hours. Expected transfer interval: every {expected_hours} hours. "
                    "Possible causes: partner system down, firewall change, schedule change, or silent failure."
                ),
                partner_id=partner["id"],
                partner_name=partner["name"],
                protocol=partner.get("protocol"),
                raw_data={"silence_hours": silence_hours, "expected_hours": expected_hours},
            ))
    except Exception:
        logger.exception("partner_silence check failed")
    return findings


# ── Check 4: SSH key health ─────────────────────────────────────────────────

def check_ssh_keys() -> list[Finding]:
    findings: list[Finding] = []
    try:
        keys = axway.list_ssh_keys()
        for key in keys:
            issues = []
            sev = "P4"

            if key.get("key_type") == "DSA":
                issues.append("DSA keys are deprecated and should be replaced with RSA-4096 or ECDSA")
                sev = "P2"
            if key.get("key_type") == "RSA" and key.get("key_size", 4096) < 2048:
                issues.append(f"RSA key size {key.get('key_size')} bits is below minimum 2048 bits")
                sev = "P2"
            if key.get("weak"):
                issues.append("Key flagged as weak by algorithm audit")
                sev = "P2"
            if key.get("age_days", 0) > 365:
                issues.append(f"Key is {key.get('age_days')} days old — consider rotation (recommended annually)")
                if sev == "P4":
                    sev = "P4"

            if not issues:
                continue

            findings.append(Finding(
                check_name="ssh_key_audit",
                category="COMPLIANCE",
                severity=sev,
                title=f"SSH key issue — {key.get('partner_name', key.get('partner_id'))}: {', '.join(issues[:1])}",
                description=(
                    f"SSH key for partner {key.get('partner_name')} (fingerprint: {key.get('fingerprint')}) "
                    f"has the following issues: {'; '.join(issues)}. "
                    "Coordinate with partner to rotate the key to meet current security standards."
                ),
                partner_id=key.get("partner_id"),
                partner_name=key.get("partner_name"),
                raw_data=key,
            ))
    except Exception:
        logger.exception("ssh_key_audit check failed")
    return findings


# ── Check 5: Queue depth ────────────────────────────────────────────────────

def check_queue_depth() -> list[Finding]:
    findings: list[Finding] = []
    warn_depth = settings.queue_depth_warn
    try:
        queues = axway.list_queues()
        for q in queues:
            depth = q.get("depth", 0)
            if depth < max(warn_depth // 10, 20):  # flag if > 10% of warn or > 20
                continue
            oldest = q.get("oldest_item_minutes", 0)
            if depth >= warn_depth:
                sev = "P2"
            elif depth >= warn_depth // 2:
                sev = "P3"
            else:
                sev = "P4"

            if oldest < 10 and depth < 100:
                continue  # small, recent queue — not worth an incident

            findings.append(Finding(
                check_name="queue_depth",
                category="QUEUE",
                severity=sev,
                title=f"Elevated queue depth for {q['partner_name']}: {depth} items ({oldest} min old)",
                description=(
                    f"Transfer queue for partner {q['partner_name']} has {depth} items, "
                    f"oldest item waiting {oldest} minutes. "
                    "This is likely caused by repeated transfer failures creating a backlog. "
                    "Resolve the underlying failure first, then retry queued items."
                ),
                partner_id=q.get("partner_id"),
                partner_name=q.get("partner_name"),
                raw_data=q,
            ))
    except Exception:
        logger.exception("queue_depth check failed")
    return findings


# ── Check 6: JVM & disk health ─────────────────────────────────────────────

def check_jvm_health() -> list[Finding]:
    findings: list[Finding] = []
    try:
        jvm = axway.get_jvm_metrics()
        heap_pct = jvm.get("heap_pct", 0)
        warn_pct = settings.jvm_heap_warn_pct

        if heap_pct >= warn_pct:
            sev = "P1" if heap_pct >= 95 else "P2"
            findings.append(Finding(
                check_name="jvm_health",
                category="JVM",
                severity=sev,
                title=f"Axway JVM heap at {heap_pct}% — Transfer Manager performance degraded",
                description=(
                    f"JVM heap usage is {heap_pct}% ({jvm.get('heap_used_mb')}MB / {jvm.get('heap_max_mb')}MB). "
                    f"GC running {jvm.get('gc_collections_per_hour', 0)} times/hour with "
                    f"{jvm.get('gc_pause_avg_ms', 0)}ms average pause. "
                    "Transfer processing is slowing down. Action required before OutOfMemoryError."
                ),
                raw_data=jvm,
            ))

        disk = axway.get_disk_metrics()
        disk_pct = disk.get("used_pct", 0)
        warn_disk = settings.disk_warn_pct

        if disk_pct >= warn_disk:
            sev = "P1" if disk_pct >= 95 else "P2"
            findings.append(Finding(
                check_name="disk_health",
                category="DISK",
                severity=sev,
                title=f"Axway disk usage at {disk_pct}% on {disk.get('path')}",
                description=(
                    f"Axway data partition {disk.get('path')} is {disk_pct}% full "
                    f"({disk.get('used_gb')}GB / {disk.get('total_gb')}GB). "
                    "If disk fills completely, Axway will stop accepting inbound transfers. "
                    "Clean up old log files and completed transfer payloads immediately."
                ),
                raw_data=disk,
            ))
    except Exception:
        logger.exception("jvm_health check failed")
    return findings


# ── Helpers ────────────────────────────────────────────────────────────────

def _error_to_category(error_code: str) -> str:
    mapping = {
        "HOST_KEY_VERIFICATION_FAILED": "SFTP_KEY",
        "AUTH_FAILED": "SFTP_AUTH",
        "CERT_EXPIRED": "TLS_CERT",
        "CIPHER_MISMATCH": "TLS_HANDSHAKE",
        "AS2_MDN_TIMEOUT": "AS2_MDN",
        "AS2_ENCRYPT_ERROR": "AS2_ENCRYPT",
    }
    return mapping.get(error_code, "UNKNOWN")


ALL_CHECKS = [
    check_cert_expiry,
    check_transfer_failures,
    check_partner_silence,
    check_ssh_keys,
    check_queue_depth,
    check_jvm_health,
]
