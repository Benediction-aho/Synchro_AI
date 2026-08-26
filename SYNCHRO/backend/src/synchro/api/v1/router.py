from fastapi import APIRouter

from synchro.api.v1.endpoints import auth, health
from synchro.core.config import get_settings

settings = get_settings()
router = APIRouter(prefix=settings.api_v1_prefix)
router.include_router(auth.router)
router.include_router(health.router, tags=["health"])
