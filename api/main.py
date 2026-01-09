from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from api.routes import admin_ui

app = FastAPI()

# Static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="frontend/assets"), name="static")

# Admin dashboard routes
app.include_router(admin_ui.router)
