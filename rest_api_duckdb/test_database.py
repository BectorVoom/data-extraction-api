#!/usr/bin/env python3
"""
Script to test database initialization and sample data creation.
"""

import sys
from datetime import date
from app.services.database import get_database_service


def main():
    """Test the database service."""
    print("Testing DuckDB service...")
    
    try:
        # Get the database service (this will initialize sample data)
        db_service = get_database_service()
        
        # Get table info
        print("\n--- Table Information ---")
        table_info = db_service.get_table_info()
        print(f"Row count: {table_info['row_count']}")
        print(f"Unique IDs: {table_info['unique_ids']}")
        print(f"Date range: {table_info['date_range']['min']} to {table_info['date_range']['max']}")
        print(f"Schema: {table_info['schema']}")
        
        # Test query
        print("\n--- Sample Query ---")
        print("Querying events for ID '12345' between 2024/01/01 and 2024/12/31...")
        
        results = db_service.query_events(
            id_filter="12345",
            from_date=date(2024, 1, 1),
            to_date=date(2024, 12, 31)
        )
        
        print(f"Found {len(results)} events:")
        for event in results:
            print(f"  - {event['event_date']}: {event['event_type']} - {event['description']} (${event['value']})")
            
        print("\n✅ Database service test completed successfully!")
        
    except Exception as e:
        print(f"❌ Database service test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()