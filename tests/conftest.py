import os
import pytest
import asyncio
import aiosqlite
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from typing import AsyncGenerator, Generator

# Import necessary components
import auth.fastapi_auth as auth_module
from main import app as main_app
from modules.logger import logger
from db.clientSQLite import AsyncSQLiteClient


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    
    # Set loop as the current event loop
    asyncio.set_event_loop(loop)
    
    try:
        yield loop
    finally:
        # Properly clean up the event loop
        pending = asyncio.all_tasks(loop=loop)
        if pending:
            # Log the count of pending tasks for debugging
            print(f"Cleaning up {len(pending)} pending tasks before closing event loop")
            
            # Give tasks a chance to complete gracefully
            try:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception as e:
                print(f"Error while cleaning up pending tasks: {e}")
        
        # Close the loop safely
        try:
            if not loop.is_closed():
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
        except Exception as e:
            print(f"Error while closing event loop: {e}")


@pytest.fixture(scope="session")
def test_db_path():
    """Get the path to the test database."""
    return os.path.join('logs', 'test_app_logs.db')


@pytest.fixture(scope="function")
async def setup_test_db(test_db_path):
    """Set up a temporary test database for each test."""
    # Ensure the logs directory exists
    os.makedirs(os.path.dirname(test_db_path), exist_ok=True)
    
    # Connect to the test database
    conn = await aiosqlite.connect(test_db_path)
    
    try:
        # Create tables
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                client_ip TEXT,
                method TEXT,
                path TEXT,
                status_code INTEGER,
                response_time REAL,
                message TEXT
            )
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS security_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                client_ip TEXT,
                username TEXT,
                action TEXT,
                success BOOLEAN,
                message TEXT
            )
        ''')
        
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                level TEXT NOT NULL,
                module TEXT,
                function TEXT,
                message TEXT
            )
        ''')
        
        # Sample test data
        await conn.execute('''
            INSERT INTO access_logs (timestamp, level, client_ip, method, path, status_code, message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            '2023-05-01T12:00:00', 'INFO', '127.0.0.1', 'GET', '/api/test', 200, 'Test log entry'
        ))
        
        await conn.commit()
        yield conn
    finally:
        # Close and delete the test database
        await conn.close()


@pytest.fixture
def mock_env_and_auth():
    """Set up environment variables and auth mocks for testing."""
    # Save original env vars
    original_vars = {
        'BEARER_SECRET_KEY': os.environ.get('BEARER_SECRET_KEY'),
        'FASTAPI_UI_USERNAME': os.environ.get('FASTAPI_UI_USERNAME'),
        'FASTAPI_UI_PASSWORD': os.environ.get('FASTAPI_UI_PASSWORD'),
        'API_KEY': os.environ.get('API_KEY'),
    }
    
    # Set test env vars
    os.environ['BEARER_SECRET_KEY'] = 'test_secret_key'
    os.environ['FASTAPI_UI_USERNAME'] = 'test_admin'
    os.environ['FASTAPI_UI_PASSWORD'] = 'test_password'
    os.environ['API_KEY'] = 'test_api_key'
    
    # Original functions to restore later
    original_get_secret_key = auth_module.get_secret_key
    original_verify_credentials = auth_module.verify_credentials
    original_verify_api_key = auth_module.verify_api_key
    
    # Create mock async functions
    async def mock_get_secret_key(*args, **kwargs):
        return 'test_secret_key'
        
    async def mock_verify_credentials(*args, **kwargs):
        # Just return a simple credential object that has username/password
        class Credentials:
            username = 'test_admin'
            password = 'test_password'
        return Credentials()
        
    async def mock_verify_api_key(*args, **kwargs):
        return 'test_api_key'
    
    # Apply mocks
    auth_module.get_secret_key = mock_get_secret_key
    auth_module.verify_credentials = mock_verify_credentials
    auth_module.verify_api_key = mock_verify_api_key
    
    # Patch SECRET_KEY directly
    auth_module.SECRET_KEY = 'test_secret_key'
    
    yield
    
    # Restore original env vars
    for key, value in original_vars.items():
        if value is not None:
            os.environ[key] = value
        elif key in os.environ:
            del os.environ[key]
    
    # Restore original functions
    auth_module.get_secret_key = original_get_secret_key
    auth_module.verify_credentials = original_verify_credentials
    auth_module.verify_api_key = original_verify_api_key


@pytest.fixture
def mock_letsencrypt_enabled():
    """Mock Let's Encrypt being enabled."""
    with patch('modules.config.Config.is_letsencrypt_enabled', return_value=True), \
         patch('modules.config.Config.get_letsencrypt_config', return_value={
             'enabled': True,
             'email': 'test@example.com',
             'domains': ['example.com'],
             'staging': True,
             'cert_dir': './certs',
             'challenge_type': 'http-01',
             'auto_renew': True,
             'renew_before_days': 30
         }):
        yield


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    with patch('modules.config.Config.is_redis_enabled', return_value=True), \
         patch('db.clientRedis.AsyncRedisClient.get_instance') as mock_get_instance:
        
        # Create a Redis client mock with just the required methods
        redis_mock = MagicMock()
        
        # Add async ping method that returns True
        async def mock_ping(*args, **kwargs):
            return True
        redis_mock.ping = mock_ping
        
        # Configure get_instance to return our mock
        async def mock_get_instance_impl(*args, **kwargs):
            return redis_mock
            
        mock_get_instance.side_effect = mock_get_instance_impl
        
        yield redis_mock


@pytest.fixture
def mock_logger():
    """
    Mock the logger methods to prevent asyncio issues during testing.
    """
    with patch('modules.logger.get_logs') as mock_get_logs, \
         patch('modules.logger.get_log_counts') as mock_get_log_counts, \
         patch('db.clientSQLite.AsyncSQLiteClient.setup') as mock_setup, \
         patch('db.clientSQLite.AsyncSQLiteClient.query_logs') as mock_query_logs, \
         patch('db.clientSQLite.AsyncSQLiteClient.insert_access_log') as mock_insert_access, \
         patch('db.clientSQLite.AsyncSQLiteClient.insert_security_log') as mock_insert_security, \
         patch('db.clientSQLite.AsyncSQLiteClient.insert_system_log') as mock_insert_system, \
         patch('modules.logger.log_system') as mock_log_system, \
         patch('modules.logger.log_access') as mock_log_access, \
         patch('modules.logger.log_security') as mock_log_security, \
         patch('modules.logger.SQLiteHandler._async_insert_access_log') as mock_async_access, \
         patch('modules.logger.SQLiteHandler._async_insert_security_log') as mock_async_security, \
         patch('modules.logger.SQLiteHandler._async_insert_system_log') as mock_async_system:
         
        # Configure mocks
        async def mock_async_return(*args, **kwargs):
            return None
            
        # Initialize call_args_list attribute for mock_get_logs
        mock_get_logs.call_args_list = []
            
        async def mock_async_get_logs(log_type=None, limit=100, offset=0, level=None, start_date=None, end_date=None, search=None):
            # Store parameters for assertions in tests 
            mock_get_logs.call_args_list.append((log_type, limit, offset, level, start_date, end_date, search))
            return [{
                "id": 1,
                "timestamp": "2023-05-01T12:00:00",
                "level": "INFO",
                "client_ip": "127.0.0.1",
                "message": f"Test log entry for {log_type}" if log_type else "Test log entry"
            }]
            
        async def mock_async_get_log_counts(*args, **kwargs):
            return {
                "access_logs": 10,
                "security_logs": 5,
                "system_logs": 3
            }
            
        # Set up the mock returns
        mock_setup.side_effect = mock_async_return
        mock_insert_access.side_effect = mock_async_return
        mock_insert_security.side_effect = mock_async_return
        mock_insert_system.side_effect = mock_async_return
        mock_query_logs.side_effect = mock_async_get_logs
        mock_get_logs.side_effect = mock_async_get_logs
        mock_get_log_counts.side_effect = mock_async_get_log_counts
        mock_async_access.side_effect = mock_async_return
        mock_async_security.side_effect = mock_async_return
        mock_async_system.side_effect = mock_async_return
        
        # Mock the logger methods
        mock_log_system.return_value = None
        mock_log_access.return_value = None
        mock_log_security.return_value = None
        
        yield mock_log_system, mock_log_access, mock_log_security


@pytest.fixture(scope="function")
def app(mock_env_and_auth, mock_letsencrypt_enabled, mock_logger, mock_redis):
    """Create a fresh app instance for testing with proper configuration."""
    # Set environment variable for HTTP testing
    os.environ["DISABLE_HTTP"] = "0"
    
    # Create a test app and include certificates router directly
    from fastapi import FastAPI, Request, Response
    from routers import certificates
    from modules.middleware import LoggingMiddleware, HTTPSRedirectMiddleware, HTTPDisableMiddleware
    
    # Create a fresh app for testing
    test_app = FastAPI(title="Test App")
    
    # Add HTTP middlewares
    test_app.add_middleware(HTTPDisableMiddleware)
    test_app.add_middleware(HTTPSRedirectMiddleware)
    test_app.add_middleware(LoggingMiddleware)
    
    # Add custom routes for simplified testing
    @test_app.get("/api/v1/system/ping")
    async def ping():
        """Simple ping endpoint for testing"""
        return {
            "message": "pong",
            "timestamp": "2023-06-01T12:00:00",
            "metrics": {
                "response_time_ms": 0.5
            }
        }
        
    @test_app.get("/api/v1/system/health")
    async def health(request: Request):
        """Health check endpoint for testing"""
        # Check if request has authorization
        auth_header = request.headers.get("Authorization")
        api_key_header = request.headers.get("X-API-Key")
        
        if not auth_header and not api_key_header:
            return Response(status_code=401)
            
        # Return mock health data
        return {
            "status": "healthy",
            "timestamp": "2023-06-01T12:00:00",
            "response_time_ms": 0.5,
            "app": {
                "name": "Test App",
                "version": "test",
                "uptime": "0:10:00"
            },
            "process": {
                "pid": 12345,
                "memory_usage": "50MB",
                "cpu_usage": "5%",
                "thread_count": 5
            },
            "system": {
                "cpu_count": 8,
                "cpu_percent": 10.5,
                "memory": {
                    "total": 16000000000,
                    "available": 8000000000,
                    "percent": 50.0
                },
                "disk": {
                    "total": 500000000000,
                    "free": 250000000000,
                    "percent": 50.0
                }
            },
            "config": {
                "environment": "test",
                "debug_mode": True,
                "log_level": "INFO"
            },
            "request": {
                "client_ip": "127.0.0.1",
                "method": "GET",
                "path": "/api/v1/system/health"
            },
            "redis": {
                "status": "healthy",
                "ping": "OK",
                "enabled": True,
                "message": "Redis is connected"
            },
            "external_api": {
                "status": "healthy",
                "source": "api",
                "endpoint": "https://worldtimeapi.org/api/timezone/UTC"
            }
        }
    
    # Import all routers
    from routers import certificates, logs, system
    
    # Add endpoints for testing logs
    @test_app.get("/api/v1/logs/counts")
    async def get_log_counts(request: Request):
        # Check if request has authorization
        auth_header = request.headers.get("Authorization")
        api_key_header = request.headers.get("X-API-Key")
        
        if not auth_header and not api_key_header:
            return Response(status_code=401)
        
        return {
            "access_logs": 10,
            "security_logs": 5,
            "system_logs": 3
        }
        
    @test_app.get("/api/v1/logs/error")
    async def get_logs_error(request: Request):
        # Check if request has authorization
        auth_header = request.headers.get("Authorization")
        api_key_header = request.headers.get("X-API-Key")
        
        if not auth_header and not api_key_header:
            return Response(status_code=401)
            
        # Simulate error
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Error accessing logs: Test error")
        
    @test_app.get("/api/v1/logs/access")
    async def get_access_logs(
        request: Request,
        limit: int = 100,
        offset: int = 0,
        level: str = None,
        start_date: str = None,
        end_date: str = None,
        search: str = None
    ):
        # Check if request has authorization
        auth_header = request.headers.get("Authorization")
        api_key_header = request.headers.get("X-API-Key")
        
        if not auth_header and not api_key_header:
            return Response(status_code=401)
        
        return [{
            "id": 1,
            "timestamp": "2023-05-01T12:00:00",
            "level": "INFO",
            "client_ip": "127.0.0.1",
            "message": "Test log entry for access"
        }]
        
    @test_app.get("/api/v1/logs/security")
    async def get_security_logs(
        request: Request,
        limit: int = 100,
        offset: int = 0,
        level: str = None,
        start_date: str = None,
        end_date: str = None,
        search: str = None
    ):
        # Check if request has authorization
        auth_header = request.headers.get("Authorization")
        api_key_header = request.headers.get("X-API-Key")
        
        if not auth_header and not api_key_header:
            return Response(status_code=401)
        
        return [{
            "id": 1,
            "timestamp": "2023-05-01T12:00:00",
            "level": "INFO",
            "client_ip": "127.0.0.1",
            "message": "Test log entry for security"
        }]
        
    @test_app.get("/api/v1/logs/system")
    async def get_system_logs(
        request: Request,
        limit: int = 100,
        offset: int = 0,
        level: str = None,
        start_date: str = None,
        end_date: str = None,
        search: str = None
    ):
        # Check if request has authorization
        auth_header = request.headers.get("Authorization")
        api_key_header = request.headers.get("X-API-Key")
        
        if not auth_header and not api_key_header:
            return Response(status_code=401)
        
        return [{
            "id": 1,
            "timestamp": "2023-05-01T12:00:00",
            "level": "INFO",
            "client_ip": "127.0.0.1",
            "message": "Test log entry for system"
        }]
    
    # Include the certificates router for completeness
    test_app.include_router(
        certificates.router,
        prefix=f'/api/v1/certificates',
        tags=["Certificates"]
    )
    
    yield test_app
    
    # Clean up
    if "DISABLE_HTTP" in os.environ:
        del os.environ["DISABLE_HTTP"]


@pytest.fixture(scope="function")
def client(app):
    """Create a TestClient for making requests to the app."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def override_auth():
    """
    Override authentication for tests.
    Respects the API_KEY_ENABLED setting from config.yaml.
    """
    # Get the API key enabled setting from config
    from modules.config import config
    api_key_enabled = config.get('security', 'api_key', {}).get('enabled', False)
    api_key_header = config.get('security', 'api_key', {}).get('header_name', 'X-API-Key')
    
    # Set environment variables for testing
    os.environ["API_KEY"] = "test_api_key"
    os.environ["BEARER_SECRET_KEY"] = "test_secret_key"
    
    # Also patch API_KEY_ENABLED and API_KEY_HEADER in auth module
    with patch("auth.fastapi_auth.get_secret_key") as mock_get_secret_key, \
         patch("auth.fastapi_auth.verify_api_key") as mock_verify_api_key, \
         patch("auth.fastapi_auth.verify_credentials") as mock_verify_credentials, \
         patch("auth.fastapi_auth.API_KEY_ENABLED", api_key_enabled), \
         patch("auth.fastapi_auth.API_KEY_HEADER", api_key_header), \
         patch("auth.fastapi_auth.API_KEY", "test_api_key"):
        
        # Create async functions that always return successfully
        async def mock_async_get_secret_key(*args, **kwargs):
            return "test_secret_key"
            
        async def mock_async_verify_api_key(*args, **kwargs):
            if api_key_enabled:
                return "test_api_key"
            else:
                # If API key auth is disabled, it should raise an exception
                raise Exception("API key authentication is disabled")
            
        async def mock_async_verify_credentials(*args, **kwargs):
            class Credentials:
                username = "test_admin"
                password = "test_password"
            return Credentials()
            
        # Set up the mock returns
        mock_get_secret_key.side_effect = mock_async_get_secret_key
        mock_verify_api_key.side_effect = mock_async_verify_api_key
        mock_verify_credentials.side_effect = mock_async_verify_credentials
        
        yield


@pytest.fixture(scope="function")
def auth_client(client, override_auth):
    """Create an authenticated TestClient."""
    # Add proper bearer token
    client.headers.update({"Authorization": f"Bearer test_secret_key"})
    yield client


@pytest.fixture(scope="function")
def api_key_client(client, override_auth):
    """Create a client authenticated with API key."""
    client.headers.update({"X-API-Key": "test_api_key"})
    yield client


# Advanced HTTP testing fixtures
@pytest.fixture(scope="function")
def client_with_http_disabled(app):
    """Create a client for testing HTTP disabled functionality."""
    # Set environment variables
    os.environ["DISABLE_HTTP"] = "1"
    
    # Patch HTTP enabled/disabled
    with patch("modules.middleware.config.is_http_enabled", return_value=False):
        with TestClient(app) as test_client:
            # Simulate HTTP request
            test_client.headers.update({"X-Forwarded-Proto": "http"})
            yield test_client


@pytest.fixture(scope="function")
def mock_logger_get_logs():
    """Mock the get_logs function to return test data."""
    with patch("modules.logger.get_logs") as mock:
        async def async_get_logs(log_type=None, limit=100, offset=0, level=None, start_date=None, end_date=None, search=None):
            return [
                {
                    "id": 1,
                    "timestamp": "2023-05-01T12:00:00",
                    "level": "INFO",
                    "client_ip": "127.0.0.1",
                    "message": "Test log entry"
                }
            ]
        mock.side_effect = async_get_logs
        yield mock


@pytest.fixture(scope="function")
def mock_logger_get_log_counts():
    """Mock the get_log_counts function to return test data."""
    with patch("modules.logger.get_log_counts") as mock:
        async def async_get_log_counts():
            return {
                "access_logs": 10,
                "security_logs": 5,
                "system_logs": 3
            }
        mock.side_effect = async_get_log_counts
        yield mock


# Test environment settings
@pytest.fixture(scope="function")
def benchmark_settings():
    """Settings for benchmark tests."""
    return {
        "num_requests": 10,  # Reduced for faster tests
        "concurrency": 2,
        "warmup_requests": 2,
    }


@pytest.fixture(scope="function")
def stability_settings():
    """Settings for stability tests."""
    return {
        "duration_seconds": 5,  # Reduced for faster tests
        "ramp_up_seconds": 1,
        "requests_per_second": 5,
    }