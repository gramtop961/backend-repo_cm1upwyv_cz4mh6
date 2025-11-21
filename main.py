import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Tree, Order

app = FastAPI(title="Christmas Trees Store API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Christmas Trees API running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# API models for responses
class TreeOut(Tree):
    id: str

# Seed some default trees if collection is empty
@app.post("/seed")
def seed_trees():
    if db is None:
        raise HTTPException(500, "Database not configured")

    count = db["tree"].count_documents({})
    if count > 0:
        return {"message": "Already seeded", "count": count}

    sample = [
        {
            "name": "Fraser Fir",
            "description": "Soft needles, strong branches, classic fragrance.",
            "price": 89.0,
            "size": "Medium",
            "image": "https://images.unsplash.com/photo-1543589077-5161fec4e69b?w=800&q=80",
            "in_stock": True,
        },
        {
            "name": "Douglas Fir",
            "description": "Full shape, sweet scent, budget friendly.",
            "price": 69.0,
            "size": "Small",
            "image": "https://images.unsplash.com/photo-1512070800541-1ff33acc2d64?w=800&q=80",
            "in_stock": True,
        },
        {
            "name": "Nordmann Fir",
            "description": "Excellent needle retention, deep green color.",
            "price": 119.0,
            "size": "Large",
            "image": "https://images.unsplash.com/photo-1484704849700-f032a568e944?w=800&q=80",
            "in_stock": True,
        },
    ]

    for item in sample:
        create_document("tree", item)

    return {"message": "Seeded", "count": len(sample)}

@app.get("/trees", response_model=List[TreeOut])
def list_trees():
    docs = get_documents("tree")
    out: List[TreeOut] = []
    for d in docs:
        d["id"] = str(d.get("_id"))
        d.pop("_id", None)
        out.append(TreeOut(**d))
    return out

class CreateOrder(BaseModel):
    order: Order

@app.post("/orders")
def create_order(payload: CreateOrder):
    if db is None:
        raise HTTPException(500, "Database not configured")

    order_data = payload.order.model_dump()

    for item in order_data.get("items", []):
        tree_id = item.get("tree_id")
        if not tree_id:
            raise HTTPException(400, "Missing tree_id in item")
        try:
            _ = db["tree"].find_one({"_id": ObjectId(tree_id)})
            if _ is None:
                raise HTTPException(400, f"Invalid tree_id: {tree_id}")
        except Exception:
            raise HTTPException(400, f"Invalid tree_id: {tree_id}")

    inserted_id = create_document("order", order_data)
    return {"message": "Order placed", "order_id": inserted_id}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
