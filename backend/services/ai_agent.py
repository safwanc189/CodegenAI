import os
import json
import re
import logging
from typing import Dict, Any, Optional

import requests

logger = logging.getLogger("ai_agent")
logger.setLevel(logging.INFO)

# Set up logging for console output
handler = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


PROMPT_TEMPLATE = """
You are an expert UI/UX engineer and frontend architect.

Given the full project specification, produce a complete UI wireframe JSON.

Return STRICT JSON ONLY.

Top-level keys:
- layout_type
- app_name
- color_scheme
- primary_color
- navigation
- pages

Each module must create ONE page.

PROJECT INPUT:
{project_json}
"""


# -------------------------------------------------------------------
# SAFE JSON EXTRACT
# -------------------------------------------------------------------
def safe_json_extract(text: str) -> Optional[Dict[str, Any]]:
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        return None

    candidate = text[start:end + 1]

    try:
        return json.loads(candidate)
    except:
        # Attempt to clean common LLM JSON errors
        cleaned = re.sub(r",\s*}", "}", candidate)
        cleaned = re.sub(r",\s*]", "]", cleaned)
        try:
            return json.loads(cleaned)
        except:
            return None


def slugify(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", name.lower()).strip("_")


# -------------------------------------------------------------------
# MAIN AI FUNCTION
# -------------------------------------------------------------------
async def generate_wireframe_ai(project: Dict[str, Any]) -> Dict[str, Any]:
    print("🔥 RAW MODULES FROM DB:", project.get("modules"))

    # ------------------------------------------------------
    # NORMALIZE MODULES + FIX NESTED LIST BUG
    # ------------------------------------------------------
    raw_modules = project.get("modules", [])

    # FIX: If modules is wrapped as [ [ {...}, {...} ] ]
    if len(raw_modules) == 1 and isinstance(raw_modules[0], list):
        logger.info("ℹ️ Detected nested module list, flattening.")
        raw_modules = raw_modules[0]

    cleaned_modules = []
    for m in raw_modules:
        if isinstance(m, dict):
            m.setdefault("fields", [])
            m.setdefault("actions", [])
            cleaned_modules.append(m)
        else:
            # New Log: Helps diagnose non-dictionary module inputs
            logger.warning("⚠️ Module item is not a dictionary, converting to default: %s (Type: %s)", m, type(m))
            cleaned_modules.append({
                "name": str(m),
                "fields": [],
                "actions": []
            })
    
    logger.info("✅ Normalized Modules Check: Total=%d, First Item Type=%s", 
                len(cleaned_modules), type(cleaned_modules[0]) if cleaned_modules else "N/A")
    # Now modules are 100% valid dicts
    # ------------------------------------------------------

    input_json = {
        "title": project.get("title"),
        "description": project.get("description"),
        "features": project.get("features", []),
        "modules": cleaned_modules,
        "tech_stack": project.get("tech_stack", []),
        "target_platform": project.get("target_platform", "web")
    }

    prompt = PROMPT_TEMPLATE.format(project_json=json.dumps(input_json, indent=2))

    logger.info("🔥 Calling LLAMA (Ollama)")

    payload = {
        "model": "llama3:8b",
        "prompt": prompt,
        "max_tokens": 4000,
        "stream": False
    }

    try:
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=300)
        resp.raise_for_status()
    except Exception as e:
        logger.error("❌ LLaMA/Ollama error: %s", e)
        # Fallback if AI call fails
        return programmatic_wireframe_from_project(project)

    body = resp.json()
    text = body.get("output") or body.get("response") or body.get("text") or resp.text

    wf = safe_json_extract(text)

    if not wf:
        print("❌ AI returned non-JSON, using fallback")
        # Fallback if AI output is not valid JSON
        return programmatic_wireframe_from_project(project)

    project["modules"] = cleaned_modules
    # New Log: Confirming data before enrichment
    logger.info("✨ AI returned valid JSON. Starting validation and enrichment.")
    return validate_and_enrich(wf, project)


# -------------------------------------------------------------------
# ENRICHER
# -------------------------------------------------------------------
def validate_and_enrich(wf: Dict[str, Any], project: Dict[str, Any]) -> Dict[str, Any]:
    wf.setdefault("layout_type", "dashboard")
    # ... (omitted boilerplate setdefaults) ...
    wf.setdefault("navigation", [])
    wf.setdefault("pages", {})

    print(f"\n--- DEBUG ENRICHMENT START ---")
    # ... (omitted debug prints) ...
    print(f"------------------------------\n")

    # 💥 CRITICAL FIX START: Normalize the navigation list access
    nav_data = wf.get("navigation", {}) 
    
    # Determine the actual list of navigation items
    if isinstance(nav_data, dict) and 'items' in nav_data:
        # Case 1: AI returned {'type': 'topbar', 'items': [...]}
        nav_items_list = nav_data.get('items', [])
    elif isinstance(nav_data, list):
        # Case 2: AI returned a simple list, which is what your code expected originally
        nav_items_list = nav_data
    else:
        # Default to an empty list to prevent crash
        nav_items_list = []
        
    # --- END CRITICAL FIX ---

    # Helper function remains the same, checking for 'id' and 'page_id'
    def nav_item_matches(n, pid):
        if not isinstance(n, dict):
            return False
        # The key check for 'id' AND 'page_id'
        # NOTE: AI output uses 'text' for label, but we check 'href' or 'id' for uniqueness
        return n.get("id") == pid or n.get("page_id") == pid or n.get("href") == f"/{pid}"
        
    # Safely check if 'mod' is a dict and has a 'name'
    for mod in project["modules"]:
        mod_name = mod.get("name")
        # ... (omitted module name safety check) ...
        pid = slugify(mod_name)
        
        # Now use the normalized list: nav_items_list
        if not any(nav_item_matches(n, pid) for n in nav_items_list):
            
            # 💥 CRITICAL FIX: Append to the actual list variable (nav_items_list)
            nav_items_list.append({
                "id": pid,
                "label": mod_name,
                "path": f"/{pid}"
            })

        # ... (rest of the page creation logic using pid) ...
        
    # FINAL STEP: Ensure the wireframe object is updated with the modified list
    if isinstance(nav_data, dict) and 'items' in nav_data:
        nav_data['items'] = nav_items_list
        wf["navigation"] = nav_data # Update the full dictionary object
    else:
        wf["navigation"] = nav_items_list # Update the simple list object
        
    print("--- DEBUG ENRICHMENT END ---\n")
    return wf

# -------------------------------------------------------------------
# FALLBACK
# -------------------------------------------------------------------
def programmatic_wireframe_from_project(project: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("⚙️ Generating programmatic fallback wireframe.")
    wf = {
        "layout_type": "sidebar",
        "app_name": project.get("title"),
        "navigation": [],
        "pages": {}
    }

    # The fix is here: Safely check if 'm' is a dict and has a 'name'
    for m in project.get("modules", []):
        mod_name = m.get("name")
        
        if not isinstance(m, dict) or not mod_name:
            logger.warning("Skipping invalid module in fallback: %s", m)
            continue
            
        pid = slugify(mod_name)

        wf["navigation"].append({"id": pid, "label": mod_name, "path": f"/{pid}"})
        wf["pages"][pid] = {
           "title": mod_name,
           "fields": m.get("fields", []),
           "actions": m.get("actions", []),
           "components": [],
        }
    
    return wf