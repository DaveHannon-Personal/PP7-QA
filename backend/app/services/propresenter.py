"""
ProPresenter 7 API client service.

Wraps the official PP7 REST API (default: http://localhost:50001).
All methods are async and use httpx.AsyncClient.

Configuration is loaded from the DB at call time so that Settings UI
changes take effect immediately without restarting the app.
"""
from __future__ import annotations

import httpx
from sqlalchemy.orm import Session
from app.models.config import AppConfig
from app.config import settings


def _get_base_url(db: Session) -> str:
    """Return the current PP7 base URL from DB config (falls back to env settings)."""
    cfg = db.query(AppConfig).filter(AppConfig.id == 1).first()
    if cfg:
        return f"{cfg.propresenter_url}:{cfg.propresenter_port}"
    return f"{settings.propresenter_url}:{settings.propresenter_port}"


def _client(base_url: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=base_url, timeout=10.0)


# ── Connection / Status ──────────────────────────────────────────────────────

async def get_version(db: Session) -> dict:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.get("/version")
        r.raise_for_status()
        return r.json()


async def get_status_layers(db: Session) -> dict:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.get("/v1/status/layers")
        r.raise_for_status()
        return r.json()


# ── Playlists ────────────────────────────────────────────────────────────────

async def get_playlists(db: Session) -> list[dict]:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.get("/v1/playlists")
        r.raise_for_status()
        return r.json()


async def get_playlist(db: Session, playlist_id: str) -> dict:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.get(f"/v1/playlist/{playlist_id}")
        r.raise_for_status()
        return r.json()


# ── Presentations ────────────────────────────────────────────────────────────

async def get_presentation(db: Session, uuid: str) -> dict:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.get(f"/v1/presentation/{uuid}")
        r.raise_for_status()
        return r.json()


async def get_active_presentation(db: Session) -> dict:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.get("/v1/presentation/active")
        r.raise_for_status()
        return r.json()


# ── Libraries ────────────────────────────────────────────────────────────────

async def get_libraries(db: Session) -> list[dict]:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.get("/v1/libraries")
        r.raise_for_status()
        return r.json()


async def get_library(db: Session, library_id: str) -> list[dict]:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.get(f"/v1/library/{library_id}")
        r.raise_for_status()
        return r.json()


# ── Looks ────────────────────────────────────────────────────────────────────

async def get_looks(db: Session) -> list[dict]:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.get("/v1/looks")
        r.raise_for_status()
        return r.json()


async def get_look(db: Session, look_id: str) -> dict:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.get(f"/v1/look/{look_id}")
        r.raise_for_status()
        return r.json()


async def get_current_look(db: Session) -> dict:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.get("/v1/look/current")
        r.raise_for_status()
        return r.json()


async def set_look(db: Session, look_id: str, data: dict) -> dict:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.put(f"/v1/look/{look_id}", json=data)
        r.raise_for_status()
        return r.json()


async def trigger_look(db: Session, look_id: str) -> None:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.get(f"/v1/look/{look_id}/trigger")
        r.raise_for_status()


# ── Themes ───────────────────────────────────────────────────────────────────

async def get_themes(db: Session) -> list[dict]:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.get("/v1/themes")
        r.raise_for_status()
        return r.json()


async def get_theme(db: Session, theme_id: str) -> dict:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.get(f"/v1/theme/{theme_id}")
        r.raise_for_status()
        return r.json()


async def set_theme_slide(db: Session, theme_id: str, theme_slide: str, data: dict) -> dict:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.put(f"/v1/theme/{theme_id}/slides/{theme_slide}", json=data)
        r.raise_for_status()
        return r.json()


# ── Props ────────────────────────────────────────────────────────────────────

async def get_props(db: Session) -> list[dict]:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.get("/v1/props")
        r.raise_for_status()
        return r.json()


async def get_prop(db: Session, prop_id: str) -> dict:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.get(f"/v1/prop/{prop_id}")
        r.raise_for_status()
        return r.json()


async def set_prop(db: Session, prop_id: str, data: dict) -> dict:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.put(f"/v1/prop/{prop_id}", json=data)
        r.raise_for_status()
        return r.json()


# ── Macros ───────────────────────────────────────────────────────────────────

async def get_macros(db: Session) -> list[dict]:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.get("/v1/macros")
        r.raise_for_status()
        return r.json()


async def get_macro(db: Session, macro_id: str) -> dict:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.get(f"/v1/macro/{macro_id}")
        r.raise_for_status()
        return r.json()


async def set_macro(db: Session, macro_id: str, data: dict) -> dict:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.put(f"/v1/macro/{macro_id}", json=data)
        r.raise_for_status()
        return r.json()


# ── Messages ─────────────────────────────────────────────────────────────────

async def get_messages(db: Session) -> list[dict]:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.get("/v1/messages")
        r.raise_for_status()
        return r.json()


async def set_message(db: Session, message_id: str, data: dict) -> dict:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.put(f"/v1/message/{message_id}", json=data)
        r.raise_for_status()
        return r.json()


# ── Groups ───────────────────────────────────────────────────────────────────

async def get_groups(db: Session) -> list[dict]:
    base = _get_base_url(db)
    async with _client(base) as c:
        r = await c.get("/v1/groups")
        r.raise_for_status()
        return r.json()
