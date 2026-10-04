"""The /v1 router. Module routers (auth in WF-013.2, trips in WF-019) are included here."""

from fastapi import APIRouter

from hermi.modules.auth.router import router as auth_router

router = APIRouter(prefix="/v1")
router.include_router(auth_router)
