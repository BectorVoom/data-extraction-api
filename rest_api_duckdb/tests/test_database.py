import pytest
from datetime import date
from app.services.database import DatabaseService


class TestDatabaseService:
    """Test DatabaseService functionality."""

    @pytest.fixture
    def db_service(self):
        """Create a fresh in-memory database service for each test."""
        service = DatabaseService(":memory:")
        service.initialize_sample_data()
        return service

    def test_connection_creation(self, db_service):
        """Test that database connection can be created."""
        conn = db_service.get_connection()
        assert conn is not None

    def test_sample_data_initialization(self, db_service):
        """Test that sample data is initialized correctly."""
        table_info = db_service.get_table_info()
        
        assert table_info["row_count"] > 0
        assert len(table_info["unique_ids"]) > 0
        assert table_info["date_range"]["min"] is not None
        assert table_info["date_range"]["max"] is not None

    def test_query_events_existing_id(self, db_service):
        """Test querying events for an existing ID."""
        results = db_service.query_events(
            id_filter="12345",
            from_date=date(2024, 1, 1),
            to_date=date(2024, 12, 31)
        )
        
        assert len(results) > 0
        for result in results:
            assert result["id"] == "12345"
            assert "event_date" in result
            assert "event_type" in result

    def test_query_events_non_existing_id(self, db_service):
        """Test querying events for a non-existing ID."""
        results = db_service.query_events(
            id_filter="nonexistent",
            from_date=date(2024, 1, 1),
            to_date=date(2024, 12, 31)
        )
        
        assert len(results) == 0

    def test_query_events_date_range_filter(self, db_service):
        """Test that date range filtering works correctly."""
        # Query for a very narrow date range
        results = db_service.query_events(
            id_filter="12345",
            from_date=date(2024, 1, 15),
            to_date=date(2024, 1, 15)
        )
        
        # Should only return events from that specific date
        for result in results:
            assert result["event_date"] == "2024-01-15"

    def test_query_events_no_results_in_range(self, db_service):
        """Test querying with a date range that has no results."""
        results = db_service.query_events(
            id_filter="12345",
            from_date=date(2025, 1, 1),
            to_date=date(2025, 12, 31)
        )
        
        assert len(results) == 0

    def test_query_events_ordered_by_date(self, db_service):
        """Test that query results are ordered by date and created_at."""
        results = db_service.query_events(
            id_filter="12345",
            from_date=date(2024, 1, 1),
            to_date=date(2024, 12, 31)
        )
        
        if len(results) > 1:
            # Check that dates are in ascending order
            dates = [result["event_date"] for result in results]
            assert dates == sorted(dates)

    def test_query_events_data_types(self, db_service):
        """Test that query results have correct data types."""
        results = db_service.query_events(
            id_filter="12345",
            from_date=date(2024, 1, 1),
            to_date=date(2024, 12, 31)
        )
        
        if results:
            result = results[0]
            assert isinstance(result["id"], str)
            assert isinstance(result["event_date"], str)
            assert isinstance(result["event_type"], str)
            assert isinstance(result["description"], str)
            assert isinstance(result["value"], (int, float))
            assert isinstance(result["created_at"], str)

    def test_get_table_info(self, db_service):
        """Test getting table information."""
        table_info = db_service.get_table_info()
        
        # Check required fields
        assert "schema" in table_info
        assert "row_count" in table_info
        assert "unique_ids" in table_info
        assert "date_range" in table_info
        
        # Check schema structure
        schema = table_info["schema"]
        column_names = [col["column"] for col in schema]
        expected_columns = ["id", "event_date", "event_type", "description", "value", "created_at"]
        for col in expected_columns:
            assert col in column_names

    def test_connection_reuse(self, db_service):
        """Test that connections are reused properly."""
        conn1 = db_service.get_connection()
        conn2 = db_service.get_connection()
        
        # Should be the same connection object
        assert conn1 is conn2

    def test_close_connection(self, db_service):
        """Test closing the database connection."""
        # Get connection first
        db_service.get_connection()
        
        # Close it
        db_service.close_connection()
        
        # Getting connection again should create a new one
        new_conn = db_service.get_connection()
        assert new_conn is not None

    def test_multiple_database_instances(self):
        """Test that multiple database instances work independently."""
        db1 = DatabaseService(":memory:")
        db2 = DatabaseService(":memory:")
        
        db1.initialize_sample_data()
        db2.initialize_sample_data()
        
        info1 = db1.get_table_info()
        info2 = db2.get_table_info()
        
        # Both should have data
        assert info1["row_count"] > 0
        assert info2["row_count"] > 0
        
        db1.close_connection()
        db2.close_connection()

    def test_parameterized_query_safety(self, db_service):
        """Test that parameterized queries are safe from injection."""
        # Try to inject SQL - this should not work due to parameterization
        malicious_id = "12345'; DROP TABLE events; --"
        
        # This should not cause an error and should return no results
        results = db_service.query_events(
            id_filter=malicious_id,
            from_date=date(2024, 1, 1),
            to_date=date(2024, 12, 31)
        )
        
        # Should return empty results (no matching ID)
        assert len(results) == 0
        
        # Table should still exist and have data
        table_info = db_service.get_table_info()
        assert table_info["row_count"] > 0

    def test_edge_case_date_ranges(self, db_service):
        """Test edge cases for date ranges."""
        # Same date for from and to
        results = db_service.query_events(
            id_filter="12345",
            from_date=date(2024, 1, 15),
            to_date=date(2024, 1, 15)
        )
        
        # Should work without error
        assert isinstance(results, list)
        
        # Very wide date range
        results = db_service.query_events(
            id_filter="12345",
            from_date=date(1900, 1, 1),
            to_date=date(2100, 12, 31)
        )
        
        # Should work without error
        assert isinstance(results, list)

    def test_parquet_integration(self):
        """Test Parquet file creation and loading."""
        import tempfile
        import os
        from app.services.database import DatabaseService
        
        with tempfile.TemporaryDirectory() as temp_dir:
            parquet_file = os.path.join(temp_dir, "test_events.parquet")
            
            # Create a new database service
            db_service = DatabaseService(":memory:")
            
            # Create sample Parquet file
            created_file = db_service.create_sample_parquet_file(parquet_file)
            assert os.path.exists(created_file)
            assert created_file == parquet_file
            
            # Initialize database from Parquet file
            db_service.initialize_from_parquet(parquet_file)
            
            # Test that data was loaded correctly
            table_info = db_service.get_table_info()
            assert table_info["row_count"] > 0
            assert len(table_info["unique_ids"]) > 0
            
            # Test querying the loaded data
            results = db_service.query_events("12345", None, None)
            assert len(results) > 0
            assert results[0]["id"] == "12345"
            
            # Test environment filtering
            prod_results = db_service.query_events(None, None, None, "production")
            assert len(prod_results) > 0
            for result in prod_results:
                assert result["environment"] == "production"

    def test_parquet_export(self):
        """Test exporting data to Parquet file."""
        import tempfile
        import os
        from app.services.database import DatabaseService
        
        with tempfile.TemporaryDirectory() as temp_dir:
            export_file = os.path.join(temp_dir, "export_events.parquet")
            
            # Create and initialize database service
            db_service = DatabaseService(":memory:")
            db_service.initialize_sample_data()
            
            # Export to Parquet
            exported_file = db_service.export_to_parquet(export_file)
            assert os.path.exists(exported_file)
            assert exported_file == export_file
            
            # Create another database and load the exported file
            db_service2 = DatabaseService(":memory:")
            db_service2.initialize_from_parquet(exported_file)
            
            # Verify data consistency
            original_info = db_service.get_table_info()
            loaded_info = db_service2.get_table_info()
            
            assert original_info["row_count"] == loaded_info["row_count"]
            assert set(original_info["unique_ids"]) == set(loaded_info["unique_ids"])