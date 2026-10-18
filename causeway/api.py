"""FastAPI app: JSON endpoints plus the single static page.  python -m causeway.api  (see make demo)"""
import json
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from causeway.graph.queries import run
from causeway.investigate import investigate, resolve
from causeway.qa import ask
from causeway.session import Session

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title="Causeway")
TENANT = "alpha"   # bound server-side; no endpoint accepts a tenant parameter
session = Session(TENANT)


def _truth():
    return {t["incident"]: t for t in json.loads((ROOT / "data/ground_truth.json").read_text())["incidents"]}


class Investigate(BaseModel):
    incident: str
    memory: bool = True


class Ask(BaseModel):
    question: str


class Resolve(BaseModel):
    incident: str


@app.get("/api/health")
def health():
    return dict(ok=session.graph.ro_query("MATCH (n) RETURN count(n)").result_set[0][0] > 0)


@app.get("/api/incidents")
def incidents():
    return run(session.graph, "list_incidents")


@app.post("/api/investigate")
def do_investigate(req: Investigate):
    if not run(session.graph, "incident_context", incident=req.incident):
        raise HTTPException(404, "unknown incident")
    return investigate(session, req.incident, req.memory)


@app.post("/api/ask")
def do_ask(req: Ask):
    return ask(session, req.question[:300])


@app.post("/api/resolve")
def do_resolve(req: Resolve):
    """Demo action: the team confirms the root cause (taken from ground truth), so memory can learn it."""
    t = _truth().get(req.incident)
    if not t:
        raise HTTPException(404, "unknown incident")
    msg = run(session.graph, "commit_message", commit=t["root_cause_commit"])[0]["msg"]
    resolve(session, req.incident, t["root_cause_commit"], msg, t["ts"] + 3600)
    return dict(remembered=req.incident, commit=t["root_cause_commit"])


app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
