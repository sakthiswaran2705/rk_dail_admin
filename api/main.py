import os
import sys
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import itsdangerous
# ======================================================
# PATH FIX
# ======================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(BASE_DIR)
sys.path.append(ROOT_DIR)

# ======================================================
# IMPORT ROUTERS
# ======================================================
from .routes.adminreviews import router as reviewrouter
from city_creation import router as city_router
from category_creation import router as category_router
from .routes.auth import session as session_router
from .routes.dashboard import dashboard as dashboard_router
from .routes.admin_approval import router as admin_approval_router
from .routes.admin_offer_approval import router as offer_approval_router
from .routes.admin_ui import router as admin_ui_router
from .routes.all_shop_shown import router as all_shop_show
from .config import project_dir, setup_logging
from pathlib import Path
from .routes.admin_payments_dt import router as  payment_router

# ======================================================
# INIT APP
# ======================================================
app = FastAPI(docs_url="/docs", redoc_url="/redoc")


# ======================================================
# ENV & LOGGING
# ======================================================
load_dotenv()
setup_logging()
# ======================================================
# SESSION MIDDLEWARE
# ======================================================
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("CLIENT_SECRET"),
    max_age=30 * 24 * 60 * 60
)

# ======================================================
# STATIC FILES
# ======================================================

BASE_DIR = Path(__file__).resolve().parents[2]
MEDIA_ROOT = BASE_DIR / "media"


app.mount(
    "/media",
    StaticFiles(directory=str(MEDIA_ROOT)),
    name="media"
)


# FRONTEND ASSETS
app.mount(
    "/assets",
    StaticFiles(directory=os.path.join(project_dir, "frontend", "assets")),
    name="assets"
)
# ======================================================
# TEMPLATES
# ======================================================
templates = Jinja2Templates(
    directory=os.path.join(project_dir, "frontend", "dashboard")
)

# ======================================================
# ROUTES
# ======================================================
app.include_router(session_router)
app.include_router(dashboard_router)
app.include_router(admin_approval_router)
app.include_router(offer_approval_router)
app.include_router(admin_ui_router)
app.include_router(all_shop_show)
app.include_router(category_router)
app.include_router(city_router)
app.include_router(reviewrouter)
app.include_router(payment_router)