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
    
    def create_sample_parquet_file(self, parquet_file_path: str = "data/events.parquet"):
        """Create a sample Parquet file with event data."""
        import pandas as pd
        import os
        
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(parquet_file_path), exist_ok=True)
        
        # Sample data with environment values
        data = {
            'id': ['12345', '12345', '12345', '67890', '67890', '67890', 
                   '11111', '11111', '22222', '22222', '33333', '33333'],
            'event_date': ['2024-01-15', '2024-02-20', '2024-03-10', '2024-01-20', 
                          '2024-02-25', '2024-04-15', '2024-05-01', '2024-05-02',
                          '2023-12-15', '2024-01-01', '2024-06-01', '2024-06-02'],
            'event_type': ['login', 'purchase', 'logout', 'login', 'view', 'purchase',
                          'signup', 'login', 'login', 'purchase', 'api_call', 'error'],
            'description': ['User login event', 'Product purchase', 'User logout event', 
                           'User login event', 'Product view event', 'Product purchase',
                           'New user signup', 'First login', 'Login event', 'New Year purchase',
                           'External API call', 'System error occurred'],
            'value': [1.0, 99.99, 1.0, 1.0, 0.0, 49.99, 0.0, 1.0, 1.0, 199.99, 2.5, 0.0],
            'environment': ['production', 'production', 'production', 'staging', 'staging', 'staging',
                           'development', 'development', 'production', 'production', 'staging', 'staging']
        }
        
        # Create DataFrame and convert date column
        df = pd.DataFrame(data)
        df['event_date'] = pd.to_datetime(df['event_date']).dt.date
        df['created_at'] = pd.Timestamp.now()
        
        # Save to Parquet
        df.to_parquet(parquet_file_path, index=False)
        logger.info(f"Sample Parquet file created at {parquet_file_path}")
        
        return parquet_file_path

    def initialize_from_parquet(self, parquet_file_path: str = "data/events.parquet"):
        """Initialize the database from a Parquet file."""
        conn = self.get_connection()
        
        try:
            # Check if Parquet file exists, create if not
            if not os.path.exists(parquet_file_path):
                logger.info(f"Parquet file not found at {parquet_file_path}, creating sample data")
                self.create_sample_parquet_file(parquet_file_path)
            
            # Create table from Parquet file
            conn.execute(f"""
                CREATE OR REPLACE TABLE events AS 
                SELECT * FROM read_parquet('{parquet_file_path}')
            """)
            
            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_id_date ON events(id, event_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_environment ON events(environment)")
            
            # Get row count for logging
            count_result = conn.execute("SELECT COUNT(*) FROM events").fetchone()
            row_count = count_result[0] if count_result else 0
            
            logger.info(f"Loaded {row_count} records from Parquet file: {parquet_file_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize from Parquet file: {e}")
            # Fallback to in-memory sample data if Parquet loading fails
            logger.warning("Falling back to in-memory sample data")
            self.initialize_sample_data()
            raise

    def initialize_sample_data(self):
        """Initialize the database with sample data (fallback method)."""
        conn = self.get_connection()
        
        try:
            # Create a sample events table with environment field
            conn.execute("""
                CREATE OR REPLACE TABLE events (
                    id VARCHAR,
                    event_date DATE,
                    event_type VARCHAR,
                    description VARCHAR,
                    value DOUBLE,
                    environment VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert sample data with environment values
            sample_data = [
                ('12345', '2024-01-15', 'login', 'User login event', 1.0, 'production'),
                ('12345', '2024-02-20', 'purchase', 'Product purchase', 99.99, 'production'),
                ('12345', '2024-03-10', 'logout', 'User logout event', 1.0, 'production'),
                ('67890', '2024-01-20', 'login', 'User login event', 1.0, 'staging'),
                ('67890', '2024-02-25', 'view', 'Product view event', 0.0, 'staging'),
                ('67890', '2024-04-15', 'purchase', 'Product purchase', 49.99, 'staging'),
                ('11111', '2024-05-01', 'signup', 'New user signup', 0.0, 'development'),
                ('11111', '2024-05-02', 'login', 'First login', 1.0, 'development'),
                ('22222', '2023-12-15', 'login', 'Login event', 1.0, 'production'),
                ('22222', '2024-01-01', 'purchase', 'New Year purchase', 199.99, 'production'),
                ('33333', '2024-06-01', 'api_call', 'External API call', 2.5, 'staging'),
                ('33333', '2024-06-02', 'error', 'System error occurred', 0.0, 'staging'),
            ]
            
            conn.executemany(
                "INSERT INTO events (id, event_date, event_type, description, value, environment) VALUES (?, ?, ?, ?, ?, ?)",
                sample_data
            )
            
            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_id_date ON events(id, event_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_environment ON events(environment)")
            
            logger.info("Sample data initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize sample data: {e}")
            raise

    def export_to_parquet(self, parquet_file_path: str = "data/events_export.parquet"):
        """Export current events table to a Parquet file."""
        conn = self.get_connection()
        
        try:
            # Create data directory if it doesn't exist
            os.makedirs(os.path.dirname(parquet_file_path), exist_ok=True)
            
            # Export to Parquet
            conn.execute(f"""
                COPY events TO '{parquet_file_path}' (FORMAT PARQUET)
            """)
            
            # Get row count for logging
            count_result = conn.execute("SELECT COUNT(*) FROM events").fetchone()
            row_count = count_result[0] if count_result else 0
            
            logger.info(f"Exported {row_count} records to Parquet file: {parquet_file_path}")
            return parquet_file_path
            
        except Exception as e:
            logger.error(f"Failed to export to Parquet file: {e}")
            raise
    
    def query_events(self, id_filter: Optional[str], from_date: Optional[date], to_date: Optional[date], environment: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Query events based on id, date range, and environment.
        
        Args:
            id_filter: ID to filter events (optional, unbounded if None)
            from_date: Start date (inclusive, unbounded if None)
            to_date: End date (inclusive, unbounded if None)
            environment: Environment to filter events (optional)
            
        Returns:
            List of matching event records
        """
        conn = self.get_connection()
        
        try:
            # Build dynamic query based on provided filters
            where_conditions = []
            params = []
            
            if id_filter is not None:
                where_conditions.append("id = ?")
                params.append(str(id_filter))
            
            if from_date is not None:
                where_conditions.append("event_date >= ?")
                params.append(from_date)
                
            if to_date is not None:
                where_conditions.append("event_date <= ?")
                params.append(to_date)
                
            if environment is not None:
                where_conditions.append("environment = ?")
                params.append(environment)
            
            # Build the WHERE clause
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            sql = f"""
                SELECT 
                    id,
                    event_date,
                    event_type,
                    description,
                    value,
                    environment,
                    created_at
                FROM events 
                {where_clause}
                ORDER BY event_date ASC, created_at ASC
            """
            
            logger.info(f"Executing query for id={id_filter}, from_date={from_date}, to_date={to_date}, environment={environment}")
            logger.debug(f"SQL: {sql}")
            logger.debug(f"Parameters: {params}")
            
            # Execute the parameterized query
            result = conn.execute(sql, params)
            
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
    
    def query_events_to_feather(self, id_filter: Optional[str], from_date: Optional[date], to_date: Optional[date], environment: Optional[str] = None) -> bytes:
        """
        Query events and return results as Apache Arrow Feather format.
        
        Args:
            id_filter: ID to filter events (optional, unbounded if None)
            from_date: Start date (inclusive, unbounded if None)
            to_date: End date (inclusive, unbounded if None)
            environment: Environment to filter events (optional)
            
        Returns:
            Feather file content as bytes
        """
        import pyarrow as pa
        import pyarrow.feather as feather
        from io import BytesIO
        
        conn = self.get_connection()
        
        try:
            # Build dynamic query based on provided filters
            where_conditions = []
            params = []
            
            if id_filter is not None:
                where_conditions.append("id = ?")
                params.append(str(id_filter))
            
            if from_date is not None:
                where_conditions.append("event_date >= ?")
                params.append(from_date)
                
            if to_date is not None:
                where_conditions.append("event_date <= ?")
                params.append(to_date)
                
            if environment is not None:
                where_conditions.append("environment = ?")
                params.append(environment)
            
            # Build the WHERE clause
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            sql = f"""
                SELECT 
                    id,
                    event_date,
                    event_type,
                    description,
                    value,
                    environment,
                    created_at
                FROM events 
                {where_clause}
                ORDER BY event_date ASC, created_at ASC
            """
            
            logger.info(f"Executing Feather query for id={id_filter}, from_date={from_date}, to_date={to_date}, environment={environment}")
            logger.debug(f"SQL: {sql}")
            logger.debug(f"Parameters: {params}")
            
            # Execute the parameterized query and convert directly to Arrow
            result = conn.execute(sql, params)
            
            # Convert DuckDB result to Arrow Table directly
            arrow_table = result.fetch_arrow_table()
            
            # Convert Arrow table to Feather format in memory
            buffer = BytesIO()
            feather.write_feather(arrow_table, buffer, compression="uncompressed")
            
            feather_bytes = buffer.getvalue()
            logger.info(f"Generated Feather file with {len(arrow_table)} rows, size: {len(feather_bytes)} bytes")
            
            return feather_bytes
            
        except Exception as e:
            logger.error(f"Feather query execution failed: {e}")
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
        
        # Use Parquet files if available, fallback to sample data
        parquet_path = os.getenv("PARQUET_DATA_PATH", "data/events.parquet")
        try:
            _db_service.initialize_from_parquet(parquet_path)
        except Exception as e:
            logger.warning(f"Failed to initialize from Parquet, using sample data: {e}")
            _db_service.initialize_sample_data()
    return _db_service


def close_database_service():
    """Close the global database service."""
    global _db_service
    if _db_service:
        _db_service.close_connection()
        _db_service = None