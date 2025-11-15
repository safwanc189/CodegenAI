# =============================================================================
# 🤖 AI Agent Service (ai_agent.py)
# -----------------------------------------------------------------------------
# CLEAN + STABLE Wireframe Generator
# Navigation editing removed → AI does NOT use navigation rules.
# =============================================================================

import subprocess
import json


async def generate_wireframe_ai(project):
    """
    Generates a stable JSON wireframe based ONLY on project info.
    No navigation enforcement.
    No navigation_text.
    No auto-regeneration of pages.
    """
    print("\n🤖 [AI AGENT] Generating wireframe via Ollama...")

    # ---------------------------------------
    # 1️⃣ PREPARE SIMPLE CLEAN PROMPT
    # ---------------------------------------

    prompt = f"""
You are a senior UI/UX architect.
Generate a COMPLETE UI wireframe in STRICT VALID JSON ONLY.

RULES:
- NO markdown.
- NO emojis.
- NO commentary.
- JSON ONLY.
- MUST return "layout_type", "app_name", "color_scheme", "primary_color".
- MUST include "navigation" (3–5 items based on project).
- MUST include "pages" with components.
- Pages MUST contain useful widgets (cards, tables, charts, buttons).
- Avoid duplicate pages.
- Keep names simple and clean.

PROJECT INFO:
Title: {project.get("title")}
Description: {project.get("description")}
Features: {project.get("features")}
Modules: {project.get("modules")}
Tech Stack: {project.get("tech_stack")}

RETURN JSON EXACTLY LIKE THIS STRUCTURE:
{{
  "layout_type": "{project.get("ui_layout", "dashboard")}",
  "app_name": "{project.get("title", "Application")}",
  "color_scheme": "{project.get("ui_color_scheme", "blue")}",
  "primary_color": "{project.get("ui_primary_color", "#4361ee")}",

  "navigation": [
    {{ "id": "home", "label": "Home", "path": "/home" }},
    {{ "id": "module1", "label": "Module 1", "path": "/module1" }}
  ],

  "pages": {{
    "home": {{
      "title": "Home",
      "components": [
        {{ "type": "stat_card", "title": "Overview", "value": "120" }},
        {{ "type": "chart", "title": "Weekly Report" }}
      ]
    }}
  }}
}}
"""

    # ---------------------------------------
    # 2️⃣ RUN MODEL
    # ---------------------------------------
    try:
        result = subprocess.run(
            ["ollama", "run", "llama3:latest"],
            input=prompt.encode("utf-8"),
            capture_output=True,
            text=False
        )

        raw_output = result.stdout.decode("utf-8", errors="ignore").strip()

        print("\n📤 Raw LLaMA Output (first 350 chars):")
        print(raw_output[:350])

        # Extract JSON only
        start = raw_output.find("{")
        end = raw_output.rfind("}") + 1
        json_text = raw_output[start:end]

        wireframe = json.loads(json_text)

        print("✅ AI JSON wireframe generated successfully.")
        return wireframe

    except Exception as e:
        print("❌ [AI ERROR]:", str(e))

        # -------------------------
        # Fallback
        # -------------------------
        return {
            "layout_type": "dashboard",
            "app_name": project.get("title", "App"),
            "color_scheme": project.get("ui_color_scheme", "blue"),
            "primary_color": project.get("ui_primary_color", "#4361ee"),

            "navigation": [
                {"id": "home", "label": "Home", "path": "/home"}
            ],

            "pages": {
                "home": {
                    "title": "Home",
                    "components": [
                        {"type": "stat_card", "title": "Overview", "value": "120"},
                        {"type": "chart", "title": "Report"}
                    ]
                }
            }
        }
