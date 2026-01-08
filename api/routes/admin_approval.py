# admin_approval.py
from fastapi import APIRouter
from bson import ObjectId
from common_urldb import db

router = APIRouter()

col_shop = db["shop"]
col_category = db["category"]
col_city = db["city"]
def oid(x):
    return str(x) if isinstance(x, ObjectId) else x

@router.get("/pending_shops/")
def pending_shops():
    shops = []

    cursor = col_shop.find({"status": "pending"})

    for s in cursor:

        # CLEAN BASE SHOP DOC
        s_clean = {k: oid(v) for k, v in s.items()}

        # ---------------------------
        # CATEGORY DETAILS
        # ---------------------------
        categories = []
        for cid in s.get("category", []):   # category = list of IDs
            try:
                c = col_category.find_one({"_id": ObjectId(cid)})
                if c:
                    categories.append({
                        "_id": oid(c["_id"]),
                        "name": c.get("name")
                    })
            except:
                pass

        s_clean["categories"] = categories  # add to final output
        # CITY DETAILS
        city_doc = None
        if s.get("city_id"):
            try:
                city = col_city.find_one({"_id": ObjectId(s["city_id"])})
                if city:
                    city_doc = {
                        "_id": oid(city["_id"]),
                        "name": city.get("city_name")
                    }
            except:
                city_doc = None

        s_clean["city"] = city_doc  # add city to final output

        # ADD TO LIST
        shops.append(s_clean)

    return {"status": True, "data": shops}


@router.get("/approve_shop")
def approve_shop(shop_id: str):

    try:
        oid = ObjectId(shop_id)
    except:
        return {"status": False, "message": "Invalid shop id"}

    # Update status ONLY
    col_shop.update_one({"_id": oid}, {"$set": {"status": "approved"}})

    return {"status": True, "message": "Shop Approved Successfully"}

@router.get("/rejected_shop")
def rejected_shop(shop_id: str):

    try:
        oid = ObjectId(shop_id)
    except:
        return {"status": False, "message": "Invalid shop ID"}

    shop = col_shop.find_one({"_id": oid})
    if not shop:
        return {"status": False, "message": "Shop not found"}

    col_shop.update_one(
        {"_id": oid},
        {"$set": {"status": "rejected"}}
    )

    return {"status": True, "message": "Shop Rejected Successfully"}


