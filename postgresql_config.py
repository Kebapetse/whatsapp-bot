import psycopg2
import psycopg2.extras
import os
import logging
from datetime import datetime
from contextlib import contextmanager
import json

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        # Fix for Render's PostgreSQL URL format (if needed)
        if self.database_url.startswith('postgres://'):
            self.database_url = self.database_url.replace('postgres://', 'postgresql://', 1)
        
        self.init_database()
    
    def init_database(self):
        """Initialize the database and create tables if they don't exist"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Create businesses table
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS businesses (
                            id SERIAL PRIMARY KEY,
                            name VARCHAR(255) NOT NULL,
                            name_lower VARCHAR(255) NOT NULL,
                            address TEXT NOT NULL,
                            phone VARCHAR(50) NOT NULL,
                            email VARCHAR(255),
                            keywords TEXT[] NOT NULL,  -- PostgreSQL array for keywords
                            registered_by VARCHAR(50) NOT NULL,
                            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            status VARCHAR(20) DEFAULT 'active'
                        )
                    ''')
                    
                    # Create indexes for better search performance
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_name_lower ON businesses(name_lower)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON businesses(status)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_registered_at ON businesses(registered_at)')
                    cursor.execute('CREATE INDEX IF NOT EXISTS idx_keywords ON businesses USING GIN(keywords)')  # GIN index for array search
                    
                    # Create full-text search index for better search capabilities
                    cursor.execute('''
                        CREATE INDEX IF NOT EXISTS idx_business_search 
                        ON businesses USING GIN(to_tsvector('english', name || ' ' || address))
                    ''')
                    
                    conn.commit()
                    logger.info("PostgreSQL database initialized successfully")
                    
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise e
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = psycopg2.connect(self.database_url)
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def add_business(self, business_data):
        """Add a new business to the database"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO businesses 
                        (name, name_lower, address, phone, email, keywords, registered_by, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    ''', (
                        business_data['name'],
                        business_data['name'].lower(),
                        business_data['address'],
                        business_data['phone'],
                        business_data['email'],
                        business_data['keywords'],  # PostgreSQL handles arrays natively
                        business_data['registered_by'],
                        'active'
                    ))
                    
                    business_id = cursor.fetchone()[0]
                    conn.commit()
                    logger.info(f"Business added successfully with ID: {business_id}")
                    return business_id
                    
        except Exception as e:
            logger.error(f"Error adding business: {e}")
            raise e
    
    def search_businesses(self, query, limit=10):
        """Search for businesses by keywords or name using advanced PostgreSQL features"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    # Use PostgreSQL's array operations and full-text search
                    cursor.execute('''
                        SELECT *, 
                               CASE 
                                   WHEN %s = ANY(keywords) THEN 3  -- Exact keyword match
                                   WHEN name_lower LIKE %s THEN 2   -- Name contains query
                                   ELSE 1                           -- Other matches
                               END as relevance_score
                        FROM businesses 
                        WHERE (
                            %s = ANY(keywords) OR 
                            name_lower LIKE %s OR 
                            to_tsvector('english', name || ' ' || address) @@ plainto_tsquery('english', %s)
                        )
                        AND status = 'active'
                        ORDER BY relevance_score DESC, registered_at DESC
                        LIMIT %s
                    ''', (
                        query.lower(),  # Exact keyword match
                        f'%{query.lower()}%',  # Name LIKE pattern
                        query.lower(),  # Array search
                        f'%{query.lower()}%',  # Name LIKE pattern (repeated)
                        query,  # Full-text search
                        limit
                    ))
                    
                    rows = cursor.fetchall()
                    
                    # Convert to list of dictionaries
                    results = []
                    for row in rows:
                        business = dict(row)
                        # Remove the relevance_score from the final result
                        business.pop('relevance_score', None)
                        results.append(business)
                    
                    return results
                    
        except Exception as e:
            logger.error(f"Error searching businesses: {e}")
            return []
    
    def get_business_count(self):
        """Get total number of active businesses"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM businesses WHERE status = 'active'")
                    return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting business count: {e}")
            return 0
    
    def get_recent_businesses(self, limit=5):
        """Get recently registered businesses"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute('''
                        SELECT name, registered_at FROM businesses 
                        WHERE status = 'active'
                        ORDER BY registered_at DESC
                        LIMIT %s
                    ''', (limit,))
                    
                    return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting recent businesses: {e}")
            return []
    
    def get_popular_keywords(self, limit=10):
        """Get most popular keywords across all businesses"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT keyword, COUNT(*) as frequency
                        FROM businesses, unnest(keywords) as keyword 
                        WHERE status = 'active'
                        GROUP BY keyword
                        ORDER BY frequency DESC, keyword
                        LIMIT %s
                    ''', (limit,))
                    
                    return [{'keyword': row[0], 'count': row[1]} for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting popular keywords: {e}")
            return []
    
    def search_by_location(self, location_query, limit=10):
        """Search businesses by location/address"""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute('''
                        SELECT * FROM businesses 
                        WHERE address ILIKE %s AND status = 'active'
                        ORDER BY registered_at DESC
                        LIMIT %s
                    ''', (f'%{location_query}%', limit))
                    
                    return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error searching by location: {e}")
            return []

# Initialize database manager
db_manager = None

def init_database():
    """Initialize database manager"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager

def get_db():
    """Get database manager instance"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager