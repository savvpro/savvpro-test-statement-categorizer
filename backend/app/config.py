import os

DATABASEURL = os.getenv("DATABASEURL", "sqlite:///./local.db")