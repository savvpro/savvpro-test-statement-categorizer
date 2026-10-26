"""
FastAPI backend for statement categorizer.
Handles CSV upload and transaction categorization.
"""
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import pandas as pd
import io
from typing import List, Dict
from pydantic import BaseModel

from brain import categorize_transaction, get_category_summary


app = FastAPI(
    title="Statement Categorizer API",
    description="Rule-based transaction categorization for freelancers and agencies",
    version="1.0.0"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TransactionResponse(BaseModel):
    """Response model for a single transaction."""
    date: str
    description: str
    amount: float
    category: str
    confidence: str


class CategorizeResponse(BaseModel):
    """Response model for categorization result."""
    transactions: List[TransactionResponse]
    summary: Dict[str, int]
    total_transactions: int


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Statement Categorizer API",
        "version": "1.0.0"
    }


@app.get("/api/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "brain": "operational",
        "endpoints": ["/", "/api/health", "/api/upload"]
    }


def validate_csv_structure(df: pd.DataFrame) -> None:
    """
    Validate that CSV has required columns.
    
    Expected columns: date, description, amount
    """
    required_columns = {"date", "description", "amount"}
    df_columns = set(df.columns.str.lower().str.strip())
    
    if not required_columns.issubset(df_columns):
        missing = required_columns - df_columns
        raise HTTPException(
            status_code=400,
            detail=f"CSV missing required columns: {', '.join(missing)}. "
                   f"Expected: date, description, amount"
        )


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to lowercase and strip whitespace."""
    df.columns = df.columns.str.lower().str.strip()
    return df


def parse_csv_file(file_content: bytes) -> pd.DataFrame:
    """
    Parse CSV file content into pandas DataFrame.
    
    Handles various CSV formats and encodings.
    """
    try:
        # Try UTF-8 first
        df = pd.read_csv(io.BytesIO(file_content))
    except UnicodeDecodeError:
        # Fallback to latin-1 encoding
        try:
            df = pd.read_csv(io.BytesIO(file_content), encoding='latin-1')
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to parse CSV file: {str(e)}"
            )
    except pd.errors.EmptyDataError:
        raise HTTPException(
            status_code=400,
            detail="CSV file is empty"
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid CSV format: {str(e)}"
        )
    
    return df


def process_transactions(df: pd.DataFrame) -> List[Dict]:
    """
    Process each transaction through the categorization brain.
    
    Args:
        df: DataFrame with date, description, amount columns
    
    Returns:
        List of categorized transactions
    """
    categorized_transactions = []
    
    for idx, row in df.iterrows():
        try:
            # Extract fields
            date = str(row.get('date', '')).strip()
            description = str(row.get('description', '')).strip()
            
            # Handle amount parsing
            try:
                amount = float(row.get('amount', 0))
            except (ValueError, TypeError):
                amount = 0.0
            
            # Categorize using the brain
            result = categorize_transaction(description, amount)
            
            # Build response object
            transaction = {
                "date": date,
                "description": description,
                "amount": amount,
                "category": result["category"],
                "confidence": result["confidence"]
            }
            
            categorized_transactions.append(transaction)
            
        except Exception as e:
            # If a row fails, mark it for review
            categorized_transactions.append({
                "date": str(row.get('date', '')),
                "description": str(row.get('description', 'Error processing row')),
                "amount": 0.0,
                "category": "Needs Review",
                "confidence": "Low"
            })
    
    return categorized_transactions


@app.post("/api/upload", response_model=CategorizeResponse)
async def upload_statement(file: UploadFile = File(...)):
    """
    Upload and categorize a bank/credit card statement.
    
    Expected CSV format:
    - Headers: date, description, amount
    - Date: any format (will be stored as-is)
    - Description: transaction description text
    - Amount: numeric (positive = credit/income, negative = debit/expense)
    
    Returns:
        JSON with categorized transactions and summary statistics
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported. Please upload a .csv file."
        )
    
    try:
        # Read file content
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty"
            )
        
        # Parse CSV
        df = parse_csv_file(content)
        
        # Normalize column names
        df = normalize_column_names(df)
        
        # Validate structure
        validate_csv_structure(df)
        
        # Process transactions
        categorized_transactions = process_transactions(df)
        
        # Generate summary
        summary = get_category_summary(categorized_transactions)
        
        return {
            "transactions": categorized_transactions,
            "summary": summary,
            "total_transactions": len(categorized_transactions)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
