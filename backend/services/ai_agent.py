# =============================================================================
# 🤖 AI Agent Service (ai_agent.py)
# ----------------------------------------------------------------------------- 
# Uses local LLaMA (Ollama) to generate structured wireframes for projects.
# Compatible with Windows CMD execution.
# =============================================================================

import subprocess
import json
import os

async def generate_wireframe_ai(project):
    """
    Generate a structured UI wireframe JSON using local Ollama (LLaMA 3).
    Works on Windows using synchronous subprocess.
    """

    print("\n🤖 [AI AGENT] Generating wireframe using Ollama (LLaMA 3)...")

    prompt = f"""
You are a senior full-stack UI/UX architect.
Generate a clean, valid JSON wireframe for this web project.

### Project Details
Title: {project.get('title')}
Description: {project.get('description')}
Key Features: {', '.join(project.get('features', []))}
Target Platform: {project.get('target_platform')}
Technology: {project.get('tech')}
Expected Output: {project.get('expected_output')}

### Output Format (must be strictly valid JSON only)
{{
  "layout_type": "sidebar" or "topnav",
  "app_name": "{project.get('title', 'My Application')}",
  "color_scheme": "blue" or "green" or "dark",
  "primary_color": "#4F46E5",
  "navigation": ["Dashboard", "Workers", "Reports", "Inventory"],
  "pages": {{
    "Dashboard": ["StatsCard", "ProgressChart"],
    "Workers": ["Table", "AddWorkerForm"],
    "Reports": ["ReportTable", "ExportButton"]
  }}
}}
    """

    try:
        print("⚙️ Running Ollama model → llama3:latest")
        print(f"🧠 [Prompt Preview] (first 200 chars):\n{prompt[:200]}...\n")

        # ✅ FIXED: input must be a string, not bytes
        result = subprocess.run(
            ["ollama", "run", "llama3:latest"],
            input=prompt,        # <--- no .encode() here
            capture_output=True,
            text=True,           # ensures input/output handled as text
            shell=True
        )

        # Print everything for debugging
        print(f"📤 [Ollama Return Code]: {result.returncode}")
        if result.stdout:
            print(f"🧠 [Ollama STDOUT] (first 300 chars):\n{result.stdout[:300]}...\n")
        if result.stderr:
            print(f"⚠️ [Ollama STDERR]:\n{result.stderr}\n")

        output = result.stdout.strip()
        if not output:
            raise ValueError("No output received from Ollama (empty response).")

        # 🧩 Extract JSON safely
        json_start = output.find("{")
        json_end = output.rfind("}") + 1
        if json_start == -1 or json_end == -1:
            raise ValueError("No JSON found in Ollama output.")

        json_text = output[json_start:json_end]
        print(f"📄 [Extracted JSON Snippet]: {json_text[:200]}...\n")

        wireframe = json.loads(json_text)
        print("✅ [AI AGENT] Wireframe generated successfully!")
        return wireframe

    except Exception as e:
        print("❌ [AI AGENT ERROR]:", str(e))
        print("💡 Tip: Try manually running this command in CMD to confirm Ollama output:")
        print('👉  ollama run llama3:latest "Generate a JSON wireframe"')
        return {"error": str(e)}
