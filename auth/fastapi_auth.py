import os
import secrets
from fastapi import HTTPException, Depends, security, status, Request
from fastapi.security import HTTPBasicCredentials, HTTPBasic
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