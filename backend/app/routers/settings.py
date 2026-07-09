"""Settings router — GET and PUT the persisted ProPresenter + Ollama config."""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.config import AppConfig
from app.schemas.config import ConfigRead, ConfigUpdate, ConnectionStatus
from app.config import settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _get_or_create_config(db: Session) -> AppConfig:
    cfg = db.query(AppConfig).filter(AppConfig.id == 1).first()
    if not cfg:
        cfg = AppConfig(
            id=1,
            propresenter_url=settings.propresenter_url,
            propresenter_port=settings.propresenter_port,
            ollama_url=settings.ollama_url,
            ollama_model=settings.ollama_model,
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


@router.get("", response_model=ConfigRead)
def get_config(db: Session = Depends(get_db)):
    return _get_or_create_config(db)


@router.put("", response_model=ConfigRead)
def update_config(body: ConfigUpdate, db: Session = Depends(get_db)):
    cfg = _get_or_create_config(db)
    if body.propresenter_url is not None:
        cfg.propresenter_url = body.propresenter_url
    if body.propresenter_port is not None:
        cfg.propresenter_port = body.propresenter_port
    if body.ollama_url is not None:
        cfg.ollama_url = body.ollama_url
    if body.ollama_model is not None:
        cfg.ollama_model = body.ollama_model
    db.commit()
    db.refresh(cfg)
    return cfg


@router.get("/status", response_model=ConnectionStatus)
async def connection_status(db: Session = Depends(get_db)):
    cfg = _get_or_create_config(db)
    pp7_base = f"{cfg.propresenter_url}:{cfg.propresenter_port}"

    # Check ProPresenter
    pp7_connected = False
    pp7_version = None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{pp7_base}/version")
            if r.status_code == 200:
                data = r.json()
                pp7_connected = True
                pp7_version = data.get("name") or data.get("version") or "connected"
    except Exception:
        pass

    # Check Ollama
    ollama_connected = False
    ollama_models: list[str] = []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{cfg.ollama_url}/v1/models")
            if r.status_code == 200:
                ollama_connected = True
                data = r.json()
                ollama_models = [m["id"] for m in data.get("data", [])]
    except Exception:
        pass

    return ConnectionStatus(
        propresenter_connected=pp7_connected,
        propresenter_version=pp7_version,
        ollama_connected=ollama_connected,
        ollama_models=ollama_models,
    )
