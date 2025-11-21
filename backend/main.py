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
    from services.project_parser import parse_structured_project

    project_data = parse_structured_project(text)
    project_data["tech_stack"] = [tech]

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
    # ================= CLEAN FINAL PROJECT JSON FOR FRONTEND ==================
    project_clean = {
      "title": project_data.get("title", ""),
      "description": project_data.get("description", ""),
      "features": project_data.get("features", []),
      "modules": project_data.get("modules", []),
      "tech_stack": project_data.get("tech_stack", []),
      "target_platform": project_data.get("target_platform", "Web"),
      "ai_summary": project_data.get("ai_summary", ""),
      "wireframe": {}
    }
    
    return {
        "success": True,
        "message": "Project parsed & saved successfully with AI 🧠",
        "project_id": str(project_id),
        "project": project_clean
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
    Always returns success if project exists — even when nothing changed.
    """
    try:
        updated_data = json.loads(project)
        oid = ObjectId(project_id)

        result = await collection.update_one(
            {"_id": oid},
            {"$set": updated_data}
        )

        # SUCCESS if document exists, even if nothing changed
        if result.matched_count == 1:
            print(f"✅ [DB] Project updated (modified: {result.modified_count}) → {project_id}")
            return {"success": True, "message": "Project updated successfully"}

        # If document doesn't exist
        print(f"❌ [DB] Project not found for update: {project_id}")
        return {"success": False, "error": "Project not found"}

    except Exception as e:
        print("❌ [Update Project ERROR]:", e)
        return {"success": False, "error": str(e)}

# =============================================================================
# 🧱 API: Generate FULL Wireframe (using LLAMA Big-Call)
# =============================================================================
@app.post("/api/generate-wireframe")
async def generate_wireframe(project_id: str = Form(...)):
    from services.ai_agent import generate_wireframe_ai
    from bson import ObjectId

    print("\n🤖 [AI AGENT] Generating FULL wireframe via LLaMA...")

    # ------------------------------------------------------------
    # STEP 1: Fetch project from DB
    # ------------------------------------------------------------
    project = await get_project(project_id)
    if not project:
        return {"success": False, "error": "Project not found"}

    print(f"📦 [DB] Retrieved project: {project.get('title')}")

    # ------------------------------------------------------------
    # STEP 2: Ask LLaMA to generate FULL UI JSON
    # ------------------------------------------------------------
    try:
        ai_wireframe = await generate_wireframe_ai(project)
        wf = ai_wireframe
        
        nav = []
        for mod in project.get("modules", []):
            slug = re.sub(r"[^a-zA-Z0-9]+", "-", mod["name"]).lower()
            nav.append({
                "id": slug,
                "label": mod["name"],
                "path": f"/{slug}"
            })
                
        wireframe_clean = {
           "layout_type": project.get("ui_layout", "sidebar"),
           "color_scheme": project.get("ui_color_scheme", "blue"),
           "primary_color": project.get("ui_primary_color", "#4361ee"),
           "app_name": project.get("title", "Application"),

           "navigation": nav,
           "pages": wf.get("pages", {})
        }
    except Exception as e:
        print("❌ [AI ERROR]:", e)
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": "AI wireframe generation failed",
            "detail": str(e)
        }

    # LLaMA must return dictionary
    if not isinstance(ai_wireframe, dict):
        print("❌ Invalid wireframe returned by LLaMA")
        return {
            "success": False,
            "error": "Invalid wireframe JSON returned by AI",
            "raw_output": str(ai_wireframe)
        }

    print("🎨 [AI] Full wireframe generated successfully")

    # ------------------------------------------------------------
    # STEP 3: Save wireframe to MongoDB
    # ------------------------------------------------------------
    try:
        oid = ObjectId(project_id)
        await collection.update_one(
          {"_id": oid},
          {"$set": {
            "wireframe": wireframe_clean,
            "status": "wireframe_generated",
            "updated_at": datetime.utcnow().isoformat()
           }}
        )
        print("✅ Wireframe saved to DB")
    except Exception as e:
        print("❌ [DB ERROR]:", e)
        return {
            "success": False,
            "error": f"Database save error: {str(e)}"
        }

    # ------------------------------------------------------------
    # STEP 4: Send response to frontend
    # ------------------------------------------------------------
    return {
        "success": True,
        "project_id": project_id,
        "title": project.get("title"),
        "wireframe": wireframe_clean
    }


# =============================================================================
# 📝 API: Update Only Wireframe (Used for Step 3 UI changes)
# =============================================================================
@app.post("/api/update-wireframe")
async def update_wireframe(project_id: str = Form(...), wireframe: str = Form(...)):
    try:
        oid = ObjectId(project_id)
        new_data = json.loads(wireframe)

        project = await get_project(project_id)
        if not project:
            return {"success": False, "error": "Project not found"}

        old_wf = project.get("wireframe", {})

        # ONLY UPDATE STYLE VALUES
        old_wf.update({
           "layout_type": new_data.get("layout_type", old_wf.get("layout_type")),
           "color_scheme": new_data.get("color_scheme", old_wf.get("color_scheme")),
           "primary_color": new_data.get("primary_color", old_wf.get("primary_color")),
           "app_name": new_data.get("app_name", old_wf.get("app_name"))
        })

        await collection.update_one(
            {"_id": oid},
            {"$set": {"wireframe": old_wf}}
        )

        return {"success": True, "message": "Wireframe updated (merged)"}

    except Exception as e:
        return {"success": False, "error": str(e)}
