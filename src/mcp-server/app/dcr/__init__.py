"""DCR (Dynamic Client Registration) emulation module."""

from app.dcr.client_detector import ClientDetector, ClientType
from app.dcr.client_registry import ClientRegistry
from app.dcr.endpoints import router as dcr_router

__all__ = [
    "ClientDetector",
    "ClientType",
    "ClientRegistry",
    "dcr_router",
]
