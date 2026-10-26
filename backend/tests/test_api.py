from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_upload_sample():
    with open("../sample_data/sample_statement.csv", "rb") as f:
        r = client.post("/upload", files={"file": ("s.csv", f, "text/csv")})
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 10
    cats = {row["category"] for row in body}
    assert "Income/Payout" in cats
    assert "Needs Review" in cats