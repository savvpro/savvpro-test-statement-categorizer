from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASEURL

engine = create_engine(DATABASEURL, connect_args={"check_same_thread": False})
sessionlocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
base = declarative_base()

class Upload(base):
    __tablename__ = "uploads"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)

class Transaction(base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    uploadid = Column(Integer, ForeignKey("uploads.id"))
    date = Column(Date)
    descriptionraw = Column(String)
    amount = Column(Numeric)
    balance = Column(Numeric, nullable=True)
    sourcerow = Column(Integer)
    category = Column(String)
    confidence = Column(Numeric)
    reason = Column(String)
    route = Column(String)
    signals = Column(JSON)
    conflicts = Column(JSON)
    suggestedcategory = Column(String, nullable=True)
    tworeasonsmet = Column(Boolean)
    isrefund = Column(Boolean)
    isduplicate = Column(Boolean)
    isrecurring = Column(Boolean)

class Rule(base):
    __tablename__ = "rules"
    id = Column(Integer, primary_key=True, index=True)
    merchantkey = Column(String, unique=True, index=True)
    category = Column(String)

base.metadata.create_all(bind=engine)

def getdb():
    db = sessionlocal()
    try:
        yield db
    finally:
        db.close()