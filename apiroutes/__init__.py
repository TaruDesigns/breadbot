from fastapi import APIRouter

from .admin import router as adminrouter

api_router = APIRouter()
api_router.include_router(adminrouter, prefix="/admin", tags=["admin"])
