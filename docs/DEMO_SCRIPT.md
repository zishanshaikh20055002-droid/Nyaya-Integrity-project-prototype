# Three-Minute Demo Script

1. Open the dashboard and point out that it is a judicial *decision-support* interface, not an automated judge.
2. Show the IPC-to-BNS mapping card and explain that statute transition is modeled as deterministic, reviewable links.
3. Move to the Evidence Vault. Explain that large media would live outside a ledger, while its SHA-256 identity and every custody action are recorded.
4. Run `./run.ps1`, refresh the dashboard, and show the `LIVE API` badge.
5. Select **Register evidence**. The local service stores a new evidence record, hashes its content, and adds a custody event to SQLite.
6. Open `http://127.0.0.1:8000/docs` to show the typed API contract and explain how a real forensic or GraphRAG service would be substituted behind those boundaries.

## Strong interview framing

"I separated the interface, legal decision-support workflow, evidence hashing, and custody persistence so each high-risk function is auditable and replaceable. The present version uses deterministic demo logic rather than claiming unsupported predictive accuracy."
