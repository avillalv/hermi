"""The /v1 router. Module routers (auth in WF-013.2, trips in WF-019) are included here."""

from fastapi import APIRouter

from hermi.modules.auth.router import router as auth_router
from hermi.modules.billing.router import router as billing_router
from hermi.modules.collaboration.router import router as collaboration_router
from hermi.modules.flights.alerts_api import router as alerts_router
from hermi.modules.flights.choice import router as choice_router
from hermi.modules.flights.reads import router as reads_router
from hermi.modules.flights.router import router as flights_router
from hermi.modules.geo.router import router as geo_router
from hermi.modules.itinerary.router import router as itinerary_router
from hermi.modules.lodging.router import router as lodging_router
from hermi.modules.notifications.router import router as notifications_router
from hermi.modules.places.router import router as places_router
from hermi.modules.trips.notes import router as notes_router
from hermi.modules.trips.people import router as people_router
from hermi.modules.trips.router import router as trips_router
from hermi.modules.trips.samples import router as samples_router

router = APIRouter(prefix="/v1")
router.include_router(auth_router)
router.include_router(trips_router)
router.include_router(geo_router)
router.include_router(billing_router)
router.include_router(people_router)
router.include_router(collaboration_router)
router.include_router(flights_router)
router.include_router(reads_router)
router.include_router(choice_router)
router.include_router(alerts_router)
router.include_router(itinerary_router)
router.include_router(places_router)
router.include_router(lodging_router)
router.include_router(notes_router)
router.include_router(samples_router)
router.include_router(notifications_router)
