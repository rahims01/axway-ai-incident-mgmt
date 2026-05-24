"""
FastAPI application — all routes.

Start with:
    uvicorn api.main:app --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config.settings import settings
from models.database import SessionLocal, get_db, init_db
from models.incident import Incident, IncidentOut, IncidentStatus, IncidentUpdate

logging.basicConfig(
    level=logging.DEBUG if settings.app_debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent.parent / "static"


# ── App lifecycle ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initialising Axway AIOps…")
    init_db()
    from collector.scheduler import start as start_scheduler
    start_scheduler()
    logger.info("Ready — open http://localhost:8000 in your browser")
    yield
    # Shutdown
    from collector.scheduler import stop as stop_scheduler
    stop_scheduler()


app = FastAPI(
    title="Axway SecureTransport AI AIOps",
    description="Proactive incident management for Axway SecureTransport MFT",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the dashboard HTML and docs
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── Dashboard ──────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(STATIC_DIR / "dashboard.html")


@app.get("/docs-site", include_in_schema=False)
def docs_site():
    return FileResponse(Path(__file__).parent.parent / "docs.html")


# ── System health ──────────────────────────────────────────────────────────

@app.get("/api/health", tags=["System"])
def health() -> dict[str, Any]:
    from collector.axway_client import axway
    try:
        services = axway.list_services()
        jvm = axway.get_jvm_metrics()
        disk = axway.get_disk_metrics()
        certs = axway.list_certificates()
        critical_certs = [c for c in certs if c.get("days_until_expiry", 999) <= 7]
        warn_certs = [c for c in certs if 7 < c.get("days_until_expiry", 999) <= 30]

        db = SessionLocal()
        try:
            open_count = db.query(Incident).filter(
                Incident.status.notin_([IncidentStatus.RESOLVED, IncidentStatus.ESCALATED])
            ).count()
            p1_count = db.query(Incident).filter(
                Incident.severity == "P1",
                Incident.status.notin_([IncidentStatus.RESOLVED, IncidentStatus.ESCALATED]),
            ).count()
        finally:
            db.close()

        return {
            "status": "DEGRADED" if p1_count > 0 else ("WARNING" if open_count > 0 else "OK"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mock_mode": {"axway": settings.mock_axway, "llm": settings.mock_llm},
            "open_incidents": open_count,
            "p1_incidents": p1_count,
            "services": services,
            "jvm": {"heap_pct": jvm.get("heap_pct"), "status": jvm.get("status")},
            "disk": {"used_pct": disk.get("used_pct"), "status": disk.get("status")},
            "certificates": {
                "total": len(certs),
                "critical": len(critical_certs),
                "warning": len(warn_certs),
            },
        }
    except Exception as exc:
        logger.exception("Health check failed")
        return {"status": "ERROR", "error": str(exc)}


# ── Incidents ──────────────────────────────────────────────────────────────

@app.get("/api/incidents", tags=["Incidents"], response_model=list[IncidentOut])
def list_incidents(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    q = db.query(Incident).order_by(Incident.created_at.desc())
    if status:
        q = q.filter(Incident.status == status)
    if severity:
        q = q.filter(Incident.severity == severity)
    return q.limit(limit).all()


@app.get("/api/incidents/{incident_id}", tags=["Incidents"], response_model=IncidentOut)
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(404, "Incident not found")
    return inc


@app.patch("/api/incidents/{incident_id}", tags=["Incidents"], response_model=IncidentOut)
def update_incident(incident_id: str, body: IncidentUpdate, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(404, "Incident not found")
    if body.status:
        inc.status = body.status
        if body.status == IncidentStatus.RESOLVED:
            inc.resolved_at = datetime.now(timezone.utc)
    if body.resolution_notes:
        inc.resolution_notes = body.resolution_notes
    db.commit()
    db.refresh(inc)
    return inc


@app.post("/api/incidents/{incident_id}/analyze", tags=["Incidents"])
def analyze_incident(incident_id: str) -> dict:
    """Trigger LLM root-cause analysis for an incident."""
    import threading
    def _run():
        from agent.agents import analyze_incident as _analyze
        _analyze(incident_id)
    threading.Thread(target=_run, daemon=True).start()
    return {"status": "started", "message": "Analysis started — refresh in a few seconds"}


@app.post("/api/incidents/{incident_id}/fix", tags=["Incidents"])
def fix_incident(incident_id: str) -> dict:
    """Attempt automated fix for an incident."""
    from agent.agents import attempt_auto_fix
    return attempt_auto_fix(incident_id)


@app.delete("/api/incidents/{incident_id}", tags=["Incidents"])
def resolve_incident(incident_id: str, db: Session = Depends(get_db)) -> dict:
    """Mark an incident as resolved."""
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(404, "Incident not found")
    inc.status = IncidentStatus.RESOLVED
    inc.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "resolved"}


# ── Stats ──────────────────────────────────────────────────────────────────

@app.get("/api/stats", tags=["System"])
def stats(db: Session = Depends(get_db)) -> dict[str, Any]:
    total = db.query(Incident).count()
    resolved = db.query(Incident).filter(Incident.status == IncidentStatus.RESOLVED).count()
    by_severity = {}
    for sev in ["P1", "P2", "P3", "P4"]:
        by_severity[sev] = db.query(Incident).filter(Incident.severity == sev).count()
    by_category: dict[str, int] = {}
    for inc in db.query(Incident.category).all():
        by_category[inc.category] = by_category.get(inc.category, 0) + 1
    return {
        "total_incidents": total,
        "resolved": resolved,
        "open": total - resolved,
        "by_severity": by_severity,
        "by_category": by_category,
    }


# ── Manual check trigger ───────────────────────────────────────────────────

@app.post("/api/checks/run", tags=["Checks"])
def run_checks() -> dict:
    """Manually trigger all proactive health checks."""
    import threading
    results: dict = {}

    def _run():
        from agent.agents import run_proactive_checks
        ids = run_proactive_checks()
        results["created"] = ids

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=30)
    return {"status": "complete", "incidents_created": results.get("created", [])}


# ── Axway data endpoints ───────────────────────────────────────────────────

@app.get("/api/partners", tags=["Axway"])
def list_partners() -> list[dict]:
    from collector.axway_client import axway
    return axway.list_partners()


@app.get("/api/certificates", tags=["Axway"])
def list_certificates() -> list[dict]:
    from collector.axway_client import axway
    return axway.list_certificates()


@app.get("/api/transfers", tags=["Axway"])
def list_transfers(partner_id: Optional[str] = None, minutes: int = 60) -> list[dict]:
    from collector.axway_client import axway
    return axway.list_transfers(partner_id=partner_id, since_minutes=minutes)


@app.get("/api/queues", tags=["Axway"])
def list_queues() -> list[dict]:
    from collector.axway_client import axway
    return axway.list_queues()


@app.get("/api/ssh-keys", tags=["Axway"])
def list_ssh_keys() -> list[dict]:
    from collector.axway_client import axway
    return axway.list_ssh_keys()


# ── Chat ───────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    history: Optional[list[dict]] = None


@app.post("/api/chat", tags=["Chat"])
def chat(req: ChatRequest) -> dict:
    from llm.client import llm
    resp = llm.chat(req.message, req.history)
    return {"answer": resp.answer, "sources": resp.sources, "suggestions": resp.follow_up_suggestions}


# ── Webhook receiver ───────────────────────────────────────────────────────

class AlertWebhook(BaseModel):
    source: str           # e.g. "datadog", "pagerduty", "splunk"
    severity: str = "P3"
    title: str
    description: str
    partner_id: Optional[str] = None
    partner_name: Optional[str] = None
    category: str = "UNKNOWN"


@app.post("/api/webhooks/alert", tags=["Webhooks"])
def receive_alert(alert: AlertWebhook, db: Session = Depends(get_db)) -> dict:
    """
    Receive alerts from external monitoring systems (Datadog, Splunk, PagerDuty, etc.).
    Creates a new incident and queues it for analysis.
    """
    from models.incident import Incident
    import hashlib

    fingerprint = hashlib.md5(
        f"webhook:{alert.source}:{alert.category}:{alert.partner_id}:{alert.title[:50]}".encode()
    ).hexdigest()[:16]

    existing = db.query(Incident).filter(
        Incident.fingerprint == fingerprint,
        Incident.status.notin_([IncidentStatus.RESOLVED, IncidentStatus.ESCALATED]),
    ).first()
    if existing:
        return {"status": "duplicate", "incident_id": existing.id, "incident_number": existing.incident_number}

    inc = Incident(
        incident_number=f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
        category=alert.category,
        severity=alert.severity,
        status=IncidentStatus.NEW,
        partner_id=alert.partner_id,
        partner_name=alert.partner_name,
        title=alert.title,
        description=alert.description,
        source_check=f"webhook:{alert.source}",
        fingerprint=fingerprint,
    )
    db.add(inc)
    db.commit()
    db.refresh(inc)

    # Kick off analysis in background
    import threading
    threading.Thread(
        target=lambda: __import__("agent.agents", fromlist=["analyze_incident"]).analyze_incident(inc.id),
        daemon=True,
    ).start()

    return {"status": "created", "incident_id": inc.id, "incident_number": inc.incident_number}
