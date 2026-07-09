"""
PP7-QA FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app.routers import (
    settings_router,
    rules_router,
    profiles_router,
    audit_router,
    chat_router,
)

app = FastAPI(
    title="PP7-QA API",
    description=(
        "AI-powered QA engine for ProPresenter 7. "
        "Define compliance rules, audit presentations, and auto-fix violations."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow the Next.js frontend (and local dev) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(settings_router)
app.include_router(rules_router)
app.include_router(profiles_router)
app.include_router(audit_router)
app.include_router(chat_router)


@app.on_event("startup")
def on_startup():
    """Initialize the SQLite database on first start."""
    init_db()


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/", tags=["health"])
def root():
    return {"message": "PP7-QA API is running. See /docs for the API reference."}
