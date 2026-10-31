# Nyaya Integrity Console

An interview-ready legal technology prototype that demonstrates transparent judicial decision support, evidence hashing, and tamper-evident custody events.

## What works locally

- FastAPI API with generated OpenAPI documentation at `/docs`
- SQLite persistence for cases, evidence, review requests, and custody events
- SHA-256 evidence hashing at registration
- Append-only, hash-linked custody-event records
- Deterministic IPC-to-BNS mappings and precedent responses for explainable demonstration output
- Static dashboard served by the API at `/`

## Run locally

```powershell
cd "D:\Law system project"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn backend.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000` for the dashboard and `http://127.0.0.1:8000/docs` for the interactive API documentation.

## Example evidence workflow

```powershell
$payload = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("sample evidence"))
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/cases/CR-2026-01842/evidence" -ContentType "application/json" -Body (@{
  filename = "investigator-note.txt"
  media_type = "text/plain"
  content_b64 = $payload
  submitted_by = "Demo Investigator"
} | ConvertTo-Json)
```

## Responsible-use boundary

The legal analysis endpoint is an explainable demonstration of workflow design. It does not determine bail, guilt, innocence, or admissibility; each output explicitly requires human review.
