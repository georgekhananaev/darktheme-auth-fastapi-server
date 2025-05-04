import os
import secrets
from fastapi import HTTPException, Depends, security, status, Request, Header
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from typing import Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv
from modules.logger import log_system, log_access, log_security
from modules.config import config
from modules.cache_handler import (
    CacheHandler, 
    get_login_attempts, 
    get_last_attempt_time, 
    set_failed_login, 
    reset_login_attempts
)

# Load environment variables from a .env file
load_dotenv()

# Secret key for token-based authentication
SECRET_KEY = os.environ["BEARER_SECRET_KEY"]

# Create instances of HTTPBearer and HTTPBasic for security
http_bearer = security.HTTPBearer()
security_basic = HTTPBasic()

# Check if Redis is enabled
REDIS_ENABLED = config.is_redis_enabled()

# Get security configuration
SECURITY_CONFIG = config.get_security_config()
API_KEY_ENABLED = SECURITY_CONFIG.get('api_key', {}).get('enabled', False)
API_KEY_HEADER = SECURITY_CONFIG.get('api_key', {}).get('header_name', 'X-API-Key') if API_KEY_ENABLED else None

# API Key (from environment variable if provided, otherwise None)
API_KEY = os.environ.get("API_KEY", None) if API_KEY_ENABLED else None


async def get_client_ip(request: Request) -> str:
    """
    Get the client IP address from the request.
    
    Args:
        request: The FastAPI request
        
    Returns:
        str: Client IP address
    """
    headers = request.headers
    # Check for X-Forwarded-For header first (for clients behind proxies)
    if "x-forwarded-for" in headers:
        return headers["x-forwarded-for"].split(",")[0].strip()
    # Otherwise use the direct client IP
    elif request.client:
        return request.client.host
    return "unknown"


async def get_secret_key(security_payload: security.HTTPAuthorizationCredentials = Depends(http_bearer),
                         request: Request = None):
    """
    Verifies the authorization token in the request header.

    Args:
        security_payload: The security credentials from the request header.
        request: The FastAPI request.

    Raises:
        HTTPException: If the token is invalid or not provided.

    Returns:
        The authorization token.
    """
    authorization = security_payload.credentials
    client_ip = await get_client_ip(request) if request else "unknown"
    
    if not authorization or SECRET_KEY not in authorization:
        log_security(
            "Unauthorized API access attempt with invalid token", 
            client_ip=client_ip, 
            level="WARNING"
        )
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Log successful API access
    log_access(
        "API access with valid token",
        client_ip=client_ip,
        level="INFO"
    )
    
    return authorization


async def verify_credentials(credentials: HTTPBasicCredentials = Depends(security_basic),
                            request: Request = None):
    """
    Verifies user credentials and handles login attempts.

    Args:
        credentials: The HTTPBasicCredentials containing the username and password.
        request: The FastAPI request.

    Raises:
        HTTPException: If the credentials are incorrect or if there are too many failed attempts.

    Returns:
        The verified credentials.
    """
    username = credentials.username
    current_time = datetime.now()
    client_ip = await get_client_ip(request) if request else "unknown"
    
    # Get Redis client
    redis = await CacheHandler.get_redis_client()

    # Check if Redis is enabled for login attempt tracking
    if REDIS_ENABLED:
        # Check if the username is currently blocked due to too many failed attempts
        attempts = await get_login_attempts(redis, username)
        last_attempt_time = await get_last_attempt_time(redis, username)

        if attempts >= 5 and last_attempt_time and (current_time - last_attempt_time) < timedelta(minutes=5):
            log_security(
                f"Too many login attempts for username: {username}",
                client_ip=client_ip,
                username=username,
                level="ERROR"
            )
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                                detail="Too many login attempts. Please try again later.")

    # Compare the provided credentials with the stored credentials
    correct_username = secrets.compare_digest(credentials.username, os.environ["FASTAPI_UI_USERNAME"])
    correct_password = secrets.compare_digest(credentials.password, os.environ["FASTAPI_UI_PASSWORD"])

    if not (correct_username and correct_password):
        if REDIS_ENABLED:
            await set_failed_login(redis, username, (await get_login_attempts(redis, username)) + 1, current_time)
            
        log_security(
            f"Failed login attempt with username: {username}",
            client_ip=client_ip,
            username=username,
            level="WARNING"
        )
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    # Reset the failed login attempts on successful login
    if REDIS_ENABLED:
        await reset_login_attempts(redis, username)
    
    # Log successful login
    log_access(
        f"Successful login for username: {username}",
        client_ip=client_ip,
        username=username,
        level="INFO"
    )
    
    return credentials


async def verify_api_key(
    request: Request, 
    api_key: Optional[str] = Header(None, name=API_KEY_HEADER if API_KEY_ENABLED else "X-API-Key", include_in_schema=API_KEY_ENABLED)
):
    """
    Verifies the API key in the request header.
    
    Args:
        request: The FastAPI request.
        api_key: The API key from the request header.
        
    Raises:
        HTTPException: If the API key is invalid or not provided when required.
        
    Returns:
        The API key if valid, or None if API key verification is disabled.
    """
    # Skip API key verification if API key security is disabled
    if not API_KEY_ENABLED:
        return None
        
    client_ip = await get_client_ip(request)
    header_name = API_KEY_HEADER.lower().replace('-', '_')
    
    # Check if API key header exists
    if not api_key:
        # Try to get it from the custom header
        headers = request.headers
        for key, value in headers.items():
            if key.lower().replace('-', '_') == header_name:
                api_key = value
                break
    
    # If API key is still not found
    if not api_key:
        log_security(
            f"API access attempt without API key", 
            client_ip=client_ip, 
            level="WARNING"
        )
        raise HTTPException(status_code=401, detail="API key missing")
    
    # Compare the provided API key with the stored API key
    if not API_KEY or not secrets.compare_digest(api_key, API_KEY):
        log_security(
            f"Invalid API key used for access", 
            client_ip=client_ip, 
            level="WARNING"
        )
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    # Log successful API access with API key
    log_access(
        "API access with valid API key",
        client_ip=client_ip,
        level="INFO"
    )
    
    return api_key


class AuthOptions:
    """
    Options for configuring authentication methods.
    """
    REQUIRE_BEARER = "require_bearer"
    REQUIRE_API_KEY = "require_api_key"
    ANY_AUTH_METHOD = "any_auth_method"
    NO_AUTH = "no_auth"


def create_auth_dependency(auth_mode: str = AuthOptions.ANY_AUTH_METHOD):
    """
    Factory function to create appropriate authentication dependency based on desired mode.
    
    Args:
        auth_mode: The authentication mode to use:
            - REQUIRE_BEARER: Only allow Bearer token authentication
            - REQUIRE_API_KEY: Only allow API key authentication (if enabled)
            - ANY_AUTH_METHOD: Allow either Bearer token or API key (if enabled)
            - NO_AUTH: No authentication required
            
    Returns:
        A dependency function for authentication with the specified mode
    """
    if auth_mode == AuthOptions.NO_AUTH:
        # No authentication required
        async def no_auth(request: Request):
            client_ip = await get_client_ip(request)
            return {
                "client_ip": client_ip,
                "authenticated_by": "none",
                "timestamp": datetime.utcnow().isoformat()
            }
        return no_auth
        
    elif auth_mode == AuthOptions.REQUIRE_BEARER:
        # Only Bearer token is accepted
        async def bearer_only_auth(
            request: Request,
            token: Optional[str] = Depends(get_secret_key)
        ):
            client_ip = await get_client_ip(request)
            return {
                "client_ip": client_ip,
                "authenticated_by": "bearer_token",
                "timestamp": datetime.utcnow().isoformat()
            }
        return bearer_only_auth
        
    elif auth_mode == AuthOptions.REQUIRE_API_KEY and API_KEY_ENABLED:
        # Only API key is accepted (if enabled)
        async def api_key_only_auth(
            request: Request,
            api_key: Optional[str] = Depends(verify_api_key)
        ):
            client_ip = await get_client_ip(request)
            return {
                "client_ip": client_ip,
                "authenticated_by": "api_key",
                "timestamp": datetime.utcnow().isoformat()
            }
        return api_key_only_auth
        
    else:
        # Default: Allow any authentication method
        if API_KEY_ENABLED:
            # Both Bearer token and API key are accepted
            async def flexible_auth(
                request: Request,
                token: Optional[str] = Depends(get_secret_key),
                api_key: Optional[str] = Depends(verify_api_key)
            ):
                client_ip = await get_client_ip(request)
                auth_method = "api_key" if api_key else "bearer_token"
                return {
                    "client_ip": client_ip,
                    "authenticated_by": auth_method, 
                    "timestamp": datetime.utcnow().isoformat()
                }
            return flexible_auth
        else:
            # Only Bearer token is accepted (API key disabled)
            async def bearer_only_auth(
                request: Request,
                token: Optional[str] = Depends(get_secret_key)
            ):
                client_ip = await get_client_ip(request)
                return {
                    "client_ip": client_ip,
                    "authenticated_by": "bearer_token",
                    "timestamp": datetime.utcnow().isoformat()
                }
            return bearer_only_auth


# Create the default verify_auth dependency using the factory
verify_auth = create_auth_dependency(AuthOptions.ANY_AUTH_METHOD)