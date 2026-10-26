from fastapi import APIRouter, UploadFile, File, HTTPException
from app.parsers.csv_parser import CSVParser
from app.brain.engine import categorize
from app.store import memory_store
from app.models.schemas import RowOut, UpdateCategoryIn

router = APIRouter()

@router.post("/upload", response_model=list[RowOut])
async def upload(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Invalid file type. Please upload a .csv file.")
    
    data = await file.read()
    
    try:
        # Attempt to parse the file
        txns = CSVParser().parse(data)
    except KeyError as e:
        # Catches missing columns (e.g., if "Amount" is missing)
        raise HTTPException(400, f"Missing required column in CSV: {e}")
    except ValueError as e:
        # Catches bad dates or amounts
        raise HTTPException(400, f"Data formatting error: {str(e)}")
    except Exception as e:
        raise HTTPException(400, f"Failed to read file: {str(e)}")

    if not txns:
        raise HTTPException(400, "The uploaded CSV contained no transactions.")

    decided = [(t, categorize(t)) for t in txns]
    return memory_store.save_batch(decided)

@router.patch("/rows/{row_id}", response_model=RowOut)
def patch_row(row_id: str, body: UpdateCategoryIn):
    row = memory_store.update_row(row_id, body.category)
    if not row:
        raise HTTPException(404, "Row not found")
    return row