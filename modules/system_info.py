import os
import platform
import sys
import psutil
from datetime import datetime
from typing import Dict, Any
from modules.config import config


def get_system_info() -> Dict[str, Any]:
    """
    Get detailed system information including hardware, OS, and process details.
    
    Returns:
        Dict: A dictionary containing system and process information
    """
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "system": {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "python_version": sys.version,
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(),
                "memory": {
                    "total": f"{memory.total / (1024 ** 3):.2f} GB",
                    "available": f"{memory.available / (1024 ** 3):.2f} GB",
                    "used_percent": memory.percent
                },
                "disk": {
                    "total": f"{disk.total / (1024 ** 3):.2f} GB",
                    "free": f"{disk.free / (1024 ** 3):.2f} GB",
                    "used_percent": disk.percent
                },
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
            },
            "process": {
                "pid": os.getpid(),
                "memory_usage": f"{psutil.Process(os.getpid()).memory_info().rss / (1024 ** 2):.2f} MB",
                "cpu_usage": f"{psutil.Process(os.getpid()).cpu_percent()}%",
                "threads": len(psutil.Process(os.getpid()).threads()),
                "start_time": datetime.fromtimestamp(psutil.Process(os.getpid()).create_time()).isoformat()
            }
        }
    except Exception as e:
        return {
            "error": f"Error collecting system info: {str(e)}"
        }


def get_app_info() -> Dict[str, Any]:
    """
    Get application information and configuration details.
    
    Returns:
        Dict: A dictionary containing application configuration information
    """
    server_config = config.get_server_config()
    redis_config = config.get_redis_config()
    cors_config = config.get_cors_config()
    
    return {
        "app": {
            "name": server_config.get('title', "darktheme-auth-fastapi-server"),
            "version": server_config.get('version', "v25.07.2024"),
            "description": server_config.get('description', "API server with authentication and authorization."),
            "host": server_config.get('host', "0.0.0.0"),
            "port": server_config.get('port', 8000),
            "api_prefix": config.get_api_prefix(),
            "redis_enabled": config.is_redis_enabled()
        },
        "config": {
            "redis": redis_config,
            "cors": {
                "origins": cors_config.get('origins', []),
                "allow_credentials": cors_config.get('allow_credentials', True)
            }
        }
    }