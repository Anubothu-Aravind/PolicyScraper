# db/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, create_engine, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()

class Insurer(Base):
    __tablename__ = "insurers"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    url = Column(String)

class PolicyDocument(Base):
    __tablename__ = "policy_documents"
    id = Column(Integer, primary_key=True)
    insurer_id = Column(Integer, ForeignKey("insurers.id"), nullable=True)
    product_name = Column(String)
    url = Column(String)
    file_path = Column(String)
    file_hash = Column(String)
    scraped_at = Column(DateTime, default=datetime.datetime.utcnow)
    meta = Column(JSON)

class PolicySection(Base):
    __tablename__ = "policy_sections"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("policy_documents.id"))
    section_title = Column(String)
    section_text = Column(Text)
    start_page = Column(Integer)
    end_page = Column(Integer)
    extracted_items = Column(JSON)  # store extracted slots

# create engine
if __name__ == "__main__":
    engine = create_engine("postgresql://user:pass@localhost/policydb")
    Base.metadata.create_all(engine)
