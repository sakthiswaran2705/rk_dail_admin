from fastapi import APIRouter, HTTPException
from bson import ObjectId
from common_urldb import db
from datetime import datetime

router = APIRouter(tags=["Reviews"])

col_reviews = db["reviews"]

# Convert ObjectId → String
def serialize_review(r):
    r["_id"] = str(r["_id"])
    return r



@router.get("/reviews/all/")
def get_reviews(shop_id: str):
    try:
        reviews = list(col_reviews.find({"shop_id": shop_id}))
        return {"status": True, "data": [serialize_review(r) for r in reviews]}
    except Exception as e:
        return {"status": False, "error": str(e)}


# DELETE REVIEW
@router.delete("/reviews/delete/{review_id}")
def delete_review(review_id: str):
    try:
        if not ObjectId.is_valid(review_id):
            raise HTTPException(status_code=400, detail="Invalid review ID")

        col_reviews.delete_one({"_id": ObjectId(review_id)})
        return {"status": True, "message": "Review deleted"}

    except Exception as e:
        return {"status": False, "error": str(e)}
