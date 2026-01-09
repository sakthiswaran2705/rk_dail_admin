from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="frontend/dashboard")

@router.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/admin")
def admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@router.get("/admin/offers")
def admin_offers(request: Request):
    return templates.TemplateResponse("admin_offers.html", {"request": request})

@router.get("/admin/payments")
def admin_payments(request: Request):
    return templates.TemplateResponse("admin_payments.html", {"request": request})

@router.get("/admin/reviews")
def admin_reviews(request: Request):
    return templates.TemplateResponse("admin_reviews.html", {"request": request})

@router.get("/admin/shops")
def all_shops(request: Request):
    return templates.TemplateResponse("all_shop.html", {"request": request})

@router.get("/admin/jobs")
def jobs(request: Request):
    return templates.TemplateResponse("jobs.html", {"request": request})

@router.get("/admin/history")
def payment_history(request: Request):
    return templates.TemplateResponse("payment_history.html", {"request": request})

@router.get("/admin/pending-offers")
def pending_offers(request: Request):
    return templates.TemplateResponse("pending_offers_page.html", {"request": request})

@router.get("/admin/profile")
def profile(request: Request):
    return templates.TemplateResponse("user-profile.html", {"request": request})
