import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    try:
        # Get database connection parameters from environment
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            # If DATABASE_URL is not set, construct from individual parameters
            db_user = os.getenv('PGUSER')
            db_password = os.getenv('PGPASSWORD')
            db_host = os.getenv('PGHOST')
            db_port = os.getenv('PGPORT')
            db_name = os.getenv('PGDATABASE')

            if not all([db_user, db_password, db_host, db_port, db_name]):
                raise ValueError("Missing required database environment variables")

            db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

        logger.info("Creating database engine...")
        engine = create_engine(db_url, pool_pre_ping=True)

        # Test connection
        engine.connect()
        logger.info("Database connection successful")

        # Create session factory
        Session = sessionmaker(bind=engine)
        return Session()

    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise

def init_db():
    """Initialize database tables"""
    try:
        logger.info("Initializing database...")
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            db_user = os.getenv('PGUSER')
            db_password = os.getenv('PGPASSWORD')
            db_host = os.getenv('PGHOST')
            db_port = os.getenv('PGPORT')
            db_name = os.getenv('PGDATABASE')

            if not all([db_user, db_password, db_host, db_port, db_name]):
                raise ValueError("Missing required database environment variables")

            db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

        engine = create_engine(db_url)
        Base.metadata.create_all(engine)
        logger.info("Database initialization completed successfully")

    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        raise