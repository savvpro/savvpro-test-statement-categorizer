import io
from fastapi import FastAPI, File, HTTPException, UploadFile, status
import pdfplumber
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://192.168.1.5:5173'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def categorize_transaction(text: str) -> str:
    desc_lower = text.lower()
    if "raast in" in desc_lower or "money received" in desc_lower:
        return "Income"
    elif "indrive" in desc_lower:
        return "Rider fee"
    elif "cheezious" in desc_lower or "pos" in desc_lower:
        return "Food / Dining"
    return "Other"

@app.post("/parse-statement")
async def upload_pdf(file: UploadFile = File(...), status_code=status.HTTP_200_OK):
  if not file.filename.endswith(".pdf"):
    raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

  file_bytes = await file.read()
  result = []

  with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            for row in table:
                if not row or any(cell and "Time" in cell for cell in row):
                    continue                
                cleaned_row = [cell.strip() if cell else "" for cell in row]
                description = " ".join([c for c in cleaned_row if c])
                
                amount_str = "0"
                for cell in cleaned_row:
                    if cell.startswith("+") or cell.startswith("-"):
                        amount_str = cell
                        break
                
                category = categorize_transaction(description)
                
                result.append({
                    "description": description,
                    "amount": amount_str,
                    "category": category,
                    "raw_row": cleaned_row
                })

  return result