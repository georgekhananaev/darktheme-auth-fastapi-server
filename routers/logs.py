from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Dict, List, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field
from auth.fastapi_auth import get_secret_key, get_client_ip
from modules.logger import get_logs, get_log_counts, log_access

router = APIRouter(prefix="/logs", tags=["Logs"])

class LogEntry(BaseModel):
    """Model for log entry returned by API"""
    id: int = Field(..., description="Unique ID of the log entry")
    timestamp: str = Field(..., description="Timestamp when the log was created")
    level: str = Field(..., description="Log level (INFO, WARNING, ERROR, etc.)")
    message: str = Field(..., description="Log message content")
    
    # Fields that may be present in some log types
    client_ip: Optional[str] = Field(None, description="Client IP address")
    username: Optional[str] = Field(None, description="Username related to the log")
    method: Optional[str] = Field(None, description="HTTP method (for access logs)")
    path: Optional[str] = Field(None, description="Request path (for access logs)")
    status_code: Optional[int] = Field(None, description="HTTP status code (for access logs)")
    response_time: Optional[float] = Field(None, description="Response time in ms (for access logs)")
    action: Optional[str] = Field(None, description="Security action (for security logs)")
    success: Optional[bool] = Field(None, description="Whether action was successful (for security logs)")
    module: Optional[str] = Field(None, description="Module name (for system logs)")
    function: Optional[str] = Field(None, description="Function name (for system logs)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "timestamp": "2023-05-04T12:34:56",
                "level": "INFO",
                "message": "User login successful",
                "client_ip": "192.168.1.1",
                "username": "admin",
                "method": "POST",
                "path": "/auth/login",
                "status_code": 200,
                "response_time": 45.2
            }
        }
    }

class LogCountResponse(BaseModel):
    """Model for log count response"""
    access_logs: int = Field(..., description="Number of access log entries")
    security_logs: int = Field(..., description="Number of security log entries")
    system_logs: int = Field(..., description="Number of system log entries")
    total: int = Field(..., description="Total number of log entries")

@router.get("/counts", response_model=LogCountResponse)
async def get_log_count_endpoint(
    client_ip: str = Depends(get_client_ip),
    _: Dict = Depends(get_secret_key)
) -> Dict:
    """
    Get counts of logs in all tables
    """
    log_access("Retrieving log counts", client_ip=client_ip)
    
    counts = await get_log_counts()
    counts["total"] = sum(counts.values())
    
    return counts

@router.get("/access", response_model=List[LogEntry])
async def get_access_logs(
    limit: int = Query(100, description="Maximum number of logs to return", ge=1, le=1000),
    offset: int = Query(0, description="Number of logs to skip", ge=0),
    level: Optional[str] = Query(None, description="Filter by log level (INFO, WARNING, ERROR, etc.)"),
    start_date: Optional[str] = Query(None, description="Filter logs after this date (format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter logs before this date (format: YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search term to filter messages"),
    client_ip: str = Depends(get_client_ip),
    _: Dict = Depends(get_secret_key)
) -> List[Dict]:
    """
    Get access logs with filtering options
    """
    log_access(f"Retrieving access logs (limit={limit}, offset={offset})", client_ip=client_ip)
    
    try:
        return await get_logs(
            log_type="access",
            limit=limit,
            offset=offset,
            level=level,
            start_date=start_date,
            end_date=end_date,
            search=search
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving logs: {str(e)}")

@router.get("/security", response_model=List[LogEntry])
async def get_security_logs(
    limit: int = Query(100, description="Maximum number of logs to return", ge=1, le=1000),
    offset: int = Query(0, description="Number of logs to skip", ge=0),
    level: Optional[str] = Query(None, description="Filter by log level (INFO, WARNING, ERROR, etc.)"),
    start_date: Optional[str] = Query(None, description="Filter logs after this date (format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter logs before this date (format: YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search term to filter messages"),
    client_ip: str = Depends(get_client_ip),
    _: Dict = Depends(get_secret_key)
) -> List[Dict]:
    """
    Get security logs with filtering options
    """
    log_access(f"Retrieving security logs (limit={limit}, offset={offset})", client_ip=client_ip)
    
    try:
        return await get_logs(
            log_type="security",
            limit=limit,
            offset=offset,
            level=level,
            start_date=start_date,
            end_date=end_date,
            search=search
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving logs: {str(e)}")

@router.get("/system", response_model=List[LogEntry])
async def get_system_logs(
    limit: int = Query(100, description="Maximum number of logs to return", ge=1, le=1000),
    offset: int = Query(0, description="Number of logs to skip", ge=0),
    level: Optional[str] = Query(None, description="Filter by log level (INFO, WARNING, ERROR, etc.)"),
    start_date: Optional[str] = Query(None, description="Filter logs after this date (format: YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter logs before this date (format: YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search term to filter messages"),
    client_ip: str = Depends(get_client_ip),
    _: Dict = Depends(get_secret_key)
) -> List[Dict]:
    """
    Get system logs with filtering options
    """
    log_access(f"Retrieving system logs (limit={limit}, offset={offset})", client_ip=client_ip)
    
    try:
        return await get_logs(
            log_type="system",
            limit=limit,
            offset=offset,
            level=level,
            start_date=start_date,
            end_date=end_date,
            search=search
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving logs: {str(e)}")