# admin_offer_approval.py

from fastapi import APIRouter, Form
from bson import ObjectId
from datetime import datetime

from common_urldb import db

router = APIRouter()

# Collections
col_shop = db["shop"]
col_offers = db["offers"]
col_user = db["user"]



# GET ALL PENDING OFFERS
@router.get("/pending_offers/")
def pending_offers():
    cursor = col_offers.find({})
    results = []

    for doc in cursor:
        shop_id = doc.get("shop_id")
        user_id = doc.get("user_id")

        shop_name = "Unknown Shop"
        owner_phone = "-"
        owner_email = "-"

        # SHOP
        shop_obj = col_shop.find_one({"_id": ObjectId(shop_id)}) if ObjectId.is_valid(shop_id) else col_shop.find_one({"_id": shop_id})
        if shop_obj:
            shop_name = shop_obj.get("shop_name", shop_name)

        # USER
        uobj = col_user.find_one({"_id": ObjectId(user_id)}) if ObjectId.is_valid(user_id) else col_user.find_one({"_id": user_id})
        if uobj:
            owner_phone = uobj.get("phonenumber", "-")
            owner_email = uobj.get("email", "-")

        # OFFERS
        for offer in doc.get("offers", []):
            if offer.get("status") == "pending":
                results.append({
                    "_id": offer.get("offer_id"),
                    "media_type": offer.get("media_type"),
                    "media_path": offer.get("media_path"),
                    "shop_name": shop_name,
                    "owner_phone": owner_phone,
                    "owner_email": owner_email,
                    "title": offer.get("title"),
                    "fee": offer.get("fee"),
                    "start_date": offer.get("start_date"),
                    "end_date": offer.get("end_date"),
                    "percentage": offer.get("percentage"),
                    "description": offer.get("description"),
                })

    return {"status": True, "data": results}


# APPROVE ONE OFFER
@router.post("/approve_offer/")
def approve_offer(offer_id: str = Form(...)):

    doc = col_offers.find_one({"offers.offer_id": offer_id})
    if not doc:
        return {"status": False, "message": "Offer not found"}

    # Update specific offer inside array
    col_offers.update_one(
        {"offers.offer_id": offer_id},
        {
            "$set": {
                "offers.$[item].status": "approved",
                "offers.$[item].approved_at": datetime.utcnow(),
            },
            "$unset": {
                "offers.$[item].rejected_at": ""
            }
        },
        array_filters=[{"item.offer_id": offer_id}]
    )

    # First-time approval: update parent document
    if doc.get("status") != "approved":
        col_offers.update_one(
            {"_id": doc["_id"]},
            {"$set": {"status": "approved"}}
        )

    return {"status": True, "message": "Offer approved"}


# REJECT ONE OFFER
@router.post("/reject_offer/")
def reject_offer(offer_id: str = Form(...)):

    doc = col_offers.find_one({"offers.offer_id": offer_id})
    if not doc:
        return {"status": False, "message": "Offer not found"}

    col_offers.update_one(
        {"offers.offer_id": offer_id},
        {
            "$set": {
                "offers.$[item].status": "rejected",
                "offers.$[item].rejected_at": datetime.utcnow(),
            },
            "$unset": {
                "offers.$[item].approved_at": ""
            }
        },
        array_filters=[{"item.offer_id": offer_id}]
    )

    return {"status": True, "message": "Offer Rejected Successfully"}
