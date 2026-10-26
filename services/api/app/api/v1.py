from fastapi import APIRouter

from app.places.router import router as places_router
from app.schedules.router import router as schedules_router
from app.suggestions.router import router as suggestions_router
from app.users.router import router as users_router
from app.visits.router import router as visits_router

v1_router = APIRouter(prefix="/v1")

v1_router.include_router(users_router)
v1_router.include_router(schedules_router)
v1_router.include_router(places_router)
v1_router.include_router(suggestions_router)
v1_router.include_router(visits_router)
