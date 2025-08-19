import duckdb
from typing import List, Dict, Any, Optional
from datetime import date
import logging
import os

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for managing DuckDB connections and queries."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the database service.
        
        Args:
            db_path: Path to the DuckDB database file. If None, uses in-memory database.
        """
        self.db_path = db_path or ":memory:"
        self._connection: Optional[duckdb.DuckDBPyConnection] = None
    
    def get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get or create a database connection."""
        if self._connection is None:
            try:
                self._connection = duckdb.connect(database=self.db_path)
                logger.info(f"Connected to DuckDB at {self.db_path}")
            except Exception as e:
                logger.error(f"Failed to connect to DuckDB: {e}")
                raise
        return self._connection
    
    def close_connection(self):
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("DuckDB connection closed")
    
    def initialize_sample_data(self):
        """Initialize the database with sample data for testing."""
        conn = self.get_connection()
        
        try:
            # Create a sample events table
            conn.execute("""
                CREATE OR REPLACE TABLE events (
                    id VARCHAR,
                    event_date DATE,
                    event_type VARCHAR,
                    description VARCHAR,
                    value DOUBLE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert sample data
            sample_data = [
                ('12345', '2024-01-15', 'login', 'User login event', 1.0),
                ('12345', '2024-02-20', 'purchase', 'Product purchase', 99.99),
                ('12345', '2024-03-10', 'logout', 'User logout event', 1.0),
                ('67890', '2024-01-20', 'login', 'User login event', 1.0),
                ('67890', '2024-02-25', 'view', 'Product view event', 0.0),
                ('67890', '2024-04-15', 'purchase', 'Product purchase', 49.99),
                ('11111', '2024-05-01', 'signup', 'New user signup', 0.0),
                ('11111', '2024-05-02', 'login', 'First login', 1.0),
                ('22222', '2023-12-15', 'login', 'Login event', 1.0),
                ('22222', '2024-01-01', 'purchase', 'New Year purchase', 199.99),
            ]
            
            conn.executemany(
                "INSERT INTO events (id, event_date, event_type, description, value) VALUES (?, ?, ?, ?, ?)",
                sample_data
            )
            
            # Create an index for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_id_date ON events(id, event_date)")
            
            logger.info("Sample data initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize sample data: {e}")
            raise
    
    def query_events(self, id_filter: str, from_date: date, to_date: date) -> List[Dict[str, Any]]:
        """
        Query events based on id and date range.
        
        Args:
            id_filter: ID to filter events
            from_date: Start date (inclusive)
            to_date: End date (inclusive)
            
        Returns:
            List of matching event records
        """
        conn = self.get_connection()
        
        try:
            # Use parameterized query to prevent SQL injection
            sql = """
                SELECT 
                    id,
                    event_date,
                    event_type,
                    description,
                    value,
                    created_at
                FROM events 
                WHERE id = ? 
                AND event_date BETWEEN ? AND ?
                ORDER BY event_date ASC, created_at ASC
            """
            
            logger.info(f"Executing query for id={id_filter}, from_date={from_date}, to_date={to_date}")
            
            # Execute the parameterized query
            result = conn.execute(sql, [str(id_filter), from_date, to_date])
            
            # Fetch all results
            rows = result.fetchall()
            columns = [desc[0] for desc in result.description]
            
            # Convert to list of dictionaries
            data = []
            for row in rows:
                row_dict = {}
                for i, value in enumerate(row):
                    # Handle date serialization
                    if isinstance(value, date):
                        row_dict[columns[i]] = value.isoformat()
                    elif hasattr(value, 'isoformat'):  # datetime objects
                        row_dict[columns[i]] = value.isoformat()
                    else:
                        row_dict[columns[i]] = value
                data.append(row_dict)
            
            logger.info(f"Query returned {len(data)} rows")
            return data
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def get_table_info(self) -> Dict[str, Any]:
        """Get information about the events table."""
        conn = self.get_connection()
        
        try:
            # Get table schema
            schema_result = conn.execute("DESCRIBE events").fetchall()
            schema = [{"column": row[0], "type": row[1], "null": row[2]} for row in schema_result]
            
            # Get row count
            count_result = conn.execute("SELECT COUNT(*) FROM events").fetchone()
            row_count = count_result[0] if count_result else 0
            
            # Get unique IDs
            ids_result = conn.execute("SELECT DISTINCT id FROM events ORDER BY id").fetchall()
            unique_ids = [row[0] for row in ids_result]
            
            # Get date range
            date_range_result = conn.execute(
                "SELECT MIN(event_date), MAX(event_date) FROM events"
            ).fetchone()
            
            min_date = date_range_result[0].isoformat() if date_range_result[0] else None
            max_date = date_range_result[1].isoformat() if date_range_result[1] else None
            
            return {
                "schema": schema,
                "row_count": row_count,
                "unique_ids": unique_ids,
                "date_range": {"min": min_date, "max": max_date}
            }
            
        except Exception as e:
            logger.error(f"Failed to get table info: {e}")
            raise


# Global database service instance
_db_service: Optional[DatabaseService] = None


def get_database_service() -> DatabaseService:
    """Get the global database service instance."""
    global _db_service
    if _db_service is None:
        # Use environment variable for database path or default to in-memory
        db_path = os.getenv("DUCKDB_DATABASE_PATH", ":memory:")
        _db_service = DatabaseService(db_path)
        _db_service.initialize_sample_data()
    return _db_service


def close_database_service():
    """Close the global database service."""
    global _db_service
    if _db_service:
        _db_service.close_connection()
        _db_service = None