from fastapi import APIRouter, Depends, Request
import time
import asyncio
from datetime import datetime
from auth.fastapi_auth import get_secret_key, get_client_ip
from modules.cache_handler import (
    CacheHandler,
    fetch_and_cache_time
)
from modules.system_info import get_system_info, get_app_info
from modules.logger import log_access, log_system

router = APIRouter()


@router.get("/ping")
async def ping(request: Request = None):
    """
    Simple ping endpoint that returns 'pong' and response time metrics
    """
    start_time = time.time()
    process_time = time.process_time()
    
    # Simulate minimal processing to measure accurate response time
    await asyncio.sleep(0.001)
    
    end_time = time.time()
    end_process_time = time.process_time()
    
    # Get client IP for logging
    client_ip = await get_client_ip(request) if request else "unknown"
    
    # Log ping request
    log_access(
        "Ping request received",
        client_ip=client_ip,
        level="DEBUG"
    )
    
    response_time = round((end_time - start_time) * 1000, 2)
    
    # Log slow response if over 100ms
    if response_time > 100:
        log_system(
            f"Slow ping response: {response_time} ms",
            level="WARNING"
        )
    
    return {
        "message": "pong",
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": {
            "response_time_ms": response_time,
            "process_time_ms": round((end_process_time - process_time) * 1000, 2),
            "server_time": datetime.now().isoformat()
        }
    }


@router.get("/health", dependencies=[Depends(get_secret_key)])
async def health_check(request: Request, redis = Depends(CacheHandler.get_redis_client)):
    """
    Comprehensive health check endpoint that provides details about:
    - Application status and configuration
    - System information (CPU, memory, disk)
    - Redis status
    - External API connectivity
    """
    start_time = time.time()
    cache_key = "current_utc_time"
    expire_seconds = 60  # Example expiration time
    time_api = "https://worldtimeapi.org/api/timezone/etc/utc"  # Example URL to get UTC time

    # Get client IP for logging
    client_ip = await get_client_ip(request) if request else "unknown"
    
    # Log health check request
    log_access(
        "Health check request",
        client_ip=client_ip,
        level="INFO"
    )
    
    try:
        # Check external API
        time_info = await fetch_and_cache_time(cache_key, time_api, expire_seconds, redis)
        
        # Check Redis health
        redis_health = await CacheHandler.check_health(redis)
        
        # Get system info
        system_info = get_system_info()
        
        # Get app info
        app_info = get_app_info()
        
        # Check current request
        request_info = {
            "client": client_ip,
            "method": request.method,
            "url": str(request.url),
            "time": datetime.now().isoformat()
        }
        
        # Calculate response time
        end_time = time.time()
        response_time = round((end_time - start_time) * 1000, 2)
        
        # Log any issues found
        if redis_health.get("status") != "healthy" and redis_health.get("status") != "disabled":
            log_system(
                f"Redis health check failed: {redis_health.get('message')}",
                level="WARNING"
            )
            
        # Safely check for fallback flag in time_info response
        if "data" in time_info and time_info["data"].get("fallback", False):
            log_system(
                f"External API health check failed - using fallback data",
                level="WARNING"
            )
        
        # Log slow response time
        if response_time > 500:  # More than 500ms
            log_system(
                f"Slow health check response: {response_time} ms",
                level="WARNING"
            )
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "response_time_ms": response_time,
            "request": request_info,
            "redis": redis_health,
            "external_api": {
                "status": "healthy" if not ("data" in time_info and time_info["data"].get("fallback", False)) else "error",
                "source": time_info.get("source", "unknown"),
                "cache_ttl": time_info.get("time_left", 0),
                "endpoint": time_api
            },
            **app_info,
            **system_info
        }
    except Exception as e:
        # Log any errors
        log_system(
            f"Error in health check: {str(e)}",
            level="ERROR"
        )
        raise