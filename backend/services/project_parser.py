import subprocess, json, re

async def llama_structured_project(prompt_text: str, tech: str):
    """
    Calls LLaMA 3 (Ollama) to convert a project description into a fully
    structured JSON object for further steps (UI wireframe, API generation, code).
    """

    llm_prompt = f"""
You are an expert software architect. Convert the user's project description into 
a perfect structured JSON object.

USER PROJECT SYNOPSIS:
\"\"\"{prompt_text}\"\"\"


RETURN STRICT JSON ONLY. NO markdown. NO explanation.
JSON FORMAT:
{{
  "title": "string",
  "description": "string",
  "features": ["Feature 1", "Feature 2"],
  "modules": [
    {{
      "name": "string",
      "components": ["string", "string"]
    }}
  ],
  "tech_stack": ["MongoDB", "Express", "React", "Node.js"],
  "target_platform": "Web",
  "ui_preferences": {{
    "layout_type": "dashboard",
    "color_scheme": "blue",
    "primary_color": "#4361ee"
  }}
}}
    """

    result = subprocess.run(
        ["ollama", "run", "llama3:latest"],  # FIXED
        input=llm_prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )

    output = result.stdout.strip()

    # ----------------------------------------------------
    # 🧹 CLEAN OUTPUT → remove ```json ... ```
    # ----------------------------------------------------
    output = re.sub(r"```json|```", "", output).strip()

    # ----------------------------------------------------
    # 🧠 TRY PARSING JSON
    # ----------------------------------------------------
    try:
        structured = json.loads(output)

        # Guarantee fields exist
        structured.setdefault("title", "Untitled Project")
        structured.setdefault("description", prompt_text)
        structured.setdefault("features", [])
        structured.setdefault("modules", [])
        structured.setdefault("tech_stack", [])
        structured.setdefault("target_platform", "Web")

        # Ensure UI preferences exist
        ui = structured.get("ui_preferences", {})
        structured["ui_preferences"] = {
            "layout_type": ui.get("layout_type", "dashboard"),
            "color_scheme": ui.get("color_scheme", "blue"),
            "primary_color": ui.get("primary_color", "#4361ee")
        }

        # Add AI summary
        structured["ai_summary"] = f"Structured automatically for {tech}"

        # Merge tech stack nicely
        if tech.lower() == "mern":
            structured["tech_stack"] = ["MongoDB", "Express", "React", "Node.js"]
        else:
            structured["tech_stack"].append(tech)

        return structured

    except Exception as e:
        print("❌ JSON Parsing Error:", e)
        print("Raw LLaMA Output:\n", output)

        # Return safe fallback
        return {
            "title": "Untitled Project",
            "description": prompt_text,
            "features": [],
            "modules": [],
            "tech_stack": [tech],
            "target_platform": "Web",
            "ui_preferences": {
                "layout_type": "dashboard",
                "color_scheme": "blue",
                "primary_color": "#4361ee"
            },
            "ai_summary": f"Structured automatically for {tech}"
        }
