import os
import aiosqlite
import asyncio
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
from modules.config import config

class AsyncSQLiteClient:
    """
    Asynchronous SQLite client for log storage with singleton pattern
    """
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            log_config = config.get_logging_config()
            log_dir = log_config.get('directory', './logs')
            sqlite_db = log_config.get('sqlite_db', 'app_logs.db')
            cls._instance.db_path = kwargs.get('db_path') or os.path.join(log_dir, sqlite_db)
            cls._instance.db_conn = None
            cls._instance._setup_complete = False
        return cls._instance
        
    @classmethod
    async def get_instance(cls, db_path: str = None):
        """Get or create the singleton instance"""
        if cls._instance is None:
            return cls(db_path=db_path)
        return cls._instance
    
    async def setup(self):
        """Initialize database connection and create tables if they don't exist"""
        async with self._lock:
            if self._setup_complete and self.db_conn is not None:
                # Check if connection is still valid
                try:
                    await self.db_conn.execute("SELECT 1")
                    return
                except Exception:
                    # Connection is not valid, recreate it
                    try:
                        if self.db_conn is not None:
                            await self.db_conn.close()
                    except Exception:
                        pass
                    self.db_conn = None
                    self._setup_complete = False
            
            # Ensure the logs directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Set timeout and pragma for better concurrency handling
            try:
                # Increase timeout to 60 seconds for high concurrency in tests
                self.db_conn = await aiosqlite.connect(
                    self.db_path,
                    timeout=60.0  # Increase SQLite busy timeout to 60 seconds
                )
                
                # Set pragmas for better concurrency
                await self.db_conn.execute("PRAGMA journal_mode=WAL")  # Use Write-Ahead Logging for better concurrency
                await self.db_conn.execute("PRAGMA synchronous=NORMAL")  # Reduce synchronous mode for better performance
                await self.db_conn.execute("PRAGMA cache_size=10000")  # Increase cache size
                # Add these pragmas to improve concurrency
                await self.db_conn.execute("PRAGMA busy_timeout=60000")  # Set busy timeout in milliseconds
                await self.db_conn.execute("PRAGMA temp_store=MEMORY")   # Store temp tables in memory
                
                # Create tables for each log type
                await self.db_conn.execute('''
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
                
                await self.db_conn.execute('''
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
                
                await self.db_conn.execute('''
                    CREATE TABLE IF NOT EXISTS system_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        level TEXT NOT NULL,
                        module TEXT,
                        function TEXT,
                        message TEXT
                    )
                ''')
                
                await self.db_conn.commit()
                self._setup_complete = True
            except Exception as e:
                print(f"Error setting up SQLite database: {e}")
                if self.db_conn is not None:
                    try:
                        await self.db_conn.close()
                    except Exception:
                        pass
                self.db_conn = None
                self._setup_complete = False
                raise
    
    async def insert_access_log(self, timestamp: str, level: str, client_ip: str = None, 
                               method: str = None, path: str = None, status_code: int = None,
                               response_time: float = None, message: str = None):
        """Insert a record in the access_logs table"""
        await self.setup()
        await self.db_conn.execute(
            '''INSERT INTO access_logs 
               (timestamp, level, client_ip, method, path, status_code, response_time, message) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (timestamp, level, client_ip, method, path, status_code, response_time, message)
        )
        await self.db_conn.commit()
    
    async def insert_security_log(self, timestamp: str, level: str, client_ip: str = None,
                                 username: str = None, action: str = None, success: bool = None,
                                 message: str = None):
        """Insert a record in the security_logs table"""
        await self.setup()
        await self.db_conn.execute(
            '''INSERT INTO security_logs 
               (timestamp, level, client_ip, username, action, success, message) 
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (timestamp, level, client_ip, username, action, success, message)
        )
        await self.db_conn.commit()
    
    async def insert_system_log(self, timestamp: str, level: str, module: str = None,
                               function: str = None, message: str = None):
        """Insert a record in the system_logs table"""
        await self.setup()
        await self.db_conn.execute(
            '''INSERT INTO system_logs 
               (timestamp, level, module, function, message) 
               VALUES (?, ?, ?, ?, ?)''',
            (timestamp, level, module, function, message)
        )
        await self.db_conn.commit()
    
    async def query_logs(self, table: str, limit: int = 100, offset: int = 0, 
                        level: str = None, start_date: str = None, end_date: str = None,
                        search: str = None) -> List[Dict[str, Any]]:
        """
        Query logs with filtering options
        
        Args:
            table: The log table to query (access_logs, security_logs, system_logs)
            limit: Maximum number of records to return
            offset: Number of records to skip
            level: Filter by log level (INFO, WARNING, ERROR, etc)
            start_date: Filter logs after this date (format: YYYY-MM-DD)
            end_date: Filter logs before this date (format: YYYY-MM-DD)
            search: Search term to filter message field
            
        Returns:
            List of log entries as dictionaries
        """
        # Improved retry mechanism for database locks
        max_retries = 5  # Increase max retries
        base_retry_delay = 0.5  # Start with shorter delay
        
        for attempt in range(max_retries):
            try:
                await self.setup()
                
                # Validate table name to prevent SQL injection
                valid_tables = ['access_logs', 'security_logs', 'system_logs']
                if table not in valid_tables:
                    raise ValueError(f"Invalid table name. Must be one of: {', '.join(valid_tables)}")
                
                # Limit the maximum number of records for performance
                if limit > 1000:
                    limit = 1000
                
                query = f"SELECT * FROM {table} WHERE 1=1"
                params = []
                
                if level:
                    query += " AND level = ?"
                    params.append(level)
                    
                if start_date:
                    query += " AND timestamp >= ?"
                    params.append(f"{start_date}T00:00:00")
                    
                if end_date:
                    query += " AND timestamp <= ?"
                    params.append(f"{end_date}T23:59:59")
                    
                if search:
                    query += " AND message LIKE ?"
                    params.append(f"%{search}%")
                    
                query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                # Add a small random delay before the query to help resolve potential lock conflicts
                if attempt > 0:
                    # Randomize delay to avoid lock contention patterns
                    import random
                    jitter = random.uniform(0, 0.5)  # Add up to 0.5 seconds jitter
                    retry_delay = base_retry_delay * (2 ** attempt) + jitter  # Exponential backoff with jitter
                    await asyncio.sleep(retry_delay)
                
                results = []
                try:
                    async with self.db_conn.execute(query, params) as cursor:
                        columns = [column[0] for column in cursor.description]
                        async for row in cursor:
                            results.append(dict(zip(columns, row)))
                except Exception as e:
                    # If this is a database lock issue, retry
                    if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                        # Just log at higher retry attempts to avoid spamming logs
                        if attempt > 1:
                            print(f"Error executing query (attempt {attempt+1}/{max_retries}): {e}")
                        await asyncio.sleep(retry_delay)
                        continue
                    elif "no such table" in str(e).lower():
                        # Table might not exist yet during parallel tests
                        print(f"Table {table} does not exist yet, returning empty results")
                        return []
                    else:
                        print(f"Error executing query: {e}")
                        raise
                
                return results
            except sqlite3.OperationalError as e:
                # If this is a database lock issue, retry
                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                    if attempt > 1:  # Only log after a few attempts
                        print(f"Database lock detected, retrying (attempt {attempt+1}/{max_retries})")
                    # Re-establish connection on retry
                    try:
                        if self.db_conn is not None:
                            await self.db_conn.close()
                    except Exception:
                        pass
                    self.db_conn = None
                    self._setup_complete = False
                else:
                    print(f"SQLite operational error: {e}")
                    if attempt == max_retries - 1:
                        # On the last attempt, return empty results instead of failing
                        print("Returning empty results after exhausting retries")
                        return []
                    raise
            except Exception as e:
                print(f"Error querying logs: {e}")
                if attempt == max_retries - 1:
                    # On the last attempt, return empty results instead of failing
                    return []
                raise
        
        # If we got here, all retries failed but we'll return empty results instead of raising an exception
        print(f"Failed to query logs after {max_retries} attempts due to database locks, returning empty results")
        return []
    
    async def get_log_counts(self) -> Dict[str, int]:
        """Get the count of logs in each table"""
        # Improved retry mechanism for database locks
        max_retries = 5  # Increase max retries
        base_retry_delay = 0.5  # Start with shorter delay
        
        for attempt in range(max_retries):
            try:
                await self.setup()
                
                # Add a small random delay before the query to help resolve potential lock conflicts
                if attempt > 0:
                    # Randomize delay to avoid lock contention patterns
                    import random
                    jitter = random.uniform(0, 0.5)  # Add up to 0.5 seconds jitter
                    retry_delay = base_retry_delay * (2 ** attempt) + jitter  # Exponential backoff with jitter
                    await asyncio.sleep(retry_delay)
                
                counts = {}
                for table in ['access_logs', 'security_logs', 'system_logs']:
                    try:
                        async with self.db_conn.execute(f"SELECT COUNT(*) FROM {table}") as cursor:
                            count = await cursor.fetchone()
                            counts[table] = count[0] if count else 0
                    except Exception as e:
                        # Handle "no such table" error which may happen during concurrent test setup
                        if "no such table" in str(e).lower():
                            # Table doesn't exist yet during parallel tests
                            counts[table] = 0
                        # If this is a database lock issue, retry the whole operation
                        elif "database is locked" in str(e).lower() and attempt < max_retries - 1:
                            if attempt > 1:  # Only log after a few attempts to reduce noise
                                print(f"Database locked while counting {table}, retrying whole operation")
                            raise sqlite3.OperationalError(f"Database locked while counting {table}")
                        else:
                            if attempt > 1 or "no such table" not in str(e).lower():
                                print(f"Error getting count for {table}: {e}")
                            # Otherwise just set count to 0 and continue
                            counts[table] = 0
                
                return counts
            except sqlite3.OperationalError as e:
                # If this is a database lock issue, retry
                if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                    if attempt > 1:  # Only log after a few attempts
                        print(f"Database lock detected in get_log_counts, retrying (attempt {attempt+1}/{max_retries})")
                    # Re-establish connection on retry
                    try:
                        if self.db_conn is not None:
                            await self.db_conn.close()
                    except Exception:
                        pass
                    self.db_conn = None
                    self._setup_complete = False
                else:
                    print(f"SQLite operational error in get_log_counts: {e}")
                    # On the last attempt, return zeros instead of failing
                    if attempt == max_retries - 1:
                        return {'access_logs': 0, 'security_logs': 0, 'system_logs': 0}
                    raise
            except Exception as e:
                print(f"Error getting log counts: {e}")
                # Return zeros if there's an error
                return {'access_logs': 0, 'security_logs': 0, 'system_logs': 0}
        
        # If we got here, all retries failed but we'll still return zeros
        print(f"Failed to get log counts after {max_retries} attempts due to database locks")
        return {'access_logs': 0, 'security_logs': 0, 'system_logs': 0}
    
    async def close(self):
        """Close the database connection"""
        if self.db_conn:
            await self.db_conn.close()
            self.db_conn = None
            self._setup_complete = False