# =============================================================================
# 🎯 SynopsisAI Backend (main.py)
# -----------------------------------------------------------------------------
# Handles:
#   ✅ Uploading project synopsis (text or file)
#   ✅ Parsing structured content (# Project Title, # Description, etc.)
#   ✅ Saving project data to MongoDB
#   ✅ Fetching project data (latest or by ID)
# =============================================================================

from fastapi import FastAPI, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import re
import json
from bson import ObjectId
from datetime import datetime

# 🔧 Import custom services
from services.synopsis_service import process_synopsis
from services.db_service import save_project, get_project, collection  # Ensure collection imported here


# =============================================================================
# 🌐 FastAPI Configuration
# =============================================================================
app = FastAPI(title="SynopsisAI Backend")

# Enable CORS for frontend communication (e.g., from codegen.html)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # In production, restrict to your frontend domain
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# 🏠 Health Check Endpoint
# =============================================================================
@app.get("/")
def home():
    """Simple API health check."""
    return {"status": "Backend running", "db": "MongoDB connected ✅"}

# =============================================================================
# 🧠 Helper Function: Parse Structured Synopsis
# =============================================================================
def parse_synopsis(text: str):
    """
    Extracts structured fields from a formatted synopsis.
    Example expected format:
        # Project Title: ...
        # Description: ...
        # Key Features: ...
        # Target Platform: ...
        # Technology Preference: ...
        # Expected Output: ...
    """

    print("\n🧠 [Parser] Trying to extract structured synopsis fields (v2)...")

    # Helper function to get a clean match from regex
    def get_value(pattern):
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        return match.group(1).strip() if match else None

    parsed = {
        # 🧾 Project title up to next section
        "project_title": get_value(
            r"#\s*Project Title:\s*(.+?)(?=#\s*Description|#\s*Key Features|#\s*Target Platform|#\s*Technology Preference|#\s*Expected Output|$)"
        ),
        # 📜 Description section
        "description": get_value(
            r"#\s*Description:\s*(.+?)(?=#\s*Key Features|#\s*Target Platform|#\s*Technology Preference|#\s*Expected Output|$)"
        ),
        # ✅ Extract numbered key features (1., 2., etc.)
        "key_features": [f.strip() for f in re.findall(r"\d+\.\s*(.+)", text)],
        # 🎯 Other simple sections
        "target_platform": get_value(r"#\s*Target Platform:\s*(.+?)(?=#|$)"),
        "technology": get_value(r"#\s*Technology Preference:\s*(.+?)(?=#|$)"),
        "expected_output": get_value(r"#\s*Expected Output:\s*(.+?)(?=#|$)")
    }

    # Debug output for clarity
    print("✅ [Clean Parser Result]")
    for key, val in parsed.items():
        print(f"   {key}: {val}")

    return parsed

# =============================================================================
# 📡 API: Upload & Save Synopsis
# =============================================================================
from services.project_parser import llama_structured_project

@app.post("/api/upload-synopsis")
async def upload_synopsis(
    synopsis: str = Form(None),
    tech: str = Form(None),
    file: UploadFile = None
):
    print("\n🚀 [API CALL] /api/upload-synopsis → AI Parser Mode")

    # STEP 1: Extract plain text (from textarea or file)
    text = await process_synopsis(synopsis, file)

    # STEP 2: Ask LLaMA to return structured project metadata
    project_data = await llama_structured_project(text, tech)

    # -----------------------------------------------------------
    # ✅ STEP 3: Normalize keys to match frontend requirements
    # -----------------------------------------------------------

    # Title
    project_data["title"] = (
        project_data.get("title")
        or project_data.get("project_title")
        or "Untitled Project"
    )

    # Description
    project_data["description"] = (
        project_data.get("description")
        or project_data.get("summary")
        or "No description provided"
    )

    # Features (list)
    project_data["features"] = (
        project_data.get("features")
        or project_data.get("key_features")
        or []
    )

    # Modules (list)
    project_data["modules"] = project_data.get("modules") or []

    # Tech stack
    project_data["tech_stack"] = (
        project_data.get("tech_stack")
        or project_data.get("technology")
        or [tech]
    )

    # Target Platform
    project_data["target_platform"] = (
        project_data.get("target_platform")
        or "Web"
    )

    # UI preferences
    project_data["ui_layout"] = (
        project_data.get("ui_layout")
        or "dashboard"
    )
    project_data["ui_color_scheme"] = (
        project_data.get("ui_color_scheme")
        or "blue"
    )
    project_data["ui_primary_color"] = (
        project_data.get("ui_primary_color")
        or "#4361ee"
    )

    # AI Summary
    project_data["ai_summary"] = (
        project_data.get("ai_summary")
        or project_data.get("expected_output")
        or "Structured automatically for " + tech
    )

    # -----------------------------------------------------------
    # STEP 4: Add backend metadata
    # -----------------------------------------------------------

    project_data["prompt"] = text
    project_data["status"] = "synopsis_uploaded"
    project_data["created_at"] = datetime.utcnow().isoformat()
    project_data["wireframe"] = {}
    project_data["code_repo"] = None

    # -----------------------------------------------------------
    # STEP 5: Save to MongoDB
    # -----------------------------------------------------------

    project_id = await save_project(project_data)
    project_data["project_id"] = str(project_id)   # include ID in object

    # -----------------------------------------------------------
    # STEP 6: Remove internal fields just before frontend response
    # -----------------------------------------------------------
    if "_id" in project_data:
        del project_data["_id"]

    # -----------------------------------------------------------
    # STEP 7: Send response
    # -----------------------------------------------------------

    return {
        "success": True,
        "message": "Project parsed & saved successfully with AI 🧠",
        "project_id": str(project_id),
        "project": project_data
    }

# =============================================================================
# 🗄️ JSON Encoder for MongoDB ObjectId
# =============================================================================
class MongoJSONEncoder(json.JSONEncoder):
    """Converts MongoDB ObjectId to JSON serializable format."""
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return super().default(o)

@app.get("/api/get-latest-project")
async def get_latest_project():
    """
    Returns the most recently saved project from MongoDB.
    Used in frontend step: 'Confirm Synopsis'
    """
    print("\n📦 [API CALL] /api/get-latest-project -----------------------------------")

    try:
        # ✅ If collection is async (Motor), await find_one()
        latest_doc = await collection.find_one(sort=[("_id", -1)])
        if not latest_doc:
            return {"success": False, "error": "No projects found in database."}

        # ✅ Convert ObjectId → str safely
        project_json = json.loads(json.dumps(latest_doc, cls=MongoJSONEncoder))

        title = project_json.get("title", "Untitled")
        print(f"✅ [DB FETCH SUCCESS] Latest Project: {title}")
        return {"success": True, "project": project_json}

    except Exception as e:
        print(f"❌ MongoDB Fetch Error: {str(e)}")
        return {"success": False, "error": str(e)}


# =============================================================================
# 📝 API: Update Project After Editing (Step 2 Edit Button)
# =============================================================================
@app.post("/api/update-project")
async def update_project(project_id: str = Form(...), project: str = Form(...)):
    """
    Saves updated project details (title, description, features, modules, etc.)
    from Step-2 Edit Form.
    """
    try:
        updated_data = json.loads(project)   # convert string → dict
        oid = ObjectId(project_id)

        result = await collection.update_one(
            {"_id": oid},
            {"$set": updated_data}
        )

        if result.modified_count > 0:
            print(f"✅ [DB] Project updated: {project_id}")
            return {"success": True, "message": "Project updated successfully"}
        else:
            print(f"⚠️ [DB] No modification for: {project_id}")
            return {"success": False, "message": "Nothing changed"}

    except Exception as e:
        print("❌ [Update Project ERROR]:", e)
        return {"success": False, "error": str(e)}

# =============================================================================
# 🧱 API: generate Wireframe Layout 
# =============================================================================

@app.post("/api/generate-wireframe")
async def generate_wireframe(project_id: str = Form(...)):
    from services.ai_agent import generate_wireframe_ai

    print("\n🤖 [AI AGENT] Generating wireframe via LLaMA...")
    project = await get_project(project_id)
    if not project:
        return {"error": "Project not found"}

    wireframe = await generate_wireframe_ai(project)

    # ✅ Save AI result to DB immediately
    oid = ObjectId(project_id)
    try:
        result = await collection.update_one(
            {"_id": oid},
            {"$set": {"wireframe": wireframe}}
        )
        if result.modified_count > 0:
            print(f"✅ [DB] Wireframe stored for Project {project_id}")
        else:
            print(f"⚠️ [DB] Wireframe not modified (may be identical)")
    except Exception as e:
        print("❌ [DB Update Error while saving wireframe]:", e)

    # Return result to frontend
    return {"success": True, "wireframe": wireframe}


# =============================================================================
# 🧱 API: Update Wireframe Layout (after editing or adding new components)
# =============================================================================

@app.post("/api/update-wireframe")
async def update_wireframe(project_id: str = Form(...), wireframe: str = Form(...)):
    import json
    try:
        wireframe_data = json.loads(wireframe)

        oid = ObjectId(project_id)

        # ✅ Use the correct collection object (from db_service)
        result = await collection.update_one(
            {"_id": oid},
            {"$set": {"wireframe": wireframe_data}}
        )

        if result.modified_count > 0:
            print(f"✅ [DB] Wireframe updated for {project_id}")
            return {"success": True, "message": "Wireframe updated"}
        else:
            print(f"⚠️ [DB] No document modified for {project_id}")
            return {"success": False, "message": "No changes made"}

    except Exception as e:
        print("❌ [Update Error]:", e)
        return {"success": False, "error": str(e)}

