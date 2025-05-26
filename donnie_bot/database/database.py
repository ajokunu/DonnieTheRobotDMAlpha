import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
import logging
from .models import Base

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.Session = None
        self._initialized = False
    
    def initialize(self, database_url: str = None):
        """Initialize database connection"""
        if self._initialized:
            return
        
        if database_url is None:
            # Default to SQLite for development, PostgreSQL for production
            if os.getenv('ENVIRONMENT') == 'production':
                database_url = os.getenv('DATABASE_URL')
                if not database_url:
                    raise ValueError("DATABASE_URL environment variable required for production")
            else:
                # SQLite for development
                os.makedirs('data', exist_ok=True)
                database_url = 'sqlite:///data/donnie_campaign.db'
        
        try:
            # Create engine with connection pooling
            if database_url.startswith('sqlite'):
                self.engine = create_engine(
                    database_url,
                    echo=False,  # Set to True for SQL logging
                    connect_args={'check_same_thread': False}
                )
            else:
                self.engine = create_engine(
                    database_url,
                    echo=False,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True  # Verify connections before use
                )
            
            # Create session factory
            self.Session = scoped_session(
                sessionmaker(bind=self.engine, expire_on_commit=False)
            )
            
            # Create all tables
            Base.metadata.create_all(self.engine)
            
            self._initialized = True
            logger.info(f"Database initialized: {database_url}")
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    @contextmanager
    def get_session(self):
        """Context manager for database sessions"""
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def health_check(self):
        """Check if database is accessible"""
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def close(self):
        """Close database connections"""
        if self.Session:
            self.Session.remove()
        if self.engine:
            self.engine.dispose()
        self._initialized = False
        logger.info("Database connections closed")

# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions
def init_database(database_url: str = None):
    """Initialize the database"""
    db_manager.initialize(database_url)

def get_db_session():
    """Get a database session context manager"""
    return db_manager.get_session()

def close_database():
    """Close database connections"""
    db_manager.close()

# Auto-initialize on import if environment variables are set
if os.getenv('AUTO_INIT_DB', 'true').lower() == 'true':
    try:
        init_database()
    except Exception as e:
        logger.warning(f"Auto-initialization failed: {e}")
        logger.info("Database will need to be manually initialized")