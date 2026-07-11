"""Budget Intelligence FastAPI backend — Phase 4+5 complete."""
import logging
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import init_db
from api.routes import (
    transactions, upload, rates, income, subscriptions,
    analysis, macro, scenarios, forecasts, reports, chat,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database on startup
init_db()

app = FastAPI(
    title="Budget Intelligence API",
    version="3.0.0",
    description="Personal finance analysis backend for Venezuela dual-currency finances",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers
app.include_router(transactions.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(rates.router, prefix="/api")
app.include_router(income.router, prefix="/api")
app.include_router(subscriptions.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(macro.router, prefix="/api")
app.include_router(scenarios.router, prefix="/api")
app.include_router(forecasts.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "5.0.0", "phase": 5}


@app.on_event("startup")
async def startup_event():
    """Run rate sync on startup (non-blocking)."""
    from core.config import settings
    if settings.rate_source != "local_only":
        def _sync():
            try:
                from jobs.rate_sync import sync_rates
                result = sync_rates()
                logger.info(f"Startup rate sync: {result}")
            except Exception as e:
                logger.warning(f"Startup rate sync failed: {e}")
        threading.Thread(target=_sync, daemon=True).start()
