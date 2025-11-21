# services/ai_agent.py

import json
import re
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger("ui_agent")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(ch)

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3:8b"


# -------------------------------------------------------------------
# 1) NEW UI SCHEMA PROMPT (ONLY PAGES, NO LAYOUT, NO COLORS)
# -------------------------------------------------------------------

PROMPT_TEMPLATE = """
You are a senior UI/UX engineer.

Your task:
➡ Convert every MODULE into a PAGE.
➡ Convert module fields → INPUT components.
➡ Convert module actions → BUTTON components.

IMPORTANT:
- Backend will generate layout, navigation, app_name.
- DO NOT include layout_type, app_name, navigation, colors.
- You ONLY generate the PAGES section.

OUTPUT JSON SCHEMA (required):

{{
  "pages": {{
    "<module_slug>": {{
      "title": "<module name>",
      "components": [
        {{
          "type": "input",
          "label": "<field name>",
          "inputType": "text"
        }},
        {{
          "type": "button",
          "label": "<action name>",
          "action": "<action_slug>"
        }}
      ]
    }}
  }}
}}

Rules:
- Keep ONLY this "pages" object in output.
- No markdown, no explanations, no extra text.
- Output valid JSON only.

PROJECT INPUT:
{project_json}
"""




# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def slugify(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")


def safe_json_extract(text: str) -> Optional[Dict[str, Any]]:
    """Extract valid JSON even if AI adds noise."""
    text = text.replace("```", "").strip()

    first = text.find("{")
    last = text.rfind("}")

    if first == -1 or last == -1:
        return None

    try:
        return json.loads(text[first:last + 1])
    except:
        return None


# -------------------------------------------------------------------
# 2) GENERATE UI WITH REAL INPUT + BUTTON COMPONENTS
# -------------------------------------------------------------------

def generate_wireframe_ai_sync(project: Dict[str, Any]) -> Dict[str, Any]:

    logger.info("⚡ Creating REAL UI wireframe for: %s", project.get("title"))

    safe_project = {
        "title": project.get("title"),
        "modules": project.get("modules", []),
    }

    prompt = PROMPT_TEMPLATE.format(
        project_json=json.dumps(safe_project, indent=2)
    )

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "max_tokens": 2000
    }

    # --- CALL LLaMA ---
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=120)
        body = resp.json()
        raw = body.get("output") or body.get("response") or json.dumps(body)

    except Exception:
        logger.error("❌ AI request failed, using fallback UI")
        return fallback_ui(project)

    # --- PARSE JSON ---
    wf = safe_json_extract(str(raw))
    if not wf:
        logger.error("❌ AI returned invalid JSON → fallback UI")
        return fallback_ui(project)

    # --- NORMALIZE INPUT KEYS ---
    for page in wf.get("pages", {}).values():
        for c in page.get("components", []):
            if "input_type" in c:
                c["inputType"] = c.pop("input_type")
            if "inputtype" in c:
                c["inputType"] = c.pop("inputtype")
            if "input-type" in c:
                c["inputType"] = c.pop("input-type")

    return wf


# -------------------------------------------------------------------
# 3) FALLBACK UI (if AI fails)
# -------------------------------------------------------------------

def fallback_ui(project: Dict[str, Any]) -> Dict[str, Any]:
    pages = {}

    for mod in project.get("modules", []):
        pid = slugify(mod["name"])

        inputs = [
            {"type": "input", "label": f, "inputType": "text"}
            for f in mod.get("fields", [])
        ]

        buttons = [
            {"type": "button", "label": a, "action": slugify(a)}
            for a in mod.get("actions", [])
        ]

        pages[pid] = {
            "title": mod["name"],
            "components": inputs + buttons
        }

    return { "pages": pages }


# -------------------------------------------------------------------
# ASYNC WRAPPER
# -------------------------------------------------------------------

async def generate_wireframe_ai(project: Dict[str, Any]):
    return generate_wireframe_ai_sync(project)
