from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from common_urldb import db
from bson import ObjectId
from datetime import datetime

router = APIRouter(tags=["Admin Payments"])

col_payments = db["payments"]
col_users = db["user"]

# -------------------------
# STATUS CALC
# -------------------------
def compute_status(expiry):
    if not isinstance(expiry, datetime):
        return "unknown"

    now = datetime.utcnow()

    if now > expiry:
        return "expired"
    elif (expiry - now).days <= 2:
        return "expiring"
    return "active"


# -------------------------
# LIST ACTIVE PAYMENTS (ADMIN)
# -------------------------
@router.get("/admin/payments/active/")
def get_active_payments():
    try:
        payments = list(col_payments.find().sort("created_at", -1))

        data = []

        for p in payments:
            expiry = p.get("expiry_date")
            status = compute_status(expiry)

            if status != "active":
                continue   # 🔥 only active

            user = col_users.find_one({"_id": ObjectId(p["user_id"])})

            data.append({
                "payment_id": p.get("payment_id"),
                "plan_name": p.get("plan_name"),
                "amount": p.get("amount"),
                "expiry_date": expiry.isoformat() if expiry else None,
                "status": status,
                "email": user.get("email") if user else "-",
                "phone": user.get("phonenumber") if user else "-"
            })

        return {"status": True, "data": data}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# -------------------------
# USER ALL PLANS (CLICK USER)
# -------------------------
@router.get("/admin/payments/user/")
def get_user_all_plans(q: str = Query(...)):
    try:
        user = col_users.find_one({
            "$or": [{"email": q}, {"phonenumber": q}]
        })

        if not user:
            return {"status": True, "data": []}

        payments = list(col_payments.find({
            "user_id": str(user["_id"])
        }).sort("created_at", -1))

        data = []
        for p in payments:
            expiry = p.get("expiry_date")
            data.append({
                "payment_id": p.get("payment_id"),
                "plan_name": p.get("plan_name"),
                "amount": p.get("amount"),
                "status": compute_status(expiry),
                "expiry_date": expiry.isoformat() if expiry else None,
                "created_at": p.get("created_at").isoformat() if isinstance(p.get("created_at"), datetime) else None
            })

        return {"status": True, "data": data}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# -------------------------
# DELETE PAYMENT (ADMIN)
# -------------------------
@router.delete("/admin/payments/delete/{payment_id}")
def delete_payment(payment_id: str):
    res = col_payments.delete_one({"payment_id": payment_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Payment not found")

    return {"status": True, "message": "Payment deleted"}
