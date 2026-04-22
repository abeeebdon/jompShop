"""Helix Platform — FastAPI main server."""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

from db import db, close_db  # noqa: E402
from storage import init_storage  # noqa: E402
from seed import seed_if_empty  # noqa: E402

# Routers
from routes.auth_routes import router as auth_router  # noqa: E402
from routes.onboarding import router as onboarding_router  # noqa: E402
from routes.catalog import router as catalog_router  # noqa: E402
from routes.orders import router as orders_router  # noqa: E402
from routes.compliance import router as compliance_router  # noqa: E402
from routes.finance import router as finance_router  # noqa: E402
from routes.webhooks import router as webhooks_router  # noqa: E402
from routes.files import router as files_router  # noqa: E402
from routes.credit import router as credit_router  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
log = logging.getLogger("helix")

app = FastAPI(title="Helix Platform", version="1.0.0-mvp")


@app.get("/api")
async def root():
    return {
        "service": "Helix Platform",
        "version": "1.0.0-mvp",
        "anchor_env": os.environ.get("ANCHOR_ENV"),
        "status": "online",
    }


@app.on_event("startup")
async def _startup():
    try:
        init_storage()
    except Exception as e:
        log.warning("storage init failed (non-fatal): %s", e)
    try:
        await seed_if_empty()
    except Exception as e:
        log.exception("seed failed: %s", e)

    # indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("user_id", unique=True)
    await db.user_sessions.create_index("session_token")
    await db.businesses.create_index("id", unique=True)
    await db.businesses.create_index("owner_user_id")
    await db.products.create_index("id", unique=True)
    await db.orders.create_index("id", unique=True)
    await db.transactions.create_index("business_id")


@app.on_event("shutdown")
async def _shutdown():
    close_db()


# register routers
for r in (auth_router, onboarding_router, catalog_router, orders_router,
          compliance_router, finance_router, webhooks_router, files_router, credit_router):
    app.include_router(r)


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
