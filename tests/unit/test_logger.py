import pytest
import asyncio
import datetime
import os
from unittest.mock import patch, MagicMock, AsyncMock

from modules.logger import (
    logger, 
    log_access, 
    log_security, 
    log_system, 
    get_logs, 
    get_log_counts,
    Logger,
    SQLiteHandler,
    ContextFilter
)
from db.clientSQLite import AsyncSQLiteClient


class TestContextFilter:
    
    def test_filter_adds_context(self):
        """Test that ContextFilter adds context to log records."""
        # Create a filter with context
        context = {"client_ip": "127.0.0.1", "username": "test_user"}
        filter_instance = ContextFilter(context)
        
        # Create a mock record
        record = MagicMock()
        
        # Apply the filter
        result = filter_instance.filter(record)
        
        # Check that context is added
        assert result is True
        assert record.client_ip == "127.0.0.1"
        assert record.username == "test_user"
    
    def test_filter_sets_defaults(self):
        """Test that ContextFilter sets default values for missing fields."""
        # Create a filter with no context
        filter_instance = ContextFilter()
        
        # Create a mock record
        record = MagicMock()
        delattr(record, 'client_ip') if hasattr(record, 'client_ip') else None
        delattr(record, 'username') if hasattr(record, 'username') else None
        
        # Apply the filter
        filter_instance.filter(record)
        
        # Check that defaults are set
        assert record.client_ip == '-'
        assert record.username == '-'


class TestSQLiteHandler:
    
    @pytest.mark.asyncio
    async def test_setup(self, monkeypatch):
        """Test that SQLiteHandler.setup initializes the client."""
        # Mock the AsyncSQLiteClient
        mock_client = MagicMock()
        
        # Create a future that returns the mock client
        future = asyncio.Future()
        future.set_result(mock_client)
        
        # Create async mocks
        mock_client.setup = AsyncMock()
        
        # Mock the get_instance method
        async def mock_get_instance(*args, **kwargs):
            return mock_client
            
        monkeypatch.setattr(AsyncSQLiteClient, 'get_instance', mock_get_instance)
        
        # Create a handler
        handler = SQLiteHandler('test')
        
        # Setup the handler
        await handler.setup()
        
        # Check that client is set and setup was called
        assert handler.client is not None
        mock_client.setup.assert_called_once()


@pytest.mark.asyncio
async def test_get_logs(monkeypatch):
    """Test get_logs function."""
    # Mock the AsyncSQLiteClient to use our test database
    mock_client = MagicMock()
    mock_logs = [{
        "id": 1,
        "timestamp": datetime.datetime.now().isoformat(),
        "level": "INFO",
        "module": "test_module",
        "function": "test_function",
        "message": "Test message"
    }]
    
    # Create async mock for query_logs
    async def mock_query_logs(*args, **kwargs):
        return mock_logs
    
    mock_client.query_logs = mock_query_logs
    mock_client.setup = AsyncMock()
    
    # Mock the get_instance method
    async def mock_get_instance(*args, **kwargs):
        return mock_client
        
    monkeypatch.setattr(AsyncSQLiteClient, 'get_instance', mock_get_instance)
    
    # Call get_logs
    logs = await get_logs("system")
    
    # Check result
    assert len(logs) == 1
    assert logs[0]["level"] == "INFO"
    assert logs[0]["module"] == "test_module"
    assert logs[0]["function"] == "test_function"
    assert logs[0]["message"] == "Test message"


@pytest.mark.asyncio
async def test_get_log_counts(monkeypatch):
    """Test get_log_counts function."""
    # Mock the AsyncSQLiteClient to use our test database
    mock_client = MagicMock()
    mock_counts = {
        "access_logs": 5,
        "security_logs": 3,
        "system_logs": 2
    }
    
    # Create async mock for get_log_counts
    async def mock_get_counts(*args, **kwargs):
        return mock_counts
    
    mock_client.get_log_counts = mock_get_counts
    mock_client.setup = AsyncMock()
    
    # Mock the get_instance method
    async def mock_get_instance(*args, **kwargs):
        return mock_client
        
    monkeypatch.setattr(AsyncSQLiteClient, 'get_instance', mock_get_instance)
    
    # Call get_log_counts
    counts = await get_log_counts()
    
    # Check result
    assert counts["access_logs"] == 5
    assert counts["security_logs"] == 3
    assert counts["system_logs"] == 2


class TestLoggerInstance:
    
    def test_logger_singleton(self):
        """Test that Logger is a singleton."""
        # Get two instances
        logger1 = Logger()
        logger2 = Logger()
        
        # Check they are the same
        assert logger1 is logger2


@pytest.mark.asyncio
async def test_log_access(monkeypatch):
    """Test log_access function."""
    # Mock the logger
    mock_logger = MagicMock()
    monkeypatch.setattr(Logger, '_access_logger', mock_logger)
    
    # Call log_access
    log_access("Test message", client_ip="127.0.0.1", username="test_user")
    
    # Check that logger was called
    mock_logger.info.assert_called_once()


@pytest.mark.asyncio
async def test_log_security(monkeypatch):
    """Test log_security function."""
    # Mock the logger
    mock_logger = MagicMock()
    monkeypatch.setattr(Logger, '_security_logger', mock_logger)
    
    # Call log_security
    log_security("Test message", client_ip="127.0.0.1", username="test_user")
    
    # Check that logger was called
    mock_logger.info.assert_called_once()


@pytest.mark.asyncio
async def test_log_system(monkeypatch):
    """Test log_system function."""
    # Mock the logger
    mock_logger = MagicMock()
    monkeypatch.setattr(Logger, '_system_logger', mock_logger)
    
    # Call log_system
    log_system("Test message")
    
    # Check that logger was called
    mock_logger.info.assert_called_once()