"""
Integration tests for FastAPI endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from main import app
import io


client = TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_health_check_endpoint(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["brain"] == "operational"


class TestUploadEndpoint:
    """Test CSV upload and categorization endpoint."""
    
    def test_upload_valid_csv(self):
        """Test uploading a valid CSV file."""
        csv_content = """date,description,amount
2024-01-15,ADOBE CREATIVE CLOUD,-49.99
2024-01-16,UBER TRIP TO OFFICE,-25.50
2024-01-17,UPWORK PAYMENT,2500.00
2024-01-18,STRIPE TRANSFER IN,1200.00
2024-01-19,AMAZON REFUND,45.00
2024-01-20,JOES CAFE,-15.00"""
        
        files = {"file": ("statement.csv", csv_content, "text/csv")}
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "transactions" in data
        assert "summary" in data
        assert "total_transactions" in data
        assert data["total_transactions"] == 6
        
        # Verify categorizations
        transactions = data["transactions"]
        assert transactions[0]["category"] == "Software & Tools"
        assert transactions[1]["category"] == "Travel & Transport"
        assert transactions[2]["category"] == "Client Income"
        assert transactions[3]["category"] == "Client Income"
        assert transactions[4]["category"] == "Expense Refund"
        assert transactions[5]["category"] == "Needs Review"
    
    def test_upload_non_csv_file(self):
        """Test uploading a non-CSV file."""
        files = {"file": ("document.txt", "not a csv", "text/plain")}
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 400
        assert "Only CSV files are supported" in response.json()["detail"]
    
    def test_upload_empty_csv(self):
        """Test uploading an empty CSV file."""
        files = {"file": ("empty.csv", "", "text/csv")}
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 400
    
    def test_upload_csv_missing_columns(self):
        """Test uploading CSV with missing required columns."""
        csv_content = """date,description
2024-01-15,ADOBE CREATIVE CLOUD
2024-01-16,UBER TRIP"""
        
        files = {"file": ("incomplete.csv", csv_content, "text/csv")}
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 400
        assert "missing required columns" in response.json()["detail"].lower()
    
    def test_upload_csv_with_extra_columns(self):
        """Test uploading CSV with extra columns (should work)."""
        csv_content = """date,description,amount,category,notes
2024-01-15,ADOBE CREATIVE CLOUD,-49.99,Business,For design work
2024-01-16,UBER TRIP,-25.50,Travel,Client meeting"""
        
        files = {"file": ("statement.csv", csv_content, "text/csv")}
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_transactions"] == 2
    
    def test_summary_counts(self):
        """Test that summary counts are accurate."""
        csv_content = """date,description,amount
2024-01-15,ADOBE CREATIVE CLOUD,-49.99
2024-01-16,FIGMA PRO,-15.00
2024-01-17,UBER TRIP,-25.50
2024-01-18,UPWORK PAYMENT,2500.00
2024-01-19,STRIPE PAYMENT,1200.00"""
        
        files = {"file": ("statement.csv", csv_content, "text/csv")}
        response = client.post("/api/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        summary = data["summary"]
        
        assert summary["Software & Tools"] == 2
        assert summary["Travel & Transport"] == 1
        assert summary["Client Income"] == 2
        assert summary["Needs Review"] == 0


class TestCORSHeaders:
    """Test CORS configuration."""
    
    def test_cors_headers_present(self):
        # Send OPTIONS preflight request to verify CORS middleware headers
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        }
        response = client.options("/api/upload", headers=headers)
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
