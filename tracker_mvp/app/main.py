from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.db import init_db
from app.routes import agents, documents, events, links, p3, pages, phases, procurement, projects, risks, settings, sites, tasks, workspace


app = FastAPI(title="АСУТП Tracker MVP")
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(pages.router)
app.include_router(workspace.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(documents.router)
app.include_router(events.router)
app.include_router(p3.router)
app.include_router(phases.router)
app.include_router(sites.router)
app.include_router(procurement.router)
app.include_router(risks.router)
app.include_router(links.router)
app.include_router(agents.router)
app.include_router(settings.router)
