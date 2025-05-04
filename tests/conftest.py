import os
import pytest
import asyncio
import aiosqlite
from fastapi.testclient import TestClient
from fastapi import FastAPI
from typing import AsyncGenerator, Generator

from main import app as main_app
from modules.logger import logger, get_logs, get_log_counts
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


# This fixture is not used in the updated tests, but kept for reference
@pytest.fixture(scope="function")
async def setup_test_db(test_db_path):
    """Set up a test database (no longer used)."""
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
        
        await conn.commit()
        yield conn
    finally:
        # Close the database connection
        await conn.close()


@pytest.fixture(scope="function")
def app() -> FastAPI:
    """Create a fresh app instance for testing."""
    from main import app as main_app
    return main_app


@pytest.fixture(scope="function")
def client(app) -> Generator:
    """Create a TestClient for making requests to the app."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def auth_client(client) -> Generator:
    """Create an authenticated TestClient."""
    client.headers = {
        "Authorization": "Bearer AbCdEfGhIjKlMnOpQrStUvWxYz",
        **client.headers
    }
    return client


# For benchmark and stability tests
@pytest.fixture(scope="function")
def benchmark_settings():
    """Settings for benchmark tests."""
    return {
        "num_requests": 1000,
        "concurrency": 10,
        "warmup_requests": 50,
    }


@pytest.fixture(scope="function")
def stability_settings():
    """Settings for stability tests."""
    return {
        "duration_seconds": 60,
        "ramp_up_seconds": 5,
        "requests_per_second": 50,
    }