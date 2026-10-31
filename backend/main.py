"""Local API for the Nyaya Integrity Console demo.

This service intentionally produces decision-support records, never bail decisions.
It persists evidence hashes and a custody log so the front end can demonstrate a
traceable evidence workflow without relying on external legal or AI providers.
"""

from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parent.parent
DATABASE = ROOT / "nyaya.db"
STATIC_DIR = ROOT / "dist"

SEED_CASE = {
    "id": "CR-2026-01842",
    "title": "State v. R. Kumar",
    "court": "District & Sessions Court, Pune",
    "status": "review_pending",
    "submitted_at": "2026-10-31T09:15:00+05:30",
    "summary": "Bail application is awaiting human review. This record is a decision-support demonstration.",
}

STATUTE_MAPPINGS = [
    {"legacy": "IPC §420", "modern": "BNS §318(4)", "legacy_name": "Cheating & dishonestly inducing delivery", "modern_name": "Cheating & dishonest inducement", "confidence": "Exact"},
    {"legacy": "IPC §468", "modern": "BNS §336(3)", "legacy_name": "Forgery for purpose of cheating", "modern_name": "Forgery intended for cheating", "confidence": "Reviewed"},
    {"legacy": "CrPC §437", "modern": "BNSS §480", "legacy_name": "Bail in non-bailable offences", "modern_name": "Bail framework", "confidence": "Exact"},
]

PRECEDENTS = [
    {"court": "SC", "name": "Arnesh Kumar v. State of Bihar", "principle": "Process safeguards and necessity of detention", "relevance": 89, "source": "Verified demo knowledge graph"},
    {"court": "HC", "name": "Sanjay Chandra v. CBI", "principle": "Balancing liberty and trial attendance", "relevance": 83, "source": "Verified demo knowledge graph"},
    {"court": "SC", "name": "Satender Kumar Antil v. CBI", "principle": "Bail practice and proportionality", "relevance": 78, "source": "Verified demo knowledge graph"},
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connection() -> sqlite3.Connection:
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def initialise_database() -> None:
    with connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                court TEXT NOT NULL,
                status TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                summary TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS evidence_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                media_type TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                byte_size INTEGER NOT NULL,
                submitted_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                forensic_signal INTEGER NOT NULL,
                FOREIGN KEY(case_id) REFERENCES cases(id)
            );
            CREATE TABLE IF NOT EXISTS custody_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                evidence_id INTEGER,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                message TEXT NOT NULL,
                event_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(case_id) REFERENCES cases(id),
                FOREIGN KEY(evidence_id) REFERENCES evidence_items(id)
            );
            CREATE TABLE IF NOT EXISTS review_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL,
                requested_by TEXT NOT NULL,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(case_id) REFERENCES cases(id)
            );
            """
        )
        db.execute(
            """INSERT OR IGNORE INTO cases(id, title, court, status, submitted_at, summary)
            VALUES(:id, :title, :court, :status, :submitted_at, :summary)""",
            SEED_CASE,
        )
        evidence_count = db.execute("SELECT COUNT(*) FROM evidence_items WHERE case_id = ?", (SEED_CASE["id"],)).fetchone()[0]
        if evidence_count == 0:
            payload = b"Nyaya demo evidence record: cctv_market_2014.mp4"
            digest = hashlib.sha256(payload).hexdigest()
            cursor = db.execute(
                """INSERT INTO evidence_items(case_id, filename, media_type, sha256, byte_size, submitted_by, created_at, forensic_signal)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)""",
                (SEED_CASE["id"], "cctv_market_2014.mp4", "video/mp4", digest, len(payload), "Cyber Cell Pune", "2026-10-30T12:44:00+00:00", 72),
            )
            evidence_id = cursor.lastrowid
            for event_type, actor, message, timestamp in [
                ("evidence_received", "Cyber Cell Pune", "Evidence received and custody initiated.", "2026-10-30T12:44:00+00:00"),
                ("hash_registered", "Station Intake Terminal", "SHA-256 content hash registered with officer signature.", "2026-10-31T04:18:00+00:00"),
                ("forensic_certificate", "FSL Pune", "Forensic analysis certificate bound to evidence record.", "2026-10-31T05:56:00+00:00"),
            ]:
                add_event(db, SEED_CASE["id"], evidence_id, event_type, actor, message, timestamp)


def add_event(
    db: sqlite3.Connection,
    case_id: str,
    evidence_id: int | None,
    event_type: str,
    actor: str,
    message: str,
    created_at: str | None = None,
) -> None:
    timestamp = created_at or now()
    material = f"{case_id}|{evidence_id}|{event_type}|{actor}|{message}|{timestamp}".encode()
    db.execute(
        """INSERT INTO custody_events(case_id, evidence_id, event_type, actor, message, event_hash, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (case_id, evidence_id, event_type, actor, message, hashlib.sha256(material).hexdigest(), timestamp),
    )


class EvidenceRegistration(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    media_type: str = Field(default="application/octet-stream", max_length=100)
    content_b64: str = Field(min_length=1)
    submitted_by: str = Field(default="Demo Investigator", max_length=100)


class ReviewRequest(BaseModel):
    requested_by: str = Field(default="A. Sharma", max_length=100)
    note: str = Field(default="Human review requested from dashboard.", max_length=500)


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialise_database()
    yield


app = FastAPI(
    title="Nyaya Integrity Console API",
    version="0.1.0",
    description="Interview-ready legal decision-support and evidence integrity demonstration API.",
    lifespan=lifespan,
)


def get_case_or_404(case_id: str) -> dict[str, Any]:
    with connection() as db:
        row = db.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    return dict(row)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "nyaya-integrity-api", "storage": "sqlite"}


@app.get("/api/cases")
def list_cases() -> list[dict[str, Any]]:
    with connection() as db:
        return [dict(row) for row in db.execute("SELECT * FROM cases ORDER BY submitted_at DESC")]


@app.get("/api/cases/{case_id}")
def get_case(case_id: str) -> dict[str, Any]:
    case = get_case_or_404(case_id)
    case["statute_mappings"] = STATUTE_MAPPINGS
    case["precedents"] = PRECEDENTS
    return case


@app.get("/api/cases/{case_id}/analysis")
def analyse_case(case_id: str) -> dict[str, Any]:
    get_case_or_404(case_id)
    return {
        "case_id": case_id,
        "decision_support_only": True,
        "consistency_index": 63,
        "recommendation": "human_review_required",
        "risk_factors": ["Witness-contact concern requires a human assessment."],
        "mitigating_factors": ["No prior conviction record in this demonstration dataset.", "Stable local residence recorded."],
        "statute_mappings": STATUTE_MAPPINGS,
        "precedents": PRECEDENTS,
        "model_card": {"name": "Deterministic demo policy engine", "version": "0.1.0", "purpose": "Transparent interview demonstration; not a predictive legal model."},
    }


@app.get("/api/cases/{case_id}/evidence")
def list_evidence(case_id: str) -> list[dict[str, Any]]:
    get_case_or_404(case_id)
    with connection() as db:
        return [dict(row) for row in db.execute("SELECT * FROM evidence_items WHERE case_id = ? ORDER BY id DESC", (case_id,))]


@app.post("/api/cases/{case_id}/evidence", status_code=201)
def register_evidence(case_id: str, item: EvidenceRegistration) -> dict[str, Any]:
    get_case_or_404(case_id)
    try:
        raw = base64.b64decode(item.content_b64, validate=True)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="content_b64 must be valid base64") from exc
    if len(raw) > 5_000_000:
        raise HTTPException(status_code=413, detail="Demo API accepts evidence up to 5 MB")
    digest = hashlib.sha256(raw).hexdigest()
    created_at = now()
    forensic_signal = 15 if item.media_type.startswith("text/") else 52
    with connection() as db:
        cursor = db.execute(
            """INSERT INTO evidence_items(case_id, filename, media_type, sha256, byte_size, submitted_by, created_at, forensic_signal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (case_id, item.filename, item.media_type, digest, len(raw), item.submitted_by, created_at, forensic_signal),
        )
        evidence_id = cursor.lastrowid
        add_event(db, case_id, evidence_id, "evidence_registered", item.submitted_by, f"Evidence '{item.filename}' registered with SHA-256 hash.", created_at)
        db.commit()
        evidence = db.execute("SELECT * FROM evidence_items WHERE id = ?", (evidence_id,)).fetchone()
    return {"evidence": dict(evidence), "message": "Evidence registered; chain-of-custody event created."}


@app.get("/api/cases/{case_id}/custody")
def custody_events(case_id: str) -> list[dict[str, Any]]:
    get_case_or_404(case_id)
    with connection() as db:
        return [dict(row) for row in db.execute("SELECT * FROM custody_events WHERE case_id = ? ORDER BY created_at DESC", (case_id,))]


@app.post("/api/cases/{case_id}/review-requests", status_code=201)
def request_human_review(case_id: str, request: ReviewRequest) -> dict[str, str]:
    get_case_or_404(case_id)
    created_at = now()
    with connection() as db:
        db.execute("INSERT INTO review_requests(case_id, requested_by, note, created_at) VALUES (?, ?, ?, ?)", (case_id, request.requested_by, request.note, created_at))
        add_event(db, case_id, None, "human_review_requested", request.requested_by, request.note, created_at)
        db.execute("UPDATE cases SET status = 'review_requested' WHERE id = ?", (case_id,))
        db.commit()
    return {"status": "review_requested", "message": "Human review request recorded in the audit trail."}


app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")

