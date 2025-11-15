# =============================================================================
# 📌 project_parser.py — FINAL UPDATED VERSION
# -----------------------------------------------------------------------------
# Converts structured text prompt into JSON structure:
# - PROJECT NAME
# - MASTER MODULE LIST
# - DETAILED MODULES WITH FIELDS + ACTIONS
#
# This version FIXES:
# ✔ Windows CRLF issues
# ✔ Module name detection
# ✔ Multi-block field parsing
# ✔ Multi-block action parsing
# ✔ Last-module truncation
# =============================================================================

import re
import json


# ------------------------------------------------------
# 1️⃣ Extract PROJECT NAME
# ------------------------------------------------------
def extract_project_name(text: str):
    match = re.search(r"PROJECT NAME\s*(.+)", text, re.IGNORECASE)
    return match.group(1).strip() if match else "Untitled Project"


# ------------------------------------------------------
# 2️⃣ Extract MASTER MODULE LIST (Flat list)
# ------------------------------------------------------
def extract_master_modules(text: str):
    block = re.search(
        r"MASTER MODULE LIST([\s\S]+?)DETAILED MODULES",
        text,
        re.IGNORECASE
    )

    if not block:
        return []

    lines = block.group(1).replace("\r", "").split("\n")

    modules = [line.strip() for line in lines if line.strip()]

    return modules


# ------------------------------------------------------
# 3️⃣ Extract DETAILED MODULES (name + fields + actions)
# ------------------------------------------------------
def extract_modules_with_details(text: str):
    text = text.replace("\r", "")  # normalize CRLF

    modules = []

    # Find all MODULE NAMES (uppercase lines before "Fields:")
    module_titles = re.findall(
        r"\n([A-Z0-9][A-Z0-9 &()\/\.-]+?)\s*\nFields:",
        text,
        re.MULTILINE
    )

    for title in module_titles:
        title_clean = title.strip()

        # Regex to capture fields + actions until next module
        pattern = (
            rf"{re.escape(title_clean)}\s*"
            r"Fields:\s*([\s\S]*?)"         # capture fields block
            r"Actions:\s*([\s\S]*?)"        # capture actions block
            r"(?=\n[A-Z0-9][A-Z0-9 &()\/\.-]+\s*\nFields:|$)"  # stop at next module
        )

        match = re.search(pattern, text)

        if not match:
            continue

        raw_fields = match.group(1)
        raw_actions = match.group(2)

        # Clean fields
        fields = [
            f.strip().lstrip("-* ").strip()
            for f in raw_fields.split("\n")
            if f.strip()
        ]

        # Clean actions
        actions = [
            a.strip().lstrip("-* ").strip()
            for a in raw_actions.split("\n")
            if a.strip()
        ]

        modules.append({
            "name": title_clean,
            "fields": fields,
            "actions": actions
        })

    return modules


# ------------------------------------------------------
# 4️⃣ Main function — convert full text → JSON
# ------------------------------------------------------
def parse_structured_project(text: str):
    project_name = extract_project_name(text)
    master_list = extract_master_modules(text)
    detailed_modules = extract_modules_with_details(text)

    return {
        "title": project_name,
        "description": f"Auto structured from detailed specification for {project_name}",
        "features": master_list,            # UI uses this for left sidebar
        "modules": detailed_modules,        # backend uses this for API/DB/schema generator
        "tech_stack": [],
        "target_platform": "Web",
        "ui_preferences": {
            "layout_type": "dashboard",
            "color_scheme": "blue",
            "primary_color": "#4361ee"
        },
        "ai_summary": "Parsed using structured-project parser"
    }


# ------------------------------------------------------
# 5️⃣ Backwards-compatible wrapper (keeps your old call working)
# ------------------------------------------------------
async def llama_structured_project(prompt_text: str, tech: str):
    parsed = parse_structured_project(prompt_text)

    # Add user-selected tech
    parsed["tech_stack"].append(tech)

    return parsed
