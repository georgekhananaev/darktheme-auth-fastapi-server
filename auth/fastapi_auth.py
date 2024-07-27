import os
import secrets
from fastapi import HTTPException, Depends, security, status
from fastapi.security import HTTPBasicCredentials, HTTPBasic
from datetime import datetime, timedelta
from dotenv import load_dotenv
from db.clientRedis import AsyncRedisClient
from components.logger import log_info, log_warning, log_error

# Load environment variables from a .env file
load_dotenv()

# Secret key for token-based authentication
SECRET_KEY = os.environ["BEARER_SECRET_KEY"]

# Create instances of HTTPBearer and HTTPBasic for security
http_bearer = security.HTTPBearer()
security_basic = HTTPBasic()


async def get_secret_key(security_payload: security.HTTPAuthorizationCredentials = Depends(http_bearer)):
    """
    Verifies the authorization token in the request header.

    Args:
        security_payload: The security credentials from the request header.

    Raises:
        HTTPException: If the token is invalid or not provided.

    Returns:
        The authorization token.
    """
    authorization = security_payload.credentials
    if not authorization or SECRET_KEY not in authorization:
        log_warning("Unauthorized access attempt.")
        raise HTTPException(status_code=403, detail="Unauthorized")
    return authorization


async def get_login_attempts(username: str):
    """
    Retrieves the number of failed login attempts for a given username.

    Args:
        username: The username to check.

    Returns:
        The number of failed login attempts.
    """
    redis_client = await AsyncRedisClient.get_instance()
    attempts = await redis_client.get(f"{username}:attempts")
    return int(attempts) if attempts else 0


async def get_last_attempt_time(username: str):
    """
    Retrieves the time of the last failed login attempt for a given username.

    Args:
        username: The username to check.

    Returns:
        The datetime of the last failed login attempt or None if not found.
    """
    redis_client = await AsyncRedisClient.get_instance()
    last_time = await redis_client.get(f"{username}:last_attempt")
    return datetime.fromtimestamp(float(last_time)) if last_time else None


async def set_failed_login(username: str, attempts: int, last_attempt_time: datetime):
    """
    Sets the number of failed login attempts and the time of the last attempt for a username.

    Args:
        username: The username to update.
        attempts: The number of failed login attempts.
        last_attempt_time: The datetime of the last failed login attempt.
    """
    redis_client = await AsyncRedisClient.get_instance()
    await redis_client.set(f"{username}:attempts", attempts, ex=300)  # 5 minutes expiration
    await redis_client.set(f"{username}:last_attempt", last_attempt_time.timestamp(), ex=300)
    log_warning(f"Failed login attempt for username: {username}. Attempts: {attempts}")


async def reset_login_attempts(username: str):
    """
    Resets the failed login attempt count for a username.

    Args:
        username: The username to reset.
    """
    redis_client = await AsyncRedisClient.get_instance()
    await redis_client.delete(f"{username}:attempts", f"{username}:last_attempt")


async def verify_credentials(credentials: HTTPBasicCredentials = Depends(security_basic)):
    """
    Verifies user credentials and handles login attempts.

    Args:
        credentials: The HTTPBasicCredentials containing the username and password.

    Raises:
        HTTPException: If the credentials are incorrect or if there are too many failed attempts.

    Returns:
        The verified credentials.
    """
    username = credentials.username
    current_time = datetime.now()

    # Check if the username is currently blocked due to too many failed attempts
    attempts = await get_login_attempts(username)
    last_attempt_time = await get_last_attempt_time(username)

    if attempts >= 5 and last_attempt_time and (current_time - last_attempt_time) < timedelta(minutes=5):
        log_error(f"Too many login attempts for username: {username}.")
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Too many login attempts. Please try again later.")

    # Compare the provided credentials with the stored credentials
    correct_username = secrets.compare_digest(credentials.username, os.environ["FASTAPI_UI_USERNAME"])
    correct_password = secrets.compare_digest(credentials.password, os.environ["FASTAPI_UI_PASSWORD"])

    if not (correct_username and correct_password):
        await set_failed_login(username, attempts + 1, current_time)
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    # Reset the failed login attempts on successful login
    await reset_login_attempts(username)
    log_info(f"Successful login for username: {username}.")
    return credentials
