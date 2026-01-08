# api/routes/admin_ui.py
import os
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from api.config import project_dir   # adjust if needed

router = APIRouter()

# Correct templates directory -> frontend/dashboard/
templates = Jinja2Templates(
    directory=os.path.join(project_dir, "frontend", "dashboard")
)

@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})
