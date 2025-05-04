import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional, Union, List

from modules.config import config
from db.clientSQLite import AsyncSQLiteClient

class ContextFilter(logging.Filter):
    """
    A logging filter that adds context data to log records.
    This allows adding dynamic fields like client_ip and username to log messages.
    """
    def __init__(self, context: Dict[str, Any] = None):
        super().__init__()
        self.context = context or {}
        
    def filter(self, record):
        """Add context data to the log record."""
        for key, value in self.context.items():
            setattr(record, key, value)
        
        # Set default values for required fields if not present
        if not hasattr(record, 'client_ip'):
            setattr(record, 'client_ip', '-')
        if not hasattr(record, 'username'):
            setattr(record, 'username', '-')
        
        return True


class SQLiteHandler(logging.Handler):
    """
    Custom logging handler that stores log records in SQLite database.
    This handler works asynchronously with the AsyncSQLiteClient.
    """
    def __init__(self, log_type: str):
        super().__init__()
        self.log_type = log_type
        self.client = None
        
    async def setup(self):
        """Initialize the SQLite client"""
        if self.client is None:
            self.client = await AsyncSQLiteClient.get_instance()
            await self.client.setup()
    
    def emit(self, record):
        """
        Process the log record and queue it for database insertion.
        This method is called synchronously by the logging system.
        
        We use a lightweight approach here to avoid blocking:
        - Extract relevant data from the log record
        - Create a dict with the data
        - In the main event loop, we'll process this data asynchronously
        """
        # Format the timestamp consistently for database storage
        timestamp = datetime.fromtimestamp(record.created).isoformat()
        
        # Extract log record data based on log type
        if self.log_type == 'access':
            self._emit_access_log(record, timestamp)
        elif self.log_type == 'security':
            self._emit_security_log(record, timestamp)
        elif self.log_type == 'system':
            self._emit_system_log(record, timestamp)
    
    def _emit_access_log(self, record, timestamp):
        """Process access log record"""
        # Create a task to be run in the event loop
        import asyncio
        
        # Extract fields from record
        client_ip = getattr(record, 'client_ip', None)
        method = getattr(record, 'method', None)
        path = getattr(record, 'path', None)
        status_code = getattr(record, 'status_code', None)
        response_time = getattr(record, 'response_time', None)
        
        # Format the message
        message = self.format(record)
        
        # Create an async task to insert the log
        asyncio.create_task(self._async_insert_access_log(
            timestamp, record.levelname, client_ip, method, path, 
            status_code, response_time, message
        ))
    
    def _emit_security_log(self, record, timestamp):
        """Process security log record"""
        import asyncio
        
        # Extract fields from record
        client_ip = getattr(record, 'client_ip', None)
        username = getattr(record, 'username', None)
        action = getattr(record, 'action', None)
        success = getattr(record, 'success', None)
        
        # Format the message
        message = self.format(record)
        
        # Create an async task to insert the log
        asyncio.create_task(self._async_insert_security_log(
            timestamp, record.levelname, client_ip, username, 
            action, success, message
        ))
    
    def _emit_system_log(self, record, timestamp):
        """Process system log record"""
        import asyncio
        
        # Extract module and function information
        module = record.module
        function = record.funcName
        
        # Format the message
        message = self.format(record)
        
        # Create an async task to insert the log
        asyncio.create_task(self._async_insert_system_log(
            timestamp, record.levelname, module, function, message
        ))
    
    async def _async_insert_access_log(self, timestamp, level, client_ip, method, 
                                     path, status_code, response_time, message):
        """Async method to insert access log into database"""
        await self.setup()
        await self.client.insert_access_log(
            timestamp, level, client_ip, method, path, 
            status_code, response_time, message
        )
    
    async def _async_insert_security_log(self, timestamp, level, client_ip, 
                                       username, action, success, message):
        """Async method to insert security log into database"""
        await self.setup()
        await self.client.insert_security_log(
            timestamp, level, client_ip, username, action, success, message
        )
    
    async def _async_insert_system_log(self, timestamp, level, module, function, message):
        """Async method to insert system log into database"""
        await self.setup()
        await self.client.insert_system_log(
            timestamp, level, module, function, message
        )


class Logger:
    """
    Centralized logging system with support for different log types:
    - Access logs: Track successful user logins and API usage
    - Security logs: Track authentication attempts, failures, and security events
    - System logs: Track application errors, warnings, and general system events
    
    Logs are stored both in files and SQLite database.
    """
    # Singleton instance
    _instance = None
    
    # Logger instances
    _access_logger = None
    _security_logger = None
    _system_logger = None
    
    # SQLite handlers
    _sqlite_handlers = {}
    
    # Configuration
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._init_loggers()
        return cls._instance
    
    @classmethod
    def _init_loggers(cls):
        """Initialize all loggers based on configuration."""
        # Get logging configuration
        log_config = config.get_logging_config()
        
        # Create log directory if it doesn't exist
        log_dir = log_config.get('directory', './logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Initialize each logger if enabled
        access_config = log_config.get('access', {})
        if access_config.get('enabled', True):
            cls._access_logger = cls._create_logger(
                'access',
                access_config.get('level', 'INFO'),
                access_config.get('format', '[%(asctime)s] [%(levelname)s] [%(client_ip)s] [%(username)s] %(message)s'),
                log_config.get('max_records', 10000),
                log_config.get('use_sqlite', True)
            )
        
        security_config = log_config.get('security', {})
        if security_config.get('enabled', True):
            cls._security_logger = cls._create_logger(
                'security',
                security_config.get('level', 'INFO'),
                security_config.get('format', '[%(asctime)s] [%(levelname)s] [%(client_ip)s] [%(username)s] %(message)s'),
                log_config.get('max_records', 10000),
                log_config.get('use_sqlite', True)
            )
        
        system_config = log_config.get('system', {})
        if system_config.get('enabled', True):
            cls._system_logger = cls._create_logger(
                'system',
                system_config.get('level', 'INFO'),
                system_config.get('format', '[%(asctime)s] [%(levelname)s] [%(module)s] [%(funcName)s] %(message)s'),
                log_config.get('max_records', 10000),
                log_config.get('use_sqlite', True)
            )
    
    @classmethod
    def _create_logger(cls, name: str, level: str, format_str: str, 
                      max_records: int, use_sqlite: bool = True):
        """
        Create and configure a logger with the specified parameters.
        
        Args:
            name: Logger name
            level: Logging level
            format_str: Log format string
            max_records: Maximum number of records per log file
            use_sqlite: Whether to log to SQLite database
            
        Returns:
            Configured logger instance
        """
        # Create logger
        logger = logging.getLogger(f"app.{name}")
        
        # Set level
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        logger.setLevel(level_map.get(level.upper(), logging.INFO))
        
        # Set formatter
        formatter = logging.Formatter(format_str)
        
        # Add custom filter for context data
        context_filter = ContextFilter()
        
        # Add SQLite handler if enabled
        if use_sqlite:
            sqlite_handler = SQLiteHandler(name)
            sqlite_handler.setFormatter(formatter)
            sqlite_handler.addFilter(context_filter)
            logger.addHandler(sqlite_handler)
            cls._sqlite_handlers[name] = sqlite_handler
        
        # Configure independent mode (don't propagate to parent loggers)
        logger.propagate = False
        
        return logger
    
    @classmethod
    async def setup_sqlite_handlers(cls):
        """Initialize all SQLite handlers for async operation"""
        for handler in cls._sqlite_handlers.values():
            await handler.setup()
    
    @classmethod
    def _get_log_level_method(cls, logger, level: str):
        """Get the appropriate logging method for the given level."""
        if level.upper() == 'DEBUG':
            return logger.debug
        elif level.upper() == 'INFO':
            return logger.info
        elif level.upper() == 'WARNING':
            return logger.warning
        elif level.upper() == 'ERROR':
            return logger.error
        elif level.upper() == 'CRITICAL':
            return logger.critical
        else:
            return logger.info
    
    @classmethod
    def access_log(cls, message: str, level: str = 'INFO', 
                  client_ip: str = None, username: str = None, 
                  extra: Dict[str, Any] = None):
        """
        Log an access event.
        
        Args:
            message: The log message
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            client_ip: Client IP address
            username: Username that performed the action
            extra: Additional context data for the log record
        """
        if cls._access_logger is None:
            return
            
        # Create extra context with client_ip and username
        context = extra or {}
        if client_ip:
            context['client_ip'] = client_ip
        if username:
            context['username'] = username
        
        # Get appropriate logging method
        log_method = cls._get_log_level_method(cls._access_logger, level)
        
        # Log with context
        log_method(message, extra=context)
    
    @classmethod
    def security_log(cls, message: str, level: str = 'INFO', 
                    client_ip: str = None, username: str = None, 
                    extra: Dict[str, Any] = None):
        """
        Log a security event.
        
        Args:
            message: The log message
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            client_ip: Client IP address
            username: Username related to the security event
            extra: Additional context data for the log record
        """
        if cls._security_logger is None:
            return
            
        # Create extra context with client_ip and username
        context = extra or {}
        if client_ip:
            context['client_ip'] = client_ip
        if username:
            context['username'] = username
        
        # Get appropriate logging method
        log_method = cls._get_log_level_method(cls._security_logger, level)
        
        # Log with context
        log_method(message, extra=context)
    
    @classmethod
    def system_log(cls, message: str, level: str = 'INFO', 
                  extra: Dict[str, Any] = None):
        """
        Log a system event.
        
        Args:
            message: The log message
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            extra: Additional context data for the log record
        """
        if cls._system_logger is None:
            return
            
        # Get appropriate logging method
        log_method = cls._get_log_level_method(cls._system_logger, level)
        
        # Log with context
        log_method(message, extra=extra or {})


# Instantiate the logger
logger = Logger()

# Legacy functions for backward compatibility
def log_info(message: str):
    """Log an info message to the system log."""
    logger.system_log(message, 'INFO')

def log_warning(message: str):
    """Log a warning message to the system log."""
    logger.system_log(message, 'WARNING')

def log_error(message: str):
    """Log an error message to the system log."""
    logger.system_log(message, 'ERROR')


# New specialized logging functions
def log_access(message: str, client_ip: str = None, username: str = None, level: str = 'INFO'):
    """Log an access event."""
    logger.access_log(message, level, client_ip, username)

def log_security(message: str, client_ip: str = None, username: str = None, level: str = 'INFO'):
    """Log a security event."""
    logger.security_log(message, level, client_ip, username)

def log_system(message: str, level: str = 'INFO', extra: Dict[str, Any] = None):
    """Log a system event."""
    logger.system_log(message, level, extra)


# Async methods for log retrieval
async def get_logs(log_type: str, limit: int = 100, offset: int = 0, 
                  level: str = None, start_date: str = None, 
                  end_date: str = None, search: str = None) -> List[Dict[str, Any]]:
    """
    Retrieve logs from SQLite database with filtering options.
    
    Args:
        log_type: The type of logs to retrieve ('access', 'security', 'system')
        limit: Maximum number of logs to return
        offset: Number of logs to skip
        level: Filter by log level
        start_date: Filter logs after this date (format: YYYY-MM-DD)
        end_date: Filter logs before this date (format: YYYY-MM-DD)
        search: Search term to filter messages
        
    Returns:
        List of log entries
    """
    # Map log type to database table
    table_map = {
        'access': 'access_logs',
        'security': 'security_logs',
        'system': 'system_logs'
    }
    
    # Validate log type
    if log_type not in table_map:
        raise ValueError(f"Invalid log type. Must be one of: {', '.join(table_map.keys())}")
    
    # Initialize SQLite client
    sqlite_client = await AsyncSQLiteClient.get_instance()
    await sqlite_client.setup()
    
    # Query logs
    return await sqlite_client.query_logs(
        table_map[log_type],
        limit=limit,
        offset=offset,
        level=level,
        start_date=start_date,
        end_date=end_date,
        search=search
    )

async def get_log_counts() -> Dict[str, int]:
    """Get the count of logs in each table"""
    sqlite_client = await AsyncSQLiteClient.get_instance()
    await sqlite_client.setup()
    return await sqlite_client.get_log_counts()