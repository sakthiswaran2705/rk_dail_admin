from fastapi import APIRouter, Form, File, UploadFile, Query, HTTPException
from bson import ObjectId
from typing import List, Optional
from datetime import datetime
import os
import uuid

# --- DATABASE CONNECTION ---
from common_urldb import db

router = APIRouter()

# --- COLLECTIONS ---
col_shop = db["shop"]
col_city = db["city"]
col_category = db["category"]
col_user = db["user"]
col_offers = db["offers"]
col_jobs = db["jobs"]

# --- CONSTANTS ---
MEDIA_BASE = "media/shop"


# --- HELPER FUNCTIONS ---

def oid(x):
    """Safely converts ObjectId to string."""
    if isinstance(x, ObjectId):
        return str(x)
    return x


def serialize_date(d):
    """Safely converts datetime to ISO string."""
    if isinstance(d, datetime):
        return d.isoformat()
    return d


def find_user_by_phone_or_email(value: str):
    """Finds user by email or phone number to link CRUD operations."""
    if "@" in value:
        return col_user.find_one({"email": value})
    return col_user.find_one({"phonenumber": value})


# ==============================================================================
# 0. SEARCH APIS (REQUIRED FOR DROPDOWNS)
# ==============================================================================

@router.get("/city/search/")
def search_city(city_name: str = Query(...)):
    """Search cities by name (Case Insensitive)"""
    try:
        # Regex search for partial match
        query = {"city_name": {"$regex": city_name, "$options": "i"}}
        cities = list(col_city.find(query).limit(10))

        result = []
        for c in cities:
            result.append({
                "id": str(c["_id"]),
                "city_name": c.get("city_name"),
                "district": c.get("district"),
                "pincode": c.get("pincode"),
                "state": c.get("state")
            })
        return {"status": True, "data": result}
    except Exception as e:
        return {"status": False, "message": str(e)}


@router.get("/category/search/")
def search_category(category: str = Query(...)):
    """Search categories by name"""
    try:
        query = {"name": {"$regex": category, "$options": "i"}}
        cats = list(col_category.find(query).limit(10))

        result = []
        for c in cats:
            result.append({
                "id": str(c["_id"]),
                "name": c.get("name")
            })
        return {"status": True, "data": result}
    except Exception as e:
        return {"status": False, "message": str(e)}


# ==============================================================================
# 1. GET ALL SHOPS (Detailed Public View)
# ==============================================================================


@router.get("/shops/all/")
def get_all_shops():
    shops = list(col_shop.find({"status": "approved"}))
    result = []

    for s in shops:
        sid_str = str(s["_id"])

        # ---------------- CITY ----------------
        city_doc = None
        city_id_raw = s.get("city_id")
        if city_id_raw and ObjectId.is_valid(str(city_id_raw)):
            c = col_city.find_one({"_id": ObjectId(str(city_id_raw))})
            if c:
                city_doc = {
                    "id": str(c["_id"]),
                    "city_name": c.get("city_name"),
                    "district": c.get("district"),
                    "pincode": c.get("pincode"),
                    "state": c.get("state")
                }

        # ---------------- USER ----------------
        user_doc = None
        user_id_raw = s.get("user_id")
        try:
            if isinstance(user_id_raw, dict) and "$oid" in user_id_raw:
                uid = ObjectId(user_id_raw["$oid"])
            elif ObjectId.is_valid(str(user_id_raw)):
                uid = ObjectId(str(user_id_raw))
            else:
                uid = None

            if uid:
                u = col_user.find_one({"_id": uid})
                if u:
                    user_doc = {
                        "id": str(u["_id"]),
                        "name": f"{u.get('firstname','')} {u.get('lastname','')}".strip(),
                        "phonenumber": u.get("phonenumber")
                    }
        except:
            pass

        # ---------------- CATEGORIES ----------------
        category_list = []
        cat_ids = [
            ObjectId(c) for c in s.get("category", [])
            if ObjectId.is_valid(str(c))
        ]
        if cat_ids:
            for c in col_category.find({"_id": {"$in": cat_ids}}):
                category_list.append({
                    "id": str(c["_id"]),
                    "name": c.get("name")
                })

        # ---------------- IMAGES (NORMALIZED) ----------------
        images_list = []

        # Main image
        if s.get("main_image"):
            images_list.append({
                "type": "main",
                "url": s["main_image"]   # media/shop/<shop_id>/main/<file>
            })

        # Gallery images
        for m in s.get("media", []):
            if isinstance(m, dict) and m.get("path"):
                images_list.append({
                    "type": m.get("type", "image"),
                    "url": m["path"]       # media/shop/<shop_id>/images/<file>
                })

        # ---------------- OFFERS ----------------
        offer_list = []
        offer_doc = col_offers.find_one({"shop_id": sid_str})
        if offer_doc:
            for item in offer_doc.get("offers", []):
                if item.get("status") == "approved":
                    offer_list.append({
                        "offer_id": item.get("offer_id"),
                        "title": item.get("title"),
                        "description": item.get("description"),
                        "percentage": item.get("percentage"),
                        "start_date": item.get("start_date"),
                        "end_date": item.get("end_date"),
                        "fee": item.get("fee"),
                        "image_url": item.get("media_path")
                    })

        # ---------------- FINAL OBJECT ----------------
        result.append({
            "shop_id": sid_str,
            "shop_name": s.get("shop_name"),
            "description": s.get("description"),
            "address": s.get("address"),
            "phone_number": s.get("phone_number"),
            "email": s.get("email"),
            "landmark": s.get("landmark"),
            "keywords": s.get("keywords", []),
            "city": city_doc,
            "user": user_doc,
            "categories": category_list,
            "images": images_list,
            "offers": offer_list
        })

    return {"status": True, "data": result}



@router.post("/add_shop_custom/")
def add_shop_custom(
        phoneid: str = Form(...),
        shop_name: str = Form(...),
        description: str = Form(...),
        address: str = Form(...),
        phone_number: str = Form(...),
        email: str = Form(...),
        landmark: str = Form(...),
        category_list: str = Form(...),
        city_name: str = Form(...),
        district: str = Form(None),
        state: str = Form(None),
        photos: List[UploadFile] = File(None),
        main_image: UploadFile = File(None),
        keywords: str = Form(...),
        pincode: str = Form(None)
):
    # 1. Validate User
    user = find_user_by_phone_or_email(phoneid)
    if not user:
        return {"status": False, "message": "User not found"}
    user_id = str(user["_id"])

    # 2. RESOLVE CITY NAME TO CITY ID
    city_doc = col_city.find_one({"city_name": {"$regex": f"^{city_name.strip()}$", "$options": "i"}})

    if city_doc:
        city_id = str(city_doc["_id"])
    else:
        return {"status": False, "message": f"City '{city_name}' not found. Please use suggestions."}

    # 3. Process Categories
    cat_ids = []
    for raw in category_list.split(","):
        name = raw.strip()
        if not name: continue
        cat = col_category.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
        if cat:
            cat_ids.append(str(cat["_id"]))

    # 4. Insert Shop
    insert_res = col_shop.insert_one({
        "shop_name": shop_name,
        "description": description,
        "address": address,
        "phone_number": phone_number,
        "email": email,
        "landmark": landmark,
        "category": cat_ids,
        "city_id": city_id,
        "keywords": [k.strip() for k in keywords.split(",") if k.strip()],
        "user_id": user_id,
        "media": [],
        "main_image": None,
        "status": "pending",  # Or 'approved' if you want direct approval
        "created_at": datetime.utcnow()
    })

    shop_id = str(insert_res.inserted_id)

    # 5. Handle Images
    update_data = {}

    # Main Image
    if main_image:
        main_dir = os.path.join(MEDIA_BASE, shop_id, "main")
        os.makedirs(main_dir, exist_ok=True)
        ext = main_image.filename.split(".")[-1]
        fname = f"{uuid.uuid4()}.{ext}"
        path = os.path.join(main_dir, fname)
        with open(path, "wb") as f:
            f.write(main_image.file.read())
        update_data["main_image"] = f"{MEDIA_BASE}/{shop_id}/main/{fname}"

    # Gallery Images
    media_list = []
    if photos:
        img_dir = os.path.join(MEDIA_BASE, shop_id, "images")
        os.makedirs(img_dir, exist_ok=True)
        for p in photos:
            if p.content_type.startswith("image"):
                ext = p.filename.split(".")[-1]
                fname = f"{uuid.uuid4()}.{ext}"
                path = os.path.join(img_dir, fname)
                with open(path, "wb") as f:
                    f.write(p.file.read())
                media_list.append({"type": "image", "path": f"{MEDIA_BASE}/{shop_id}/images/{fname}"})

    if media_list:
        update_data["media"] = media_list

    if update_data:
        col_shop.update_one({"_id": ObjectId(shop_id)}, {"$set": update_data})

    return {"status": True, "message": "Shop added successfully", "shop_id": shop_id}


@router.post("/update_shop/")
def update_shop_custom(
        shop_id: str = Form(...),
        shop_name: str = Form(None),
        description: str = Form(None),
        address: str = Form(None),
        phone_number: str = Form(None),
        email: str = Form(None),
        landmark: str = Form(None),
        city_name: str = Form(None),
        keywords: str = Form(None),
        photos: List[UploadFile] = File(None),
        main_image: UploadFile = File(None)
):
    try:
        soid = ObjectId(shop_id)
    except:
        return {"status": False, "message": "Invalid Shop ID"}

    shop = col_shop.find_one({"_id": soid})
    if not shop:
        return {"status": False, "message": "Shop not found"}

    update = {}
    if shop_name: update["shop_name"] = shop_name
    if description: update["description"] = description
    if address: update["address"] = address
    if phone_number: update["phone_number"] = phone_number
    if email: update["email"] = email
    if landmark: update["landmark"] = landmark
    if keywords: update["keywords"] = [k.strip() for k in keywords.split(",")]

    # City Name Update
    if city_name:
        city_doc = col_city.find_one({"city_name": {"$regex": f"^{city_name.strip()}$", "$options": "i"}})
        if city_doc:
            update["city_id"] = str(city_doc["_id"])

    # 1. Main Image Update
    if main_image:
        main_dir = os.path.join(MEDIA_BASE, shop_id, "main")
        os.makedirs(main_dir, exist_ok=True)

        # Remove old main image
        old_main = shop.get("main_image")
        if old_main and os.path.exists(old_main):
            try:
                os.remove(old_main)
            except:
                pass

        ext = main_image.filename.split(".")[-1]
        fname = f"{uuid.uuid4()}.{ext}"
        path = os.path.join(main_dir, fname)
        with open(path, "wb") as f:
            f.write(main_image.file.read())
        update["main_image"] = f"{MEDIA_BASE}/{shop_id}/main/{fname}"

    # 2. Append new photos to existing media
    if photos:
        img_dir = os.path.join(MEDIA_BASE, shop_id, "images")
        os.makedirs(img_dir, exist_ok=True)
        current_media = shop.get("media", [])

        for p in photos:
            if p.content_type.startswith("image"):
                ext = p.filename.split(".")[-1]
                fname = f"{uuid.uuid4()}.{ext}"
                path = os.path.join(img_dir, fname)
                with open(path, "wb") as f:
                    f.write(p.file.read())
                current_media.append({"type": "image", "path": f"{MEDIA_BASE}/{shop_id}/images/{fname}"})

        update["media"] = current_media

    if update:
        col_shop.update_one({"_id": soid}, {"$set": update})

    return {"status": True, "message": "Shop updated successfully"}


@router.delete("/shops/delete/{shop_id}")
def delete_shop(shop_id: str):
    try:
        oidv = ObjectId(shop_id)
    except:
        return {"status": False, "message": "Invalid shop id"}

    res = col_shop.delete_one({"_id": oidv})
    if res.deleted_count:
        # Cascade delete (Offers and Jobs)
        col_offers.delete_many({"shop_id": shop_id})
        col_jobs.delete_many({"shop_id": shop_id})
        return {"status": True, "message": "Shop, Offers and Jobs deleted"}

    return {"status": False, "message": "Shop not found"}


@router.post("/shop/photo/delete/")
def delete_shop_photo(shop_id: str = Form(...), photo_index: int = Form(...)):
    try:
        soid = ObjectId(shop_id)
    except:
        return {"status": False, "message": "Invalid shop id"}

    shop = col_shop.find_one({"_id": soid})
    if not shop:
        return {"status": False, "message": "Shop not found"}

    media_list = shop.get("media", [])

    if not (0 <= photo_index < len(media_list)):
        return {"status": False, "message": "Invalid photo index"}

    # Remove item at index (Updates DB immediately)
    media_list.pop(photo_index)
    col_shop.update_one({"_id": soid}, {"$set": {"media": media_list}})

    return {"status": True, "message": "Photo deleted"}


# ==============================================================================
# 3. OFFER MANAGEMENT
# ==============================================================================

@router.post("/add_offer_custom/")
async def add_offer_custom(
        phoneid: str = Form(...),
        target_shop: str = Form(...),
        title: str = Form(""),
        fee: str = Form(""),
        start_date: str = Form(""),
        end_date: str = Form(""),
        percentage: str = Form(""),
        description: str = Form(""),
        file: UploadFile = File(...)
):
    user = find_user_by_phone_or_email(phoneid)
    if not user:
        return {"status": False, "message": "User not found"}
    user_id = str(user["_id"])

    if file.content_type.startswith("image"):
        folder, media_type = "images", "image"
    elif file.content_type.startswith("video"):
        folder, media_type = "videos", "video"
    else:
        return {"status": False, "message": "Invalid file type"}

    offer_id = str(ObjectId())

    save_dir = os.path.join(MEDIA_BASE, target_shop, "offers", folder)
    os.makedirs(save_dir, exist_ok=True)

    ext = file.filename.split(".")[-1]
    filename = f"{offer_id}.{ext}"
    full_path = os.path.join(save_dir, filename)

    with open(full_path, "wb") as f:
        f.write(await file.read())

    offer_obj = {
        "offer_id": offer_id,
        "media_type": media_type,
        "media_path": f"{MEDIA_BASE}/{target_shop}/offers/{folder}/{filename}",
        "filename": filename,
        "title": title,
        "fee": fee,
        "start_date": start_date,
        "end_date": end_date,
        "percentage": percentage,
        "description": description,
        "uploaded_at": datetime.utcnow(),
        "status": "pending"  # Or approved
    }

    if col_offers.find_one({"shop_id": target_shop}):
        col_offers.update_one({"shop_id": target_shop}, {"$push": {"offers": offer_obj}})
    else:
        col_offers.insert_one({
            "shop_id": target_shop,
            "user_id": user_id,
            "offers": [offer_obj],
            "status": "pending",
            "created_at": datetime.utcnow()
        })

    return {"status": True, "message": "Offer added successfully"}


@router.post("/delete_offer_custom/")
def delete_offer_custom(offer_id: str = Form(...)):
    """Removes a specific offer object from the 'offers' array using $pull"""
    try:
        # Find document containing the offer
        doc = col_offers.find_one({"offers.offer_id": offer_id})
        if not doc:
            return {"status": False, "message": "Offer not found"}

        # Pull from array
        col_offers.update_one(
            {"_id": doc["_id"]},
            {"$pull": {"offers": {"offer_id": offer_id}}}
        )
        return {"status": True, "message": "Offer deleted successfully"}
    except Exception as e:
        return {"status": False, "message": str(e)}


# ==============================================================================
# 4. JOB MANAGEMENT
# ==============================================================================

from bson import ObjectId
from fastapi import APIRouter, Form, HTTPException
from datetime import datetime


# router = APIRouter() # Assuming you have this

@router.post("/jobs/add/")
def add_job(
        phoneid: str = Form(...),
        job_title: str = Form(...),
        job_description: str = Form(...),
        address: str = Form(None),  # Added Address
        salary: int = Form(...),
        work_start_time: str = Form(...),
        work_end_time: str = Form(...),
        city_id: str = Form(...),
        gender: str = Form("Any"),
        experience: str = Form("Fresher")
):
    try:
        user = find_user_by_phone_or_email(phoneid)
        if not user:
            return {"status": False, "message": "User not found"}

        if not ObjectId.is_valid(city_id):
            return {"status": False, "message": "Invalid city id"}

        city = col_city.find_one({"_id": ObjectId(city_id)})
        if not city:
            return {"status": False, "message": "City not found"}

        job = {
            "user_id": ObjectId(user["_id"]),
            "job_title": job_title,
            "job_description": job_description,
            "address": address,  # Save Address
            "salary": salary,
            "work_start_time": work_start_time,
            "work_end_time": work_end_time,
            "gender": gender,
            "experience": experience,
            "city_id": ObjectId(city_id),
            "city_name": city.get("city_name"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        col_jobs.insert_one(job)
        return {"status": True, "message": "Job added successfully"}

    except Exception as e:
        print("Add job error:", e)
        return {"status": False, "message": "Failed to add job"}


from typing import Optional


@router.post("/job/update/{job_id}/")
def update_job(
        job_id: str,
        # phoneid: str = Form(...),  <-- CRITICAL: Ensure this is REMOVED
        job_title: str = Form(None),
        job_description: str = Form(None),
        salary: str = Form(None),  # Changed to str to handle empty inputs safely
        address: str = Form(None),
        work_start_time: str = Form(None),
        work_end_time: str = Form(None),
        city_id: str = Form(None),
        gender: str = Form(None),
        experience: str = Form(None)
):
    try:
        if not ObjectId.is_valid(job_id):
            return {"status": False, "message": "Invalid Job ID"}

        j_oid = ObjectId(job_id)

        # Check if job exists
        job = col_jobs.find_one({"_id": j_oid})
        if not job:
            return {"status": False, "message": "Job not found"}

        # Build Update Dictionary
        update_data = {}
        if job_title: update_data["job_title"] = job_title
        if job_description: update_data["job_description"] = job_description

        # Safe Salary Conversion
        if salary and salary.strip():
            try:
                update_data["salary"] = int(salary)
            except ValueError:
                pass  # Ignore invalid numbers

        if address: update_data["address"] = address
        if work_start_time: update_data["work_start_time"] = work_start_time
        if work_end_time: update_data["work_end_time"] = work_end_time
        if gender: update_data["gender"] = gender
        if experience: update_data["experience"] = experience

        if city_id and ObjectId.is_valid(city_id):
            c_obj = col_city.find_one({"_id": ObjectId(city_id)})
            if c_obj:
                update_data["city_id"] = ObjectId(city_id)
                update_data["city_name"] = c_obj.get("city_name")

        update_data["updated_at"] = datetime.utcnow()

        col_jobs.update_one({"_id": j_oid}, {"$set": update_data})

        return {"status": True, "message": "Job updated successfully"}

    except Exception as e:
        print(f"Update Error: {e}")
        return {"status": False, "message": "Failed to update job"}
@router.get("/jobs/all/")
def get_all_jobs():
    try:
        jobs = list(col_jobs.find().sort("created_at", -1))
        for j in jobs:
            j["_id"] = str(j["_id"])
            j["user_id"] = str(j["user_id"])
            j["city_id"] = str(j["city_id"])
        return {"status": True, "data": jobs}
    except Exception as e:
        print("Fetch jobs error:", e)
        return {"status": False, "message": "Failed to fetch jobs"}


@router.get("/city/search/")
def search_city(city_name: str = Query(...)):
    """Search cities by name (Case Insensitive)"""
    try:
        # Regex search for partial match
        query = {"city_name": {"$regex": city_name, "$options": "i"}}
        cities = list(col_city.find(query).limit(10))

        result = []
        for c in cities:
            result.append({
                "id": str(c["_id"]),
                "city_name": c.get("city_name"),
                "district": c.get("district"),
                "pincode": c.get("pincode"),
                "state": c.get("state")
            })
        return {"status": True, "data": result}
    except Exception as e:
        return {"status": False, "message": str(e)}



@router.delete("/jobs/delete/{job_id}")
def delete_job(job_id: str):
    if ObjectId.is_valid(job_id):
        col_jobs.delete_one({"_id": ObjectId(job_id)})
        return {"status": True, "message": "Deleted"}
    return {"status": False, "message": "Invalid ID"}
