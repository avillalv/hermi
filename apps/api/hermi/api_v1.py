"""The /v1 router. Module routers (auth in WF-013.2, trips in WF-019) are included here."""

from fastapi import APIRouter

from hermi.modules.auth.router import router as auth_router
from hermi.modules.geo.router import router as geo_router
from hermi.modules.trips.router import router as trips_router

router = APIRouter(prefix="/v1")
router.include_router(auth_router)
router.include_router(trips_router)
router.include_router(geo_router)
