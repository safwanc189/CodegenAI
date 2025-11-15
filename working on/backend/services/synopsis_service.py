import io
from PyPDF2 import PdfReader
from docx import Document

# -----------------------------------------------------------------------------
# 📄 Handles all file uploads and text extraction
# -----------------------------------------------------------------------------
async def process_synopsis(synopsis_text, uploaded_file):
    print("\n🧩 [Service] process_synopsis() called")

    # Case 1️⃣: Text typed in directly
    if synopsis_text and not uploaded_file:
        print("🟢 Using direct text input (no file uploaded)")
        return synopsis_text.strip()

    # Case 2️⃣: File uploaded
    if uploaded_file:
        filename = uploaded_file.filename.lower()
        content = await uploaded_file.read()
        text = ""

        print(f"📄 Processing uploaded file: {filename}")

        if filename.endswith(".txt"):
            text = content.decode("utf-8", errors="ignore")
        elif filename.endswith(".pdf"):
            reader = PdfReader(io.BytesIO(content))
            text = " ".join(page.extract_text() or "" for page in reader.pages)
        elif filename.endswith(".docx"):
            doc = Document(io.BytesIO(content))
            text = " ".join(p.text for p in doc.paragraphs)
        else:
            print("⚠️ Unsupported file type:", filename)
            return "Unsupported file format."

        print(f"✅ File text extracted ({len(text)} chars)")
        return text.strip()

    # Case 3️⃣: No text or file
    print("⚠️ No synopsis text or file provided")
    return ""
