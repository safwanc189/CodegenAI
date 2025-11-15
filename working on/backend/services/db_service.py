# =============================================================================
# 📦 db_service.py
# -----------------------------------------------------------------------------
# Handles MongoDB connection and helper functions for saving/fetching projects
# =============================================================================

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

# -----------------------------------------------------------------------------
# 🔌 MongoDB Connection Setup
# -----------------------------------------------------------------------------
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "synopsis_ai_db"
COLLECTION_NAME = "projects"

# Create MongoDB client and get the collection
client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

print(f"🗄️ Connected to MongoDB: {MONGO_URI} → DB: {DB_NAME}, Collection: {COLLECTION_NAME}")

# -----------------------------------------------------------------------------
# 💾 Save Project
# -----------------------------------------------------------------------------
async def save_project(project_data: dict) -> str:
    """
    Saves a project document into MongoDB.
    Returns the inserted document ID.
    """
    result = await collection.insert_one(project_data)
    print(f"✅ [DB] Project saved with _id: {result.inserted_id}")
    return str(result.inserted_id)

# -----------------------------------------------------------------------------
# 📤 Get Project by ID
# -----------------------------------------------------------------------------
async def get_project(project_id: str):
    """
    Fetch a single project document by its ObjectId.
    Returns a JSON-safe dict.
    """
    try:
        doc = await collection.find_one({"_id": ObjectId(project_id)})
        if not doc:
            print("⚠️ No project found with that ID")
            return None

        # Convert ObjectId to string for frontend use
        doc["_id"] = str(doc["_id"])
        print(f"📦 [DB] Retrieved project: {doc['title']}")
        return doc

    except Exception as e:
        print(f"❌ [DB ERROR] {str(e)}")
        return None
