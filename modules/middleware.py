import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from modules.logger import log_access, log_system
from auth.fastapi_auth import get_client_ip


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all incoming requests and responses.
    
    This middleware captures request details such as method, path, client IP,
    and timing information. It logs access and performance data.
    """
    
    async def dispatch(self, request: Request, call_next):
        """Process an incoming request and log its details."""
        # Start timer
        start_time = time.time()
        
        # Get client IP
        client_ip = await get_client_ip(request)
        path = request.url.path
        method = request.method
        
        # Process the request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            process_time_ms = round(process_time * 1000, 2)
            
            # Determine status code category
            status_code = response.status_code
            status_phrase = self._get_status_phrase(status_code)
            
            # Log the request
            log_access(
                f"{method} {path} {status_code} {status_phrase} - {process_time_ms}ms",
                client_ip=client_ip,
                level="INFO" if status_code < 400 else "WARNING"
            )
            
            # Log slow responses (more than 500ms)
            if process_time_ms > 500:
                log_system(
                    f"Slow response on {method} {path}: {process_time_ms}ms",
                    level="WARNING"
                )
                
            return response
            
        except Exception as e:
            # Calculate time even for errors
            process_time = time.time() - start_time
            process_time_ms = round(process_time * 1000, 2)
            
            # Log the error
            log_system(
                f"Error processing {method} {path}: {str(e)}",
                level="ERROR"
            )
            
            # Log the access with error status
            log_access(
                f"{method} {path} 500 Error - {process_time_ms}ms",
                client_ip=client_ip,
                level="ERROR"
            )
            
            # Re-raise the exception
            raise
            
    @staticmethod
    def _get_status_phrase(status_code: int) -> str:
        """Get a human-readable phrase for the HTTP status code."""
        if 100 <= status_code < 200:
            return "Informational"
        elif 200 <= status_code < 300:
            return "Success"
        elif 300 <= status_code < 400:
            return "Redirection"
        elif 400 <= status_code < 500:
            return "Client Error"
        elif 500 <= status_code < 600:
            return "Server Error"
        else:
            return "Unknown"