import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Create base class for declarative models
Base = declarative_base()

class TrainDetails(Base):
    __tablename__ = 'train_details'
    
    id = Column(Integer, primary_key=True)
    train_id = Column(String, nullable=False)
    station = Column(String, nullable=False)
    time_actual = Column(DateTime, nullable=False)
    time_scheduled = Column(DateTime, nullable=False)
    delay = Column(Integer)
    status = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

def get_database_connection():
    """Create database connection using environment variables"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()

def init_db():
    """Initialize database tables"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
