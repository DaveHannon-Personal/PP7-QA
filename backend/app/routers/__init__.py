from app.routers.settings import router as settings_router
from app.routers.rules import router as rules_router
from app.routers.profiles import router as profiles_router
from app.routers.audit import router as audit_router
from app.routers.chat import router as chat_router

__all__ = [
    "settings_router",
    "rules_router",
    "profiles_router",
    "audit_router",
    "chat_router",
]
