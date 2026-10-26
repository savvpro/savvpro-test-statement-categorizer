from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.models.db import base, getdb

testengine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
testingsessionlocal = sessionmaker(autocommit=False, autoflush=False, bind=testengine)
base.metadata.create_all(bind=testengine)

def overridelgetdb():
    try:
        db = testingsessionlocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[getdb] = overridelgetdb
client = TestClient(app)

def testhealthcheck() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def testcategories() -> None:
    response = client.get("/api/categories")
    assert response.status_code == 200
    assert "Software & Tools" in response.json()