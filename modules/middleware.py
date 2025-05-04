import time
import os
from typing import Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse
from modules.logger import log_access, log_system
from modules.config import config
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


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware to redirect HTTP requests to HTTPS.
    
    This middleware checks if the request is using HTTP and redirects
    to HTTPS if configured to do so.
    """
    
    async def dispatch(self, request: Request, call_next):
        """Process an incoming request and redirect to HTTPS if needed."""
        # Check if HTTPS redirection is enabled
        if config.is_http_to_https_redirect_enabled() and config.is_https_enabled():
            # Check if the request is using HTTP
            # Consider both URL scheme and X-Forwarded-Proto header (used in testing)
            is_http = request.url.scheme == "http" or request.headers.get("X-Forwarded-Proto") == "http"
            if is_http:
                # Get the host and port
                host = request.headers.get("host", "").split(":")[0]
                # Create the HTTPS URL
                https_url = f"https://{host}"
                
                # Add the path and query parameters
                path = request.url.path
                if request.url.query:
                    path = f"{path}?{request.url.query}"
                
                # Log the redirection
                client_ip = await get_client_ip(request)
                log_access(
                    f"Redirecting HTTP request to HTTPS: {request.url} -> {https_url}{path}",
                    client_ip=client_ip,
                    level="INFO"
                )
                
                # Return the redirection response
                return RedirectResponse(
                    url=f"{https_url}{path}",
                    status_code=301  # Permanent redirect
                )
        
        # Process the request normally if no redirection is needed
        return await call_next(request)


class HTTPDisableMiddleware(BaseHTTPMiddleware):
    """
    Middleware to disable HTTP requests when configured.
    
    This middleware checks if HTTP is disabled in configuration and
    returns a 403 Forbidden response for all HTTP requests.
    """
    
    async def dispatch(self, request: Request, call_next):
        """Process an incoming request and block HTTP if disabled."""
        # Check if HTTP is disabled and we're in secure mode (environment variable set by run_local.sh)
        if not config.is_http_enabled() and os.environ.get("DISABLE_HTTP") == "1":
            # Check if this is an HTTP request (from URL scheme or X-Forwarded-Proto header)
            is_http = request.url.scheme == "http" or request.headers.get("X-Forwarded-Proto") == "http"
            # Allow HTTPS requests even when HTTP is disabled
            if is_http and request.headers.get("X-Forwarded-Proto") != "https":
                # The request is using HTTP and HTTP is disabled
                client_ip = await get_client_ip(request)
                log_access(
                    f"Blocked HTTP request (HTTP disabled): {request.method} {request.url.path}",
                    client_ip=client_ip,
                    level="WARNING"
                )
                
                # Return a 403 Forbidden response
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "HTTP requests are disabled. Please use HTTPS instead."
                    }
                )
        
        # Process the request normally if HTTP is enabled
        return await call_next(request)