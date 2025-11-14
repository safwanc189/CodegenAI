# =============================================================================
# 🤖 AI Agent Service (ai_agent.py)
# ----------------------------------------------------------------------------- 
# NEW Powerful Wireframe Generator (Optimized for Ollama + Frontend Rendering)
# =============================================================================

import subprocess
import json


async def generate_wireframe_ai(project):
    """
    Generates a rich and consistent JSON wireframe for your project.
    Zero markdown. Zero emojis. FULL JSON ONLY.
    Always returns pages + components (never empty).
    """

    print("\n🤖 [AI AGENT] Generating wireframe via Ollama...")

    # -------------------------
    # High-power, zero-truncation prompt
    # -------------------------
    prompt = f"""
You are a senior full-stack UI/UX architect.
Generate a COMPLETE UI wireframe as STRICT VALID JSON ONLY.

RULES:
- NO emojis
- NO markdown
- NO explanation
- JSON ONLY, nothing else
- MUST ALWAYS include pages
- MUST ALWAYS include components inside each page
- Use the project details to design an outstanding UI

PROJECT DETAILS:
Title: {project.get("title")}
Description: {project.get("description")}
Features: {project.get("features")}
Modules: {project.get("modules")}
Tech Stack: {project.get("tech_stack")}
Target Platform: {project.get("target_platform")}

RETURN JSON EXACTLY LIKE THIS STRUCTURE:
{{
  "layout_type": "sidebar" or "topnav" or "dashboard",

  "app_name": "{project.get("title", "Application")}",
  "color_scheme": "blue",
  "primary_color": "#4361ee",

  "navigation": [
    {{ "id": "dashboard", "label": "Dashboard", "path": "/dashboard" }},
    {{ "id": "module_name", "label": "Users", "path": "/users" }}
  ],

  "pages": {{
    "dashboard": {{
      "title": "Dashboard",
      "components": [
        {{ "type": "stat_card", "title": "Total Students", "value": "1200" }},
        {{ "type": "chart", "title": "Attendance Trend" }}
      ]
    }},

    "students": {{
      "title": "Students",
      "components": [
        {{ "type": "table", "columns": ["ID", "Name", "Attendance %"] }},
        {{ "type": "button", "label": "Add Student" }}
      ]
    }}
  }}
}}
"""

    try:
        # -------------------------
        # Run model safely
        # -------------------------
        result = subprocess.run(
            ["ollama", "run", "llama3:latest"],
            input=prompt.encode("utf-8"),
            capture_output=True,
            text=False
        )

        raw_output = result.stdout.decode("utf-8", errors="ignore").strip()

        print("\n📤 Raw LLaMA Output (first 350 chars):")
        print(raw_output[:350])

        # -------------------------
        # Extract JSON safely
        # -------------------------
        start = raw_output.find("{")
        end = raw_output.rfind("}") + 1

        if start < 0 or end < 1:
            raise ValueError("LLaMA returned no JSON output")

        json_text = raw_output[start:end]
        wireframe = json.loads(json_text)

        # ------------------------------------------------
        # ENSURE PAGES ALWAYS EXISTS (no frontend crash)
        # ------------------------------------------------
        if "pages" not in wireframe or not isinstance(wireframe["pages"], dict):
            wireframe["pages"] = {}

        if len(wireframe["pages"]) == 0:
            wireframe["pages"] = {
                "dashboard": {
                    "title": "Dashboard",
                    "components": [
                        {"type": "stat_card", "title": "Total Items", "value": "0"},
                        {"type": "chart", "title": "Daily Trend"}
                    ]
                }
            }

        print("✅ AI JSON wireframe generated successfully.")
        return wireframe

    except Exception as e:
        print("❌ [AI ERROR]:", str(e))

        # -------------------------
        # Guaranteed valid fallback
        # -------------------------
        return {
            "fallback": True,
            "title": project.get("title"),
            "layout_type": "sidebar",
            "color_scheme": "blue",
            "primary_color": "#4361ee",

            "navigation": [
                {"id": "dashboard", "label": "Dashboard", "path": "/dashboard"},
                {"id": "students", "label": "Students", "path": "/students"},
            ],

            "pages": {
                "dashboard": {
                    "title": "Dashboard",
                    "components": [
                        {"type": "stat_card", "title": "Total Students", "value": "1200"},
                        {"type": "chart", "title": "Attendance Overview"},
                    ]
                },
                "students": {
                    "title": "Students",
                    "components": [
                        {"type": "table", "columns": ["ID", "Name", "Attendance %"]},
                        {"type": "button", "label": "Add Student"}
                    ]
                }
            }
        }
